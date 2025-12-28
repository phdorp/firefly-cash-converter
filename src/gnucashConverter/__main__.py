from argparse import ArgumentParser, Namespace, _SubParsersAction
import toml
import subprocess
import enum
from typing import List, Callable, Dict
import logging
import sys

from gnucashConverter import convertData as cdt
from gnucashConverter import loadData as ldb
from gnucashConverter import fireflyInterface as ffi


class CommandType(enum.Enum):
    CONVERT = "convert"
    TRANSFER = "transfer"


def main():
    parser = ArgumentParser("cash")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for defineParser in PARSER_DEFINITIONS:
        defineParser(subparsers)

    arguments: Namespace = parser.parse_args()
    COMMAND_EXECUTION[CommandType(arguments.command)](arguments)


def defineTransferParser(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        CommandType.TRANSFER.value, help="Transfer transactions to Firefly III"
    )
    parser.add_argument(
        "source",
        type=str,
        choices=["barclays", "paypal", "trade_republic", "common", "pytr"],
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


def defineConvertParser(subparsers: _SubParsersAction):
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
    loader = ldb.loaderMapping[arguments.source](arguments.input_file, accountName=arguments.account_name)
    transactions = loader.load()

    converter = cdt.ConvertData(transactions)
    converter.saveCsv(filePath=f"{arguments.output}/{arguments.file_name}.csv")


def transfer(arguments: Namespace):
    if arguments.source == "pytr":
        subprocess.run(["pytr", "export_transactions", "--outputdir", ".tmp"])
        input_file = ".tmp/account_transactions.csv"
        source = "trade_republic"
    else:
        assert arguments.input_file is not None, "Input file must be provided for non-pytr sources."
        input_file = arguments.input_file
        source = arguments.source

    loader = ldb.loaderMapping[source](input_file, accountName=arguments.account_name)
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
