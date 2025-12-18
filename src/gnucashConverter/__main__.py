import argparse
import toml

from gnucashConverter import convertData as cdt
from gnucashConverter import loadData as ldb


def main():
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
        choices=["barclays", "paypal", "trade_republic"],
    )

    arguments = parser.parse_args()

    loader: ldb.DataLoader = ldb.loaderMapping[arguments.source](arguments.input_file)

    try:
        accountMap = toml.load(arguments.account_map) if arguments.account_map else None
        converter = cdt.ConvertData(loader.load(), accountMap)
        converter.assignAccounts()
        converter.saveCsv(arguments.output_file)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
