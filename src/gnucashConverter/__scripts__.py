import argparse
import toml

from gnucashConverter import convertData as cdt
from gnucashConverter import loadData as ldb
from gnucashConverter import fireflyInterface as ffi


def convert():
    parser = argparse.ArgumentParser("data converter")
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input file to be converted.",
    )
    parser.add_argument(
        "output_file",
        type=str,
        help="Path to the output file where the converted data will be saved.",
    )
    parser.add_argument("--account_map", type=str, help="Path to the account map definitions.", default=None)
    parser.add_argument(
        "--source",
        type=str,
        choices=["barclays", "paypal", "trade_republic", "common"],
    )
    parser.add_argument("--account_name", type=str, help="Name of the account to assign to loaded transactions.", default=None)

    arguments = parser.parse_args()

    loader = ldb.loaderMapping[arguments.source](arguments.input_file, arguments.account_name)
    loader.load()

    try:
        accountMap = toml.load(arguments.account_map) if arguments.account_map else None
        converter = cdt.ConvertData(loader.load(), accountMap)
        converter.assignAccounts()
        converter.saveCsv(arguments.output_file)
    except Exception as e:
        print(f"An error occurred: {e}")

def transfer():
    parser = argparse.ArgumentParser("transaction transfer")
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input file to be converted.",
    )
    parser.add_argument(
        "--interface_config",
        type=str,
        help="Path to the interface configuration file.",
        required=True,
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["barclays", "paypal", "trade_republic"],
        required=True,
    )
    parser.add_argument("--account_name", type=str, help="Name of the account to assign to loaded transactions.", default=None)
    arguments = parser.parse_args()

    loader = ldb.loaderMapping[arguments.source](arguments.input_file, arguments.account_name)
    loader.load()

    try:
        interfaceConfig = toml.load(arguments.interface_config)
        interface = ffi.FireflyInterface(**interfaceConfig)

        for transaction in loader.transactions:
            response = interface.createTransaction(transaction)
            print(f"Processed transaction with response: {response.status_code}")

    except Exception as e:
        print(f"An error occurred: {e}")
