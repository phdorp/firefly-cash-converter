import enum
import logging
from argparse import ArgumentParser, Namespace, _SubParsersAction
from typing import Callable, Dict, List, Optional

import toml

from fireflyConverter import billEnricher as bce
from fireflyConverter import bills as bls
from fireflyConverter import convertData as cdt
from fireflyConverter import data
from fireflyConverter import fireflyInterface as ffi
from fireflyConverter import llmInterface as lli
from fireflyConverter import loadData as ldb

logger = logging.getLogger(__name__)

AUTO_LABELED_TAG = "auto_labeled"


class CommandType(enum.Enum):
    CONVERT = "convert"
    TRANSFER = "transfer"


def defineTransferParser(subparsers: _SubParsersAction):
    """Define the `transfer` subcommand and its arguments.

    Args:
        subparsers (_SubParsersAction): Subparser collection to which the
            transfer parser is added.
    """
    parser: ArgumentParser = subparsers.add_parser(
        CommandType.TRANSFER.value, help="Transfer transactions to Firefly III"
    )
    parser.add_argument(
        "source",
        type=str,
        choices=["barclays", "paypal", "trade_republic", "common"],
        help="Source of the input data.",
    )
    parser.add_argument(
        "--config_path",
        type=str,
        default="./config.toml",
        help="Path to the CLI configuration file.",
    )
    parser.add_argument(
        "--account_name", type=str, help="Name of the account to assign to loaded transactions.", default=None
    )
    parser.add_argument(
        "--input_directory",
        type=str,
        help="Path to the directory containing input files to be converted.",
        default="tmp",
    )
    parser.add_argument(
        "--input_name",
        type=str,
        help="Name of the input file to be converted.",
        default=None,
    )
    parser.add_argument(
        "--filter_query",
        type=str,
        help="Optional data query to filter transactions before transfer.",
        default=None,
    )
    parser.add_argument(
        "--apply_rule_groups",
        type=str,
        nargs="*",
        help="List of rule group titles to apply after transferring transactions.",
        default=None,
    )
    parser.add_argument(
        "--apply_rules",
        action="store_true",
        help=(
            "Let Firefly III run all of its rules on each transaction when it is imported. "
            "Cannot be combined with --apply_rule_groups."
        ),
    )
    parser.add_argument(
        "--bills_directory",
        type=str,
        help="Directory of bill documents to map onto the transferred transactions.",
        default=None,
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Enrich and report without transferring or archiving anything.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include raw LLM responses in the enrichment report.",
    )


def defineConvertParser(subparsers: _SubParsersAction):
    """Define the `convert` subcommand and its arguments.

    Args:
        subparsers (_SubParsersAction): Subparser collection to which the
            convert parser is added.
    """
    parser: ArgumentParser = subparsers.add_parser(
        CommandType.CONVERT.value, help="Convert transaction data to Firefly III transactions (common)"
    )
    parser.add_argument(
        "source", type=str, choices=["barclays", "paypal", "trade_republic"], help="Source of the input data."
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input file to be converted.",
    )
    parser.add_argument(
        "--output",
        default=".",
        type=str,
        help="Path to the output directory where the converted data will be saved.",
    )
    parser.add_argument(
        "--file_name",
        default="transactions",
        type=str,
        help="Name of the output file (without extension).",
    )
    parser.add_argument(
        "--account_name", type=str, help="Name of the account to assign to loaded transactions.", default=None
    )
    parser.add_argument(
        "--filter_query",
        type=str,
        help="Optional data query to filter transactions before conversion.",
        default=None,
    )


PARSER_DEFINITIONS: List[Callable[[_SubParsersAction], None]] = [
    defineConvertParser,
    defineTransferParser,
]


def convert(arguments: Namespace):
    """Load source data, convert to Firefly format, and save as CSV.

    Args:
        arguments (Namespace): Parsed CLI arguments.
    """
    logger.info(f"Starting convert command for source: {arguments.source}")
    logger.debug(f"Input file: {arguments.input_file}")

    loader = ldb.loaderMapping[arguments.source](arguments.input_file, accountName=arguments.account_name)
    logger.info(f"Loading transactions from {arguments.source}")
    transactions = loader.load()
    logger.info(f"Loaded {len(transactions)} transactions")

    converter = cdt.ConvertData(transactions)

    if arguments.filter_query:
        logger.info(f"Applying filter query: {arguments.filter_query}")
        converter = converter.filterByQuery(arguments.filter_query)
        logger.info(f"After filtering: {len(converter.transactions)} transactions remain")

    output_path = f"{arguments.output}/{arguments.file_name}.csv"
    logger.info(f"Saving converted transactions to: {output_path}")
    converter.saveCsv(filePath=output_path)
    logger.info("Convert command completed successfully")


def transfer(arguments: Namespace):
    """Load source data and push transactions to Firefly via the configured interface.

    When a bills directory is configured, matching transactions are enriched
    with data read from their bills before the batch is transferred.

    Args:
        arguments (Namespace): Parsed CLI arguments.
    """
    logger.info(f"Starting transfer command for source: {arguments.source}")

    inputName = arguments.source if arguments.input_name is None else arguments.input_name
    accountName = arguments.source if arguments.account_name is None else arguments.account_name
    inputFile = f"{arguments.input_directory}/{inputName}"
    logger.debug(f"Input file: {inputFile}, Account: {accountName}")

    loader = ldb.loaderMapping[arguments.source](inputFile, accountName=accountName)
    logger.info(f"Loading transactions from {inputFile}")
    transactions = loader.load()
    logger.info(f"Loaded {len(transactions)} transactions")

    logger.info(f"Loading Firefly interface configuration from {arguments.config_path}")
    config = toml.load(arguments.config_path)
    if "firefly_interface" not in config:
        raise ValueError("Configuration file must contain a [firefly_interface] section")
    interface = ffi.FireflyInterface(**config["firefly_interface"])
    logger.debug("Firefly interface initialized successfully")

    if arguments.filter_query:
        logger.info(f"Applying filter query: {arguments.filter_query}")
        transactions = cdt.ConvertData(transactions).filterByQuery(arguments.filter_query).transactions
        logger.info(f"After filtering: {len(transactions)} transactions remain")

    billConfig = None
    enricher = None
    report = None
    billDirectory = _configuredBillDirectory(arguments, config)
    if billDirectory:
        billConfig = _loadBillConfig(config, billDirectory)

    _validateRuleUsage(bool(arguments.apply_rules), arguments.apply_rule_groups, billConfig)

    verbose = arguments.verbose if billConfig is not None else False
    if billConfig is not None:
        enricher, report = _runEnrichment(config, interface, billConfig, transactions, accountName)
        _writeReport(billConfig.report_path, report, verbose=verbose)

    matchedTransactionIds = _matchedTransactionIds(report)
    autoLabeled = billDirectory is not None
    applyRulesRequested = bool(arguments.apply_rules)

    if arguments.dry_run:
        for transaction in transactions:
            applyRules = _rulesApplyTo(transaction, matchedTransactionIds, applyRulesRequested)
            _tagAutoLabeled(transaction, applyRules, autoLabeled)
            logger.info(
                f"[dry-run] {transaction.date} | {transaction.amount} | {transaction.description} | "
                f"category={transaction.category_name} | tags={transaction.tags} | apply_rules={applyRules}"
            )
        logger.info("Dry run completed; no transactions were transferred")
        return

    logger.info(f"Transferring {len(transactions)} transactions to Firefly III")
    processed_count = 0
    rulesAppliedCount = 0
    matchedBillPaths = _matchedBillPaths(report)
    for transaction in transactions:
        applyRules = _rulesApplyTo(transaction, matchedTransactionIds, applyRulesRequested)
        _tagAutoLabeled(transaction, applyRules, autoLabeled)
        response = interface.createTransaction(transaction, apply_rules=applyRules)
        billPaths = matchedBillPaths.get(id(transaction), [])
        if billPaths and response.status_code != 422:
            journalId = _transactionJournalId(response)
            for billPath in billPaths:
                with bls.prepareBillUpload(billPath) as (uploadPath, filename):
                    interface.uploadAttachment(uploadPath, journalId, filename)
        processed_count += 1
        if applyRules:
            rulesAppliedCount += 1
        if response.status_code == 200:
            logger.debug(f"Transaction {processed_count}/{len(transactions)} created successfully (status: {response.status_code})")
        else:
            logger.info(f"Transaction {processed_count}/{len(transactions)} processed with status: {response.status_code}")

    logger.info(f"Transfer command completed successfully. Processed {processed_count} transactions")
    if arguments.apply_rules:
        logger.info(
            f"Firefly III rules applied on import to {rulesAppliedCount} transaction(s); "
            f"{len(matchedTransactionIds)} bill-matched transaction(s) were left untouched"
        )

    if enricher is not None and billConfig.move_processed:
        enricher.archiveProcessed(report)

    if arguments.apply_rule_groups:
        logger.info(f"Applying rule groups: {arguments.apply_rule_groups}")
        for rule_group_title in arguments.apply_rule_groups:
            response = interface.applyRuleGroup(rule_group_title)
            if response.status_code == 204:
                logger.info(f"Rule group '{rule_group_title}' applied successfully.")
            else:
                logger.warning(f"Failed to apply rule group '{rule_group_title}'. Status code: {response.status_code}")


def _configuredBillDirectory(arguments: Namespace, config: dict) -> Optional[str]:
    """Return the bills directory that enables enrichment, or None.

    Enrichment is opt-in: it runs only when a directory is supplied on the
    command line or set as ``directory`` in the ``[bills]`` section, so simply
    having other ``[bills]`` settings does not change the transfer behaviour.

    Args:
        arguments (Namespace): Parsed CLI arguments.
        config (dict): Parsed configuration file.

    Returns:
        Optional[str]: The bills directory, or None when enrichment is off.
    """
    return arguments.bills_directory or config.get("bills", {}).get("directory")


def _loadBillConfig(config: dict, directory: str) -> bce.BillConfig:
    """Build the bill enrichment configuration from the config file.

    Args:
        config (dict): Parsed configuration file.
        directory (str): Bills directory to use.

    Returns:
        bce.BillConfig: Enrichment configuration.

    Raises:
        TypeError: If the ``[bills]`` section contains unknown keys.
    """
    section = dict(config.get("bills", {}))
    section["directory"] = directory
    return bce.BillConfig(**section)


def _validateRuleUsage(
    applyRules: bool,
    applyRuleGroups: Optional[List[str]],
    billConfig: Optional[bce.BillConfig],
) -> None:
    """Reject rule requests that would label transactions twice or overwrite bills.

    ``--apply_rules`` and ``--apply_rule_groups`` are two different Firefly III
    mechanisms; running both on one import would apply the rules twice. Rule
    groups are also rejected together with bill enrichment, because triggering a
    group rewrites stored transactions and would overwrite the values the LLM
    wrote from the bills.

    Args:
        applyRules (bool): Whether the per-transaction rule flag was requested.
        applyRuleGroups (Optional[List[str]]): Rule group titles from the command line.
        billConfig (Optional[bce.BillConfig]): Enrichment configuration, or None when off.

    Raises:
        ValueError: If both rule mechanisms are requested, or rule groups are
            combined with bill enrichment.
    """
    if applyRules and applyRuleGroups:
        raise ValueError(
            "--apply_rules and --apply_rule_groups cannot be combined: Firefly III would "
            "run its rules twice on the same transactions"
        )
    if billConfig is not None and applyRuleGroups:
        raise ValueError(
            "Rule groups cannot be combined with bill enrichment because they would "
            "overwrite the category and tags written from the bills"
        )


def _matchedTransactionIds(report: Optional[bce.EnrichmentReport]) -> set[int]:
    """Return the identities of the transactions a bill was applied to.

    Args:
        report (Optional[bce.EnrichmentReport]): Enrichment report, or None when off.

    Returns:
        set[int]: ``id()`` of every enriched transaction.
    """
    if report is None:
        return set()
    return {id(transaction) for transaction in report.matched_transactions}


def _matchedBillPaths(report: Optional[bce.EnrichmentReport]) -> dict[int, list[str]]:
    """Map each matched transaction identity to all contributing bill paths."""
    if report is None:
        return {}
    if len(report.matched) != len(report.matched_transactions):
        raise ValueError("Bill enrichment report has mismatched matched records and transactions")
    return {
        id(transaction): [record.bill_path, *(bill.path for bill in record.additional_bills)]
        for record, transaction in zip(report.matched, report.matched_transactions)
    }


def _transactionJournalId(response) -> str:
    """Extract the Firefly transaction journal ID from a create response."""
    try:
        splits = response.json()["data"]["attributes"]["transactions"]
        journalId = splits[0]["transaction_journal_id"]
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError("Firefly III did not return a transaction journal ID") from error
    if journalId is None or not str(journalId).strip():
        raise ValueError("Firefly III returned an empty transaction journal ID")
    return str(journalId)


def _rulesApplyTo(transaction: data.BaseTransaction, matchedTransactionIds: set[int], requested: bool) -> bool:
    """Return whether Firefly III should run its rules for this transaction.

    Bill-enriched transactions never qualify, so the LLM output stays intact.

    Args:
        transaction (data.BaseTransaction): Transaction about to be posted.
        matchedTransactionIds (set[int]): Identities of bill-enriched transactions.
        requested (bool): Whether per-transaction rule application was requested.

    Returns:
        bool: True when Firefly III should run its rules at import.
    """
    return requested and id(transaction) not in matchedTransactionIds


def _tagAutoLabeled(transaction: data.BaseTransaction, applyRules: bool, autoLabeled: bool) -> None:
    """Add the auto-label audit tag to a transaction that rules labelled at import.

    The tag is only written for imports that also use bill enrichment, where it
    distinguishes the rule-labelled transactions from the bill-labelled ones.

    Args:
        transaction (data.BaseTransaction): Transaction to tag in place.
        applyRules (bool): Whether Firefly III runs its rules for this transaction.
        autoLabeled (bool): Whether bill enrichment is active for this import.
    """
    if not (applyRules and autoLabeled):
        return
    tags = list(transaction.tags or [])
    if AUTO_LABELED_TAG not in tags:
        transaction.tags = tags + [AUTO_LABELED_TAG]


def _accountNamesForBills(
    interface: ffi.FireflyInterface,
    accountName: Optional[str],
    enabled: bool,
    accountTypes: Optional[List[str]] = None,
) -> List[str]:
    """Return the account names a bill may be mapped to.

    Only accounts that are not disabled are offered, and the account the
    transactions are imported into is skipped so a bill can never become its
    own counter-account.

    Args:
        interface (ffi.FireflyInterface): Interface used to read the existing accounts.
        accountName (Optional[str]): Account the transactions are imported into.
        enabled (bool): Whether the bills may set the counter-account.
        accountTypes (Optional[List[str]]): Allowed Firefly account types.

    Returns:
        List[str]: Account names offered to the reader, empty when disabled.
    """
    if not enabled:
        return []
    logger.info("Loading existing accounts from Firefly III")
    accounts = interface.getAccounts()
    allowedTypes = {"expense"} if accountTypes is None else set(accountTypes)
    return [
        account.name
        for account in accounts
        if account.active is not False
        and (accountName is None or account.name.casefold() != accountName.casefold())
        and account.type in allowedTypes
    ]


def _runEnrichment(
    config: dict,
    interface: ffi.FireflyInterface,
    billConfig: bce.BillConfig,
    transactions: List[data.BaseTransaction],
    accountName: Optional[str],
) -> tuple[bce.BillEnricher, bce.EnrichmentReport]:
    """Read bills with the local LLM and enrich the matching transactions.

    Args:
        config (dict): Parsed configuration file, expected to hold an ``[llm]`` section.
        interface (ffi.FireflyInterface): Interface used to read existing categories, tags and accounts.
        billConfig (bce.BillConfig): Enrichment configuration.
        transactions (List[data.BaseTransaction]): Transactions of the current import.
        accountName (Optional[str]): Account the transactions are imported into.

    Returns:
        tuple[bce.BillEnricher, bce.EnrichmentReport]: The enricher and the per-bill report.
    """
    llmSection = config.get("llm", {})
    client = lli.LLMInterface(
        base_url=llmSection.get("base_url", "http://127.0.0.1:1234/v1"),
        model=llmSection.get("model", ""),
        timeout_s=llmSection.get("timeout_s", 120),
    )

    logger.info("Loading existing categories and tags from Firefly III")
    categories = interface.getCategories()
    tags = interface.getTags()
    accounts = _accountNamesForBills(interface, accountName, billConfig.accounts, billConfig.account_types)
    examples = bls.loadPromptExamples(
        billConfig.prompt_examples_directory,
        maxSplits=billConfig.max_split_bills,
        renderResolution=billConfig.render_resolution,
    )

    reader = bls.BillReader(
        client,
        categories,
        tags,
        accounts,
        vision=billConfig.vision,
        maxPages=billConfig.max_pages,
        renderResolution=billConfig.render_resolution,
        maxSplits=billConfig.max_split_bills,
        examples=examples,
    )
    enricher = bce.BillEnricher(reader, categories, tags, accounts, billConfig)
    report = enricher.enrich(transactions)
    return enricher, report


def _writeReport(path: str | None, report: bce.EnrichmentReport, verbose: bool = False) -> None:
    """Write the enrichment report to disk when a path is configured.

    Args:
        path (str | None): Destination of the report, or None to skip writing.
        report (bce.EnrichmentReport): Report to render.
        verbose (bool): Include raw LLM responses in the report.
    """
    if not path:
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(bce.renderReport(report, verbose=verbose))
    logger.info(f"Wrote bill enrichment report to {path}")


COMMAND_EXECUTION: Dict[CommandType, Callable[[Namespace], None]] = {
    CommandType.CONVERT: convert,
    CommandType.TRANSFER: transfer,
}
