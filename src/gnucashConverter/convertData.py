from typing import List, Dict, Optional

import pandas as pd
import re

from gnucashConverter import data


class ConvertData:
    @property
    def transactions(self) -> List[data.BaseTransaction]:
        """Return the list of transactions to be converted.

        Returns:
            List[data.Transaction]: Currently-loaded transactions.
        """
        return self._transactions

    def __init__(self, data: List[data.BaseTransaction], accountMap: Optional[Dict[str, str]] = None):
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
            accountName = self._findAccountName(transaction.description)

            if transaction.type is data.TransactionType.WITHDRAWAL:
                transaction.destination_name = accountName
            elif transaction.type is data.TransactionType.DEPOSIT:
                transaction.source_name = accountName
            else:
                raise ValueError(f"Unknown transaction type: {transaction.type}")

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
