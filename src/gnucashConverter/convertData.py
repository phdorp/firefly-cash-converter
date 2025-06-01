from typing import List

import pandas as pd

from gnucashConverter import data


class ConvertData:
    def __init__(self, data: List[data.Transaction]):
        self._data = data

    def convert(self) -> pd.DataFrame:
        # Placeholder for conversion logic
        # This should be replaced with actual conversion code
        return pd.DataFrame(self._data)

    def saveCsv(self, filePath: str):
        """
        Save the transaction data to a CSV file.

        Args:
            filePath (str): The path where the CSV file will be saved.
        """
        separator = ";"
        self.convert().to_csv(filePath, sep=separator, index=False)
