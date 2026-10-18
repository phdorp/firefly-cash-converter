from __future__ import annotations

import dataclasses as dc
import datetime
import logging
import os
import re
from difflib import SequenceMatcher
from typing import List, Optional, Sequence, Set, Tuple

from fireflyConverter import data

logger = logging.getLogger(__name__)

MATCHED = "matched"
NO_TOTAL = "no_total"
NO_CANDIDATE = "no_candidate"
AMBIGUOUS = "ambiguous"
ALREADY_MATCHED = "already_matched"

_WITHDRAWAL = data.TransactionType.WITHDRAWAL.value


@dc.dataclass
class MatchOutcome:
    """Result of matching one bill against the transaction batch.

    Attributes:
        status (str): One of ``matched``, ``no_total``, ``no_candidate``,
            ``ambiguous`` or ``already_matched``.
        transaction (data.BaseTransaction | None): The matched transaction, if any.
    """

    status: str
    transaction: Optional[data.BaseTransaction] = None


def vendorSimilarity(left: str, right: str) -> float:
    """Score how well a vendor name matches a transaction description.

    Combines token containment (a short vendor fully present in a long bank
    description) with a character-level ratio, returning the better of the two.

    Args:
        left (str): Vendor name, typically taken from the bill.
        right (str): Transaction description, typically from the bank export.

    Returns:
        float: Similarity between 0 and 1.
    """
    leftTokens = _tokenize(left)
    rightTokens = _tokenize(right)
    if not leftTokens or not rightTokens:
        return 0.0

    coverage = len(leftTokens & rightTokens) / len(leftTokens)
    ratio = SequenceMatcher(None, " ".join(sorted(leftTokens)), " ".join(sorted(rightTokens))).ratio()
    return max(coverage, ratio)


def _tokenize(text: str) -> Set[str]:
    """Split text into lowercase alphanumeric tokens."""
    if not text:
        return set()
    return {token for token in re.split(r"[^0-9a-z]+", text.lower()) if token}


class BillMatcher:
    """Match bills to withdrawal transactions by amount, date and vendor.

    A transaction that has been matched is claimed, so a later bill can never
    reuse it: the one-bill-one-transaction rule holds even when two bills look
    alike.

    Attributes:
        _transactions (List[data.BaseTransaction]): Withdrawal transactions to match against.
        _dateWindowDays (int): Maximum allowed day gap between bill and transaction dates.
        _amountTolerance (float): Allowed difference between bill total and transaction amount.
        _vendorThreshold (float): Minimum vendor similarity for a candidate.
        _claimed (Set[int]): Identities of transactions already handed to a bill.
    """

    def __init__(
        self,
        transactions: Sequence[data.BaseTransaction],
        dateWindowDays: int = 14,
        amountTolerance: float = 0.0,
        vendorThreshold: float = 0.6,
    ) -> None:
        """Initialize the matcher with the transactions of the current import.

        Args:
            transactions (Sequence[data.BaseTransaction]): Transactions to match against.
            dateWindowDays (int): Maximum date gap in days. Defaults to 14.
            amountTolerance (float): Allowed amount difference. Defaults to 0.0.
            vendorThreshold (float): Minimum vendor similarity. Defaults to 0.6.
        """
        self._transactions = [transaction for transaction in transactions if transaction.type == _WITHDRAWAL]
        self._dateWindowDays = dateWindowDays
        self._amountTolerance = amountTolerance
        self._vendorThreshold = vendorThreshold
        self._claimed: Set[int] = set()

    def match(self, bill: data.Bill) -> MatchOutcome:
        """Find the single unclaimed transaction that belongs to a bill.

        Args:
            bill (data.Bill): The bill to match.

        Returns:
            MatchOutcome: The matched transaction, or the reason none was returned.
        """
        if bill.total is None:
            return MatchOutcome(NO_TOTAL)

        candidates = [transaction for transaction in self._transactions if self._isCandidate(bill, transaction)]
        available = [transaction for transaction in candidates if id(transaction) not in self._claimed]

        if len(available) == 1:
            self._claimed.add(id(available[0]))
            return MatchOutcome(MATCHED, available[0])
        if len(available) > 1:
            return MatchOutcome(AMBIGUOUS)
        if candidates:
            return MatchOutcome(ALREADY_MATCHED)
        return MatchOutcome(NO_CANDIDATE)

    def _isCandidate(self, bill: data.Bill, transaction: data.BaseTransaction) -> bool:
        """Return True if a transaction satisfies amount, date and vendor criteria."""
        if abs(float(transaction.amount) - bill.total) > self._amountTolerance:
            return False
        if not self._withinDateWindow(bill.date, transaction.date):
            return False
        return vendorSimilarity(bill.vendor or "", transaction.description or "") >= self._vendorThreshold

    def _withinDateWindow(self, billDate: Optional[str], transactionDate: Optional[str]) -> bool:
        """Return True if the dates are within the window, or either is unusable."""
        left = _parseDate(billDate)
        right = _parseDate(transactionDate)
        if left is None or right is None:
            return True
        return abs((left - right).days) <= self._dateWindowDays


def _parseDate(value: Optional[str]) -> Optional[datetime.date]:
    """Parse an ISO date, ignoring any time component."""
    if not value:
        return None
    text = str(value).split("T")[0].strip()
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def applyBill(
    bill: data.Bill,
    transaction: data.BaseTransaction,
    categories: Sequence[str],
    tags: Sequence[str],
    accounts: Sequence[str],
    markerTag: Optional[str] = "bill-matched",
    confidenceThreshold: float = 0.5,
) -> List[str]:
    """Write bill-derived category, account, tags and notes onto a transaction.

    The category, account and tags are restricted to the values that already
    exist, a low-confidence extraction applies none of them, and an existing
    counter-account is never overwritten. Notes and the marker tag are always
    written so the enrichment remains traceable.

    Args:
        bill (data.Bill): The matched bill.
        transaction (data.BaseTransaction): Transaction to enrich in place.
        categories (Sequence[str]): Existing Firefly III category names.
        tags (Sequence[str]): Existing Firefly III tag names.
        accounts (Sequence[str]): Existing Firefly III account names.
        markerTag (Optional[str]): Audit tag added to enriched transactions. Defaults to "bill-matched".
        confidenceThreshold (float): Minimum confidence to apply category, account and tags. Defaults to 0.5.

    Returns:
        List[str]: Human-readable issues to include in the report.
    """
    issues: List[str] = []
    resolvedTags: List[str] = []

    if bill.confidence < confidenceThreshold:
        issues.append(
            f"Low confidence ({bill.confidence:.2f} < {confidenceThreshold}); "
            "category, account and tags left empty"
        )
    else:
        category = _canonicalName(bill.category, categories)
        if bill.category and category is None:
            issues.append(f"Category '{bill.category}' is not defined in Firefly III; left empty")
        transaction.category_name = category

        issues.extend(_applyAccount(bill, transaction, accounts))

        resolvedTags, unknownTags = _canonicalTags(bill.tags, tags)
        for unknown in unknownTags:
            issues.append(f"Tag '{unknown}' is not defined in Firefly III; dropped")

    if markerTag:
        resolvedTags.append(markerTag)

    transaction.tags = resolvedTags
    transaction.notes = _composeNotes(bill, transaction.notes)
    return issues


def _applyAccount(bill: data.Bill, transaction: data.BaseTransaction, accounts: Sequence[str]) -> List[str]:
    """Set the bill's counter-account on the transaction unless one is already set.

    An empty account vocabulary means the mapping is off, or that Firefly III
    holds no account to choose from; the transaction is then left untouched
    without an issue, because nothing could be mapped.

    Args:
        bill (data.Bill): The matched bill.
        transaction (data.BaseTransaction): Transaction to enrich in place.
        accounts (Sequence[str]): Existing Firefly III account names.

    Returns:
        List[str]: Human-readable issues to include in the report.
    """
    account = _canonicalName(bill.account, accounts)
    if account is None:
        if bill.account and accounts:
            return [f"Account '{bill.account}' is not defined in Firefly III; left empty"]
        return []
    if transaction.destination_name:
        if _canonicalName(transaction.destination_name, [account]) is not None:
            return []
        return [f"Kept existing account '{transaction.destination_name}'; bill suggested '{account}'"]
    transaction.destination_name = account
    return []


def _canonicalName(name: Optional[str], candidates: Sequence[str]) -> Optional[str]:
    """Return the existing name matching name case-insensitively, or None."""
    if not name:
        return None
    for candidate in candidates:
        if candidate.strip().lower() == name.strip().lower():
            return candidate
    return None


def _canonicalTags(names: Sequence[str], tags: Sequence[str]) -> Tuple[List[str], List[str]]:
    """Split requested tag names into existing canonical names and unknown ones."""
    lookup = {tag.strip().lower(): tag for tag in tags}
    resolved: List[str] = []
    unknown: List[str] = []
    for name in names:
        canonical = lookup.get(name.strip().lower())
        if canonical is None:
            unknown.append(name)
        elif canonical not in resolved:
            resolved.append(canonical)
    return resolved, unknown


def _composeNotes(bill: data.Bill, existingNotes: Optional[str]) -> str:
    """Build the note text from the bill summary and source file, keeping prior notes."""
    parts: List[str] = []
    if bill.note:
        parts.append(bill.note.strip())
    parts.append(f"Source: {os.path.basename(bill.path)}")
    newNote = " | ".join(parts)
    if existingNotes:
        return f"{existingNotes}\n{newNote}"
    return newNote
