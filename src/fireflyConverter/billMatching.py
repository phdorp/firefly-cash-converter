from __future__ import annotations

import dataclasses as dc
import datetime
import logging
import os
import re
from difflib import SequenceMatcher
from itertools import combinations
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
        additional_bills (List[data.Bill]): Other bills contributing to a split.
        overflow_bills (List[data.Bill]): Bills excluded because the split limit was reached.
    """

    status: str
    transaction: Optional[data.BaseTransaction] = None
    additional_bills: List[data.Bill] = dc.field(default_factory=list)
    overflow_bills: List[data.Bill] = dc.field(default_factory=list)


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

    def match(
        self,
        bill: data.Bill,
        additional_bills: Sequence[data.Bill] = (),
        max_split_balls: int = 5,
    ) -> MatchOutcome:
        """Find the transaction that belongs to a bill, optionally as a split.

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
            splitOutcome = self._matchSplit(bill, additional_bills, max_split_balls)
            if splitOutcome is not None:
                return splitOutcome
            return MatchOutcome(AMBIGUOUS)

        splitOutcome = self._matchSplit(bill, additional_bills, max_split_balls)
        if splitOutcome is not None:
            return splitOutcome
        if candidates:
            return MatchOutcome(ALREADY_MATCHED)
        return MatchOutcome(NO_CANDIDATE)

    def _matchSplit(
        self,
        bill: data.Bill,
        additionalBills: Sequence[data.Bill],
        maxSplitBills: int,
    ) -> Optional[MatchOutcome]:
        """Find an unclaimed transaction whose amount is covered by several bills."""
        if bill.total is None or maxSplitBills < 2:
            return None

        availableTransactions = [transaction for transaction in self._transactions if id(transaction) not in self._claimed]
        matches: List[Tuple[data.BaseTransaction, List[data.Bill], List[data.Bill]]] = []
        for transaction in availableTransactions:
            candidates = [
                candidate
                for candidate in [bill, *additionalBills]
                if candidate.total is not None and self._isSplitCandidate(candidate, transaction)
            ]
            if bill not in candidates:
                continue
            if (
                len(candidates) > maxSplitBills
                and abs(
                    sum(float(candidate.total) for candidate in candidates if candidate.total is not None)
                    - float(transaction.amount)
                )
                <= self._amountTolerance
            ):
                return MatchOutcome(AMBIGUOUS, overflow_bills=candidates)
            group = self._findBillGroup(candidates, transaction, maxSplitBills)
            if group is not None:
                matchingBills, overflowBills = group
                if len(matchingBills) > 1:
                    matches.append((transaction, matchingBills, overflowBills))

        if len(matches) != 1:
            return None

        transaction, matchingBills, overflowBills = matches[0]
        self._claimed.add(id(transaction))
        primaryIndex = matchingBills.index(bill)
        additional = matchingBills[:primaryIndex] + matchingBills[primaryIndex + 1 :]
        return MatchOutcome(MATCHED, transaction, additional, overflowBills)

    def _findBillGroup(
        self,
        candidates: Sequence[data.Bill],
        transaction: data.BaseTransaction,
        maxSplitBills: int,
    ) -> Optional[Tuple[List[data.Bill], List[data.Bill]]]:
        """Find a bill subset whose totals equal a transaction amount."""
        if transaction.amount is None:
            return None

        uniqueCandidates: List[data.Bill] = []
        seenIds: Set[int] = set()
        for candidate in candidates:
            if id(candidate) not in seenIds:
                uniqueCandidates.append(candidate)
                seenIds.add(id(candidate))
        for size in range(2, min(maxSplitBills, len(uniqueCandidates)) + 1):
            for groupTuple in combinations(uniqueCandidates, size):
                total = sum(float(candidate.total) for candidate in groupTuple if candidate.total is not None)
                if abs(total - float(transaction.amount)) <= self._amountTolerance:
                    matched = list(groupTuple)
                    overflow = [
                        candidate
                        for candidate in uniqueCandidates
                        if candidate not in matched and candidate is not None
                    ]
                    return matched, overflow
        return None

    def _isCandidate(self, bill: data.Bill, transaction: data.BaseTransaction) -> bool:
        """Return True if a transaction satisfies amount, date and vendor criteria."""
        if abs(float(transaction.amount) - bill.total) > self._amountTolerance:
            return False
        if not self._withinDateWindow(bill.date, transaction.date):
            return False
        return vendorSimilarity(bill.vendor or "", transaction.description or "") >= self._vendorThreshold

    def _isSplitCandidate(self, bill: data.Bill, transaction: data.BaseTransaction) -> bool:
        """Return True if a bill can contribute a positive part of a transaction."""
        if bill.total is None or float(bill.total) <= 0:
            return False
        if float(bill.total) - float(transaction.amount) > self._amountTolerance:
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
    additional_bills: Sequence[data.Bill] = (),
    accountsEnabled: Optional[bool] = None,
    amountTolerance: float = 0.0,
    maxSplitEntries: int = 5,
) -> List[str]:
    """Write bill-derived category, account, tags and notes onto a transaction.

    A low-confidence extraction applies none of the category, account or tags.
    Existing counter-accounts are never overwritten. Additional bills are
    represented as Firefly III split entries.

    Args:
        bill (data.Bill): The matched bill.
        transaction (data.BaseTransaction): Transaction to enrich in place.
        categories (Sequence[str]): Existing Firefly III category names.
        tags (Sequence[str]): Existing Firefly III tag names.
        accounts (Sequence[str]): Existing Firefly III account names.
        markerTag (Optional[str]): Audit tag added to enriched transactions. Defaults to "bill-matched".
        confidenceThreshold (float): Minimum confidence to apply category, account and tags. Defaults to 0.5.
        additional_bills (Sequence[data.Bill]): Other bills contributing to a split.
        accountsEnabled (Optional[bool]): Retained for API compatibility; unknown account names are never created.
        amountTolerance (float): Allowed difference between split total and transaction amount.
        maxSplitEntries (int): Maximum number of line-item split entries to apply.

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

        accountField = "source_name" if transaction.type == data.TransactionType.DEPOSIT.value else "destination_name"
        existingAccount = getattr(transaction, accountField)
        accountName, _ = _applyAccount(bill, transaction, accounts, allowNew=False)
        if existingAccount and accountName and _canonicalName(existingAccount, [accountName]) is None:
            issues.append(f"Kept existing account '{existingAccount}'; bill suggested '{accountName}'")
        resolvedTags, unknownTags = _canonicalTags(bill.tags, tags)
        for unknown in unknownTags:
            issues.append(f"Tag '{unknown}' is not defined in Firefly III; dropped")

    if markerTag:
        resolvedTags.append(markerTag)

    transaction.tags = resolvedTags
    transaction.notes = _composeNotes(bill, transaction.notes)

    if bill.splits and not additional_bills:
        if len(bill.splits) > maxSplitEntries:
            issues.append(
                f"Bill has {len(bill.splits)} split entries; maximum is "
                f"{maxSplitEntries}; splits were not applied"
            )
            return issues
        splitTotal = sum(float(split.amount) for split in bill.splits if split.amount is not None)
        if bill.total is None or abs(splitTotal - float(bill.total)) > amountTolerance:
            issues.append(
                f"Bill split total {splitTotal:.2f} does not match bill total "
                f"{bill.total if bill.total is not None else 'unknown'}; splits were not applied"
            )
            return issues

        splitTransactions: List[data.TransactionSplit] = []
        for split in bill.splits:
            if split.amount is None:
                issues.append("Bill split without an amount was ignored")
                continue
            splitCategory: Optional[str] = None
            splitTags: List[str] = []
            if split.confidence >= confidenceThreshold:
                splitCategory = _canonicalName(split.category, categories)
                if split.category and splitCategory is None:
                    issues.append(f"Category '{split.category}' is not defined in Firefly III; left empty")
                splitTags, unknownTags = _canonicalTags(split.tags, tags)
                for unknown in unknownTags:
                    issues.append(f"Tag '{unknown}' is not defined in Firefly III; dropped")
            splitTransactions.append(
                data.TransactionSplit(
                    amount=split.amount,
                    source_name=transaction.source_name,
                    destination_name=transaction.destination_name,
                    category_name=splitCategory,
                    tags=splitTags + ([markerTag] if markerTag else []),
                    notes=_composeNotes(bill, split.note),
                )
            )
        if splitTransactions:
            transaction.split_transactions = splitTransactions

    if additional_bills:
        splitTotal = sum(float(additional.total) for additional in [bill, *additional_bills] if additional.total is not None)
        if abs(splitTotal - float(transaction.amount)) > amountTolerance:
            issues.append(
                f"Split bill total {splitTotal:.2f} does not match transaction amount "
                f"{float(transaction.amount):.2f}; split was not applied"
            )
            return issues

        splitTransactions: List[data.TransactionSplit] = []
        primaryAmount = bill.total
        if primaryAmount is not None:
            splitTransactions.append(
                data.TransactionSplit(
                    amount=primaryAmount,
                    category_name=transaction.category_name,
                    source_name=transaction.source_name,
                    destination_name=transaction.destination_name,
                    tags=list(transaction.tags or []),
                    notes=_composeNotes(bill, None),
                )
            )
        for additional in additional_bills:
            splitCategory: Optional[str] = None
            splitTags: List[str] = []
            if additional.confidence >= confidenceThreshold:
                splitCategory = _canonicalName(additional.category, categories)
                if additional.category and splitCategory is None:
                    issues.append(
                        f"Category '{additional.category}' is not defined in Firefly III; left empty"
                    )
                splitTags, unknownTags = _canonicalTags(additional.tags, tags)
                for unknown in unknownTags:
                    issues.append(f"Tag '{unknown}' is not defined in Firefly III; dropped")
            else:
                issues.append(
                    f"Low confidence ({additional.confidence:.2f} < {confidenceThreshold}); "
                    f"split fields left empty for {os.path.basename(additional.path)}"
                )
            if additional.total is not None:
                splitTransactions.append(
                    data.TransactionSplit(
                        amount=additional.total,
                        category_name=splitCategory,
                        source_name=transaction.source_name,
                        destination_name=transaction.destination_name,
                        tags=splitTags + ([markerTag] if markerTag else []),
                        notes=_composeNotes(additional, None),
                    )
                )
        transaction.split_transactions = splitTransactions
    return issues


def _applyAccount(
    bill: data.Bill,
    transaction: data.BaseTransaction,
    accounts: Sequence[str],
    allowNew: bool = True,
) -> Tuple[Optional[str], Optional[str]]:
    """Set the bill's counter-account on the transaction unless one is already set.

    An empty account vocabulary means the mapping is off, or that Firefly III
    holds no account to choose from; the transaction is then left untouched
    without an issue, because nothing could be mapped.

    Args:
        bill (data.Bill): The matched bill.
        transaction (data.BaseTransaction): Transaction to enrich in place.
        accounts (Sequence[str]): Existing Firefly III account names.

    Returns:
        Tuple[Optional[str], Optional[str]]: Account name and inferred Firefly type.
    """
    if not bill.account or not accounts:
        return None, None

    account = _canonicalName(bill.account, accounts)
    if account is None and allowNew:
        account = bill.account.strip()
    if account is None:
        return None, None

    accountField = "source_name" if transaction.type == data.TransactionType.DEPOSIT.value else "destination_name"
    existingAccount = getattr(transaction, accountField)
    if existingAccount:
        return account, _accountType(transaction)
    setattr(transaction, accountField, account)
    return account, _accountType(transaction)


def _accountType(transaction: data.BaseTransaction) -> str:
    """Infer the Firefly account type for a bill counter-account."""
    return "income" if transaction.type == data.TransactionType.DEPOSIT.value else "expense"


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
