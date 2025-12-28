import enum
import logging
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from typing import Callable, Dict, List

import toml

from gnucashConverter import convertData as cdt
from gnucashConverter import fireflyInterface as ffi
from gnucashConverter import loadData as ldb


class CommandType(enum.Enum):
    CONVERT = "convert"
    TRANSFER = "transfer"


def main():
    """Parse CLI arguments and dispatch the selected subcommand.

    Creates the argument parser, registers subcommands, parses user input, and
    invokes the mapped command handler.

    Raises:
        KeyError: If the provided command does not have a registered handler.
    """
    parser = ArgumentParser("cash")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for defineParser in PARSER_DEFINITIONS:
        defineParser(subparsers)

    arguments: Namespace = parser.parse_args()
    COMMAND_EXECUTION[CommandType(arguments.command)](arguments)


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
    )
    parser.add_argument(
        "--interface_config",
        type=str,
        default="./config/fireflyInterface.toml",
        help="Path to the interface configuration file.",
    )
    parser.add_argument(
        "--account_name", type=str, help="Name of the account to assign to loaded transactions.", default=None
    )
    parser.add_argument(
        "--input_directory",
        type=str,
        help="Path to the input file to be converted.",
        default="tmp",
    )
    parser.add_argument(
        "--input_name",
        type=str,
        help="Name of the input file to be converted.",
        default=None,
        required=False,
    )


def defineConvertParser(subparsers: _SubParsersAction):
    """Define the `convert` subcommand and its arguments.

    Args:
        subparsers (_SubParsersAction): Subparser collection to which the
            convert parser is added.
    """
    parser: ArgumentParser = subparsers.add_parser(
        CommandType.CONVERT.value, help="Convert transaction data to Firefly III transactions"
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


PARSER_DEFINITIONS: List[Callable[[_SubParsersAction], None]] = [
    defineConvertParser,
    defineTransferParser,
]


def convert(arguments: Namespace):
    """Load source data, convert to Firefly format, and save as CSV.

    Args:
        arguments (Namespace): Parsed CLI arguments.
    """
    loader = ldb.loaderMapping[arguments.source](arguments.input_file, accountName=arguments.account_name)
    transactions = loader.load()

    converter = cdt.ConvertData(transactions)
    converter.saveCsv(filePath=f"{arguments.output}/{arguments.file_name}.csv")


def transfer(arguments: Namespace):
    """Load source data and push transactions to Firefly via the configured interface.

    Args:
        arguments (Namespace): Parsed CLI arguments.
    """
    inputName = arguments.source if arguments.input_name is None else arguments.input_name
    accountName = arguments.source if arguments.account_name is None else arguments.account_name
    inputFile = f"{arguments.input_directory}/{inputName}.csv"

    loader = ldb.loaderMapping[arguments.source](inputFile, accountName=accountName)
    transactions = loader.load()

    interfaceConfig = toml.load(arguments.interface_config)
    interface = ffi.FireflyInterface(**interfaceConfig)

    for transaction in transactions:
        response = interface.createTransaction(transaction)
        print(f"Processed transaction with response: {response.status_code}")


COMMAND_EXECUTION: Dict[CommandType, Callable[[Namespace], None]] = {
    CommandType.CONVERT: convert,
    CommandType.TRANSFER: transfer,
}

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log = logging.getLogger(__name__)
        log.info("Exiting...")
        sys.exit()
    except Exception as e:
        log = logging.getLogger(__name__)
        log.fatal(e)
        raise
