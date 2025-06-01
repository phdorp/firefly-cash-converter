import argparse

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
    parser.add_argument("--source", type=str, choices=["barclays", "paypal"],)

    arguments = parser.parse_args()

    loader = ldb.loaderMapping[arguments.source](arguments.input_file)
    loader.load()

    converter = cdt.ConvertData(loader.data)
    converter.saveCsv(arguments.output_file)

if __name__ == "__main__":
    main()