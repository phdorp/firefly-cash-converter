from typing import List, Dict, Optional

import pandas as pd
import re

from gnucashConverter import data


class ConvertData:
    """Transaction data converter with account mapping and CSV export.

    Handles conversion of BaseTransaction objects by mapping transaction descriptions
    to accounts using regex patterns and supports exporting transaction data to CSV format.

    Attributes:
        _transactions (List[data.BaseTransaction]): List of transactions to process.
        _unmappedAccountName (str): Default account name for unmapped transactions.
        _accountMap (Dict[str, str]): Mapping of account names to description regex patterns.
    """

    @property
    def transactions(self) -> List[data.BaseTransaction]:
        """Return the list of transactions to be converted.

        Returns:
            List[data.BaseTransaction]: Currently-loaded transactions.
        """
        return self._transactions

    def __init__(self, data: List[data.BaseTransaction], accountMap: Optional[Dict[str, str]] = None):
        """Initialize the converter with transaction data and optional account mapping.

        Args:
            data (List[data.BaseTransaction]): List of transactions to convert.
            accountMap (Optional[Dict[str, str]]): Mapping of account names to description patterns.
                Keys are account names, values are regex patterns to match in transaction descriptions.
                Defaults to None (empty mapping).
        """
        self._transactions = data
        self._unmappedAccountName = "Imbalance-EUR"
        self._accountMap = accountMap if accountMap is not None else {}

    def _findAccountName(self, description: str) -> str:
        """Find the account name for a transaction based on its description.

        Searches through the configured account map patterns to find a matching
        account for the given transaction description. If no match is found,
        returns the unmapped account name.

        Args:
            description (str): The transaction description to search.

        Returns:
            str: The account name if a pattern matches, otherwise the unmapped account name.
        """
        for accountName, descriptionPattern in self._accountMap.items():
            if re.search(descriptionPattern, description):
                return accountName
        return self._unmappedAccountName

    def assignAccounts(self) -> None:
        """Assign accounts to transactions based on description pattern matching.

        Iterates through all transactions and assigns source or destination account names
        based on the transaction type and pattern matching against the account map.
        For withdrawals, the account is assigned as the destination. For deposits, the
        account is assigned as the source.

        Raises:
            ValueError: If a transaction has an unknown or invalid type.
        """
        for transaction in self._transactions:
            accountName = self._findAccountName(transaction.description)

            if transaction.type is data.TransactionType.WITHDRAWAL.value:
                transaction.destination_name = accountName
            elif transaction.type is data.TransactionType.DEPOSIT.value:
                transaction.source_name = accountName
            else:
                raise ValueError(f"Unknown transaction type: {transaction.type}")

    def _convert(self) -> pd.DataFrame:
        """Convert transaction data to a pandas DataFrame.

        Converts the internal transaction list to a DataFrame representation.
        This method provides a foundation for further data transformations or exports.

        Returns:
            pd.DataFrame: DataFrame representation of the transactions.
        """
        # Placeholder for conversion logic
        # This should be replaced with actual conversion code
        return pd.DataFrame(self._transactions)

    def saveCsv(self, filePath: str):
        """Save the transaction data to a CSV file.

        Converts the internal transaction data to a DataFrame and exports it
        to a CSV file with comma separation.

        Args:
            filePath (str): The file path where the CSV file will be saved.
        """
        separator = ","
        self._convert().to_csv(filePath, sep=separator, index=False)
