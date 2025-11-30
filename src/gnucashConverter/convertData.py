from typing import List

import pandas as pd
import re

from gnucashConverter import data


class ConvertData:
    @property
    def transactions(self) -> List[data.Transaction]:
        """Return the list of transactions to be converted.

        Returns:
            List[data.Transaction]: Currently-loaded transactions.
        """
        return self._transactions

    def __init__(self, data: List[data.Transaction], accountMap: dict[str, str] = None):
        self._transactions = data
        self._unmappedAccountName = "Imbalance-EUR"
        self._accountMap = accountMap if accountMap is not None else {}

    def _findAccountName(self, description: str) -> str:
        for accountName, descriptionPattern in self._accountMap.items():
            if re.search(descriptionPattern, description):
                return accountName
        return self._unmappedAccountName

    def assignAccounts(self) -> None:
        for transaction in self._transactions:
            transaction.AccountName = self._findAccountName(transaction.Description)

    def _convert(self) -> pd.DataFrame:
        # Placeholder for conversion logic
        # This should be replaced with actual conversion code
        return pd.DataFrame(self._transactions)

    def saveCsv(self, filePath: str):
        """
        Save the transaction data to a CSV file.

        Args:
            filePath (str): The path where the CSV file will be saved.
        """
        separator = ","
        self._convert().to_csv(filePath, sep=separator, index=False)
