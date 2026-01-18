import enum
import logging
from argparse import ArgumentParser, Namespace, _SubParsersAction
from typing import Callable, Dict, List

import toml

from fireflyConverter import convertData as cdt
from fireflyConverter import fireflyInterface as ffi
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


COMMAND_EXECUTION: Dict[CommandType, Callable[[Namespace], None]] = {
    CommandType.CONVERT: convert,
    CommandType.TRANSFER: transfer,
}
