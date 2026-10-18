import enum
import logging
from argparse import ArgumentParser, Namespace, _SubParsersAction
from typing import Callable, Dict, List

import toml

from fireflyConverter import billEnricher as bce
from fireflyConverter import bills as bls
from fireflyConverter import convertData as cdt
from fireflyConverter import data
from fireflyConverter import fireflyInterface as ffi
from fireflyConverter import llmInterface as lli
from fireflyConverter import loadData as ldb

logger = logging.getLogger(__name__)


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
    if arguments.bills_directory or "bills" in config:
        billConfig = _loadBillConfig(config, arguments.bills_directory)
        enricher, report = _runEnrichment(config, interface, billConfig, transactions)
        _writeReport(billConfig.report_path, report)

    if arguments.dry_run:
        if report is not None:
            print(bce.renderReport(report))
        for transaction in transactions:
            logger.info(
                f"[dry-run] {transaction.date} | {transaction.amount} | {transaction.description} | "
                f"category={transaction.category_name} | tags={transaction.tags}"
            )
        logger.info("Dry run completed; no transactions were transferred")
        return

    if enricher is not None and billConfig.move_processed:
        enricher.archiveProcessed(report)

    logger.info(f"Transferring {len(transactions)} transactions to Firefly III")
    processed_count = 0
    for transaction in transactions:
        response = interface.createTransaction(transaction)
        processed_count += 1
        if response.status_code == 200:
            logger.debug(f"Transaction {processed_count}/{len(transactions)} created successfully (status: {response.status_code})")
        else:
            logger.info(f"Transaction {processed_count}/{len(transactions)} processed with status: {response.status_code}")

    logger.info(f"Transfer command completed successfully. Processed {processed_count} transactions")

    if arguments.apply_rule_groups:
        logger.info(f"Applying rule groups: {arguments.apply_rule_groups}")
        for rule_group_title in arguments.apply_rule_groups:
            response = interface.applyRuleGroup(rule_group_title)
            if response.status_code == 204:
                logger.info(f"Rule group '{rule_group_title}' applied successfully.")
            else:
                logger.warning(f"Failed to apply rule group '{rule_group_title}'. Status code: {response.status_code}")


def _loadBillConfig(config: dict, directoryOverride: str | None) -> bce.BillConfig:
    """Build the bill enrichment configuration from the config file.

    Args:
        config (dict): Parsed configuration file.
        directoryOverride (str | None): Directory from ``--bills_directory``.

    Returns:
        bce.BillConfig: Enrichment configuration.

    Raises:
        ValueError: If no bills directory is configured.
    """
    section = dict(config.get("bills", {}))
    directory = directoryOverride or section.get("directory")
    if not directory:
        raise ValueError("Bill enrichment requires --bills_directory or a directory in [bills]")
    section["directory"] = directory
    return bce.BillConfig(**section)


def _runEnrichment(
    config: dict,
    interface: ffi.FireflyInterface,
    billConfig: bce.BillConfig,
    transactions: List[data.BaseTransaction],
) -> tuple[bce.BillEnricher, bce.EnrichmentReport]:
    """Read bills with the local LLM and enrich the matching transactions.

    Args:
        config (dict): Parsed configuration file, expected to hold an ``[llm]`` section.
        interface (ffi.FireflyInterface): Interface used to read existing categories and tags.
        billConfig (bce.BillConfig): Enrichment configuration.
        transactions (List[data.BaseTransaction]): Transactions of the current import.

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

    reader = bls.BillReader(client, categories, tags, vision=billConfig.vision, maxPages=billConfig.max_pages)
    enricher = bce.BillEnricher(reader, categories, tags, billConfig)
    report = enricher.enrich(transactions)
    return enricher, report


def _writeReport(path: str | None, report: bce.EnrichmentReport) -> None:
    """Write the enrichment report to disk when a path is configured.

    Args:
        path (str | None): Destination of the report, or None to skip writing.
        report (bce.EnrichmentReport): Report to render.
    """
    if not path:
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(bce.renderReport(report))
    logger.info(f"Wrote bill enrichment report to {path}")


COMMAND_EXECUTION: Dict[CommandType, Callable[[Namespace], None]] = {
    CommandType.CONVERT: convert,
    CommandType.TRANSFER: transfer,
}