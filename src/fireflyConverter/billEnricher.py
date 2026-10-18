from __future__ import annotations

import dataclasses as dc
import logging
import os
import shutil
from typing import Any, List, Optional, Sequence

from fireflyConverter import billMatching as bm
from fireflyConverter import bills, data

logger = logging.getLogger(__name__)


@dc.dataclass
class BillConfig:
    """Configuration for bill-aware enrichment.

    Field names mirror the ``[bills]`` section of the configuration file.

    Attributes:
        directory (str): Folder that holds the dropped bills.
        date_window_days (int): Maximum day gap between bill and transaction dates.
        amount_tolerance (float): Allowed difference between bill total and transaction amount.
        vendor_threshold (float): Minimum vendor similarity for a match.
        confidence_threshold (float): Minimum extraction confidence to apply category and tags.
        marker_tag (str): Audit tag written onto enriched transactions.
        move_processed (bool): Whether applied bills are archived after a run.
        processed_subdir (str): Subfolder that applied bills are moved into.
        report_path (str): Where the enrichment report is written.
        vision (bool): Whether scanned bills may be rasterized for the vision model.
        max_pages (int): Number of PDF pages considered for text extraction.
        accounts (bool): Whether bills may also set the transaction's counter-account.
    """

    directory: str
    date_window_days: int = 14
    amount_tolerance: float = 0.0
    vendor_threshold: float = 0.6
    confidence_threshold: float = 0.5
    marker_tag: str = "bill-matched"
    move_processed: bool = True
    processed_subdir: str = "processed"
    report_path: str = "bills-report.md"
    vision: bool = True
    max_pages: int = 1
    accounts: bool = True


@dc.dataclass
class MatchRecord:
    """Summary of one bill that was matched and applied.

    Attributes:
        bill_path (str): Path of the matched bill file.
        description (str): Description of the enriched transaction.
        category (str | None): Category written onto the transaction.
        account (str | None): Counter-account written onto the transaction.
        tags (List[str]): Tags written onto the transaction.
        llm_response (str | None): Raw LLM response for verbose reporting.
    """

    bill_path: str
    description: str
    category: Optional[str]
    tags: List[str]
    account: Optional[str] = None
    llm_response: Optional[str] = None


@dc.dataclass
class EnrichmentReport:
    """Outcome of one enrichment run.

    Attributes:
        matched (List[MatchRecord]): Bills that were matched and applied.
        matched_transactions (List[data.BaseTransaction]): Transactions that a bill was applied to.
        unmatched (List[str]): Bills without a matching transaction.
        ambiguous (List[str]): Bills that matched more than one transaction.
        duplicates (List[str]): Bills whose only candidate transaction was claimed by another bill.
        errors (List[str]): Bills that could not be read or parsed.
        issues (List[str]): Non-fatal warnings from applying bills.
    """

    matched: List[MatchRecord] = dc.field(default_factory=list)
    matched_transactions: List[data.BaseTransaction] = dc.field(default_factory=list)
    unmatched: List[str] = dc.field(default_factory=list)
    ambiguous: List[str] = dc.field(default_factory=list)
    duplicates: List[str] = dc.field(default_factory=list)
    errors: List[str] = dc.field(default_factory=list)
    issues: List[str] = dc.field(default_factory=list)


class BillEnricher:
    """Match dropped bills to transactions and enrich the matched ones.

    Attributes:
        _reader (Any): Bill reader exposing a ``read(path)`` method.
        _categories (List[str]): Existing Firefly III category names.
        _tags (List[str]): Existing Firefly III tag names.
        _accounts (List[str]): Existing Firefly III account names.
        _config (BillConfig): Enrichment configuration.
    """

    def __init__(
        self,
        reader: Any,
        categories: Sequence[str],
        tags: Sequence[str],
        accounts: Sequence[str],
        config: BillConfig,
    ) -> None:
        """Initialize the enricher.

        Args:
            reader (Any): Bill reader (see ``bills.BillReader``).
            categories (Sequence[str]): Existing Firefly III category names.
            tags (Sequence[str]): Existing Firefly III tag names.
            accounts (Sequence[str]): Existing Firefly III account names.
            config (BillConfig): Enrichment configuration.
        """
        self._reader = reader
        self._categories = list(categories)
        self._tags = list(tags)
        self._accounts = list(accounts)
        self._config = config

    def enrich(self, transactions: Sequence[data.BaseTransaction]) -> EnrichmentReport:
        """Read every bill, match it, and enrich the matched transactions.

        Reading or parsing failures are recorded and skipped so that a single
        bad document never aborts the import.

        Args:
            transactions (Sequence[data.BaseTransaction]): Transactions of the current import.

        Returns:
            EnrichmentReport: Per-bill outcome.
        """
        report = EnrichmentReport()
        matcher = bm.BillMatcher(
            transactions,
            dateWindowDays=self._config.date_window_days,
            amountTolerance=self._config.amount_tolerance,
            vendorThreshold=self._config.vendor_threshold,
        )

        billPaths = bills.discoverBills(self._config.directory)
        logger.info(f"Found {len(billPaths)} bill(s) in {self._config.directory}")
        for path in billPaths:
            try:
                bill = self._reader.read(path)
            except Exception as error:  # noqa: BLE001 - one bad bill must not abort the import
                logger.warning(f"Failed to read bill {path}: {error}")
                report.errors.append(f"{path}: {error}")
                continue

            outcome = matcher.match(bill)
            if outcome.status == bm.MATCHED:
                issues = bm.applyBill(
                    bill,
                    outcome.transaction,
                    self._categories,
                    self._tags,
                    self._accounts,
                    markerTag=self._config.marker_tag,
                    confidenceThreshold=self._config.confidence_threshold,
                )
                report.issues.extend(f"{os.path.basename(path)}: {issue}" for issue in issues)
                report.matched.append(
                    MatchRecord(
                        bill_path=path,
                        description=outcome.transaction.description,
                        category=outcome.transaction.category_name,
                        account=outcome.transaction.destination_name,
                        tags=list(outcome.transaction.tags or []),
                        llm_response=bill.llm_response,
                    )
                )
                report.matched_transactions.append(outcome.transaction)
            elif outcome.status == bm.AMBIGUOUS:
                report.ambiguous.append(path)
            elif outcome.status == bm.ALREADY_MATCHED:
                report.duplicates.append(path)
            else:
                report.unmatched.append(path)

        return report

    def archiveProcessed(self, report: EnrichmentReport) -> None:
        """Move successfully applied bills into the processed subfolder.

        Existing files are never overwritten: a name collision is resolved by
        appending a counter, so an earlier audit copy is preserved.

        Args:
            report (EnrichmentReport): Report whose matched bills should be archived.
        """
        if not report.matched:
            return

        target = os.path.join(self._config.directory, self._config.processed_subdir)
        os.makedirs(target, exist_ok=True)
        for record in report.matched:
            destination = _uniqueTarget(target, os.path.basename(record.bill_path))
            logger.info(f"Archiving bill: {record.bill_path} -> {destination}")
            shutil.move(record.bill_path, destination)


def _uniqueTarget(directory: str, filename: str) -> str:
    """Return a path inside directory that does not exist yet.

    Args:
        directory (str): Directory the file is moved into.
        filename (str): Preferred file name.

    Returns:
        str: An unused path, with a counter suffix when the name is taken.
    """
    base, extension = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}-{counter}{extension}")
        counter += 1
    return candidate


def renderReport(report: EnrichmentReport, verbose: bool = False) -> str:
    """Render an enrichment report as Markdown.

    Args:
        report (EnrichmentReport): Report to render.
        verbose (bool): Include raw LLM responses for matched bills.

    Returns:
        str: Markdown report text.
    """
    lines: List[str] = ["# Bill enrichment report", ""]
    lines.append(
        f"Matched: {len(report.matched)} | Unmatched: {len(report.unmatched)} | "
        f"Ambiguous: {len(report.ambiguous)} | Duplicates: {len(report.duplicates)} | "
        f"Errors: {len(report.errors)}"
    )
    lines.append("")

    lines.append("## Matched")
    if report.matched:
        for record in report.matched:
            parts = (
                f"- {os.path.basename(record.bill_path)} -> \"{record.description}\" | "
                f"category: {record.category or '-'} | account: {record.account or '-'} | "
                f"tags: {', '.join(record.tags) or '-'}"
            )
            if verbose and record.llm_response:
                parts += f" | LLM: {record.llm_response}"
            lines.append(parts)
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Unmatched bills")
    lines.extend(f"- {path}" for path in report.unmatched)
    if not report.unmatched:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Ambiguous bills")
    lines.extend(f"- {path}" for path in report.ambiguous)
    if not report.ambiguous:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Duplicate bills")
    lines.extend(f"- {path}" for path in report.duplicates)
    if not report.duplicates:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Errors")
    lines.extend(f"- {error}" for error in report.errors)
    if not report.errors:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Warnings")
    lines.extend(f"- {issue}" for issue in report.issues)
    if not report.issues:
        lines.append("- (none)")

    lines.append("")
    return "\n".join(lines)
