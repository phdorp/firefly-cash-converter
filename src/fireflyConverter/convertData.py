import re
import tomllib
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from fireflyConverter import data


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

    @property
    def queries(self) -> Dict[str, str]:
        """Return the currently-loaded query definitions.

        Returns:
            Dict[str, str]: Currently-loaded query definitions.
        """
        return self._queries

    @queries.setter
    def queries(self, queries: Dict[str, str] | str) -> None:
        """Set the query definitions.

        Args:
            queries (Dict[str, str] | str): Query definitions to set.
        """
        if isinstance(queries, str):
            self._queries = self._loadQueryConfig(queries)
        else:
            self._queries = queries

    def __init__(
        self,
        data: List[data.BaseTransaction],
        accountMap: Optional[Dict[str, str]] = None,
        queries: Optional[Dict[str, str] | str] = None,
    ):
        """Initialize the converter with transaction data and optional account mapping.

        Args:
            data (List[data.BaseTransaction]): List of transactions to convert.
            accountMap (Optional[Dict[str, str]]): Mapping of account names to description patterns.
                Keys are account names, values are regex patterns to match in transaction descriptions.
                Defaults to None (empty mapping).
            queries (Optional[Dict[str, str] | str]): Query definitions for filtering transactions.
                Can be a dictionary of query definitions or a path to a TOML config file.
                Defaults to None (empty queries).
        """
        self._transactions = data
        self._unmappedAccountName = ""
        self._accountMap = accountMap if accountMap is not None else {}
        self.queries = queries if queries is not None else {}

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

    def filterByQuery(self, query: str) -> "ConvertData":
        """Filter transactions using a pandas query expression.

        The query string uses pandas query syntax. Common examples:
        - "amount > 100"
        - "type == 'withdrawal'"
        - "amount > 100 and type == 'withdrawal'"
        - "reconciled == True"
        - "date >= '2025-01-01' and date <= '2025-12-31'"

        Args:
            query (str): A pandas-compatible query expression.

        Returns:
            ConvertData: New ConvertData instance with filtered transactions.

        Raises:
            ValueError: If the query is invalid or fails to execute.
        """
        try:
            dataframe = self._convert()
            filtered_dataframe = dataframe.query(query)
            transactions = [data.BaseTransaction(**row.to_dict()) for _, row in filtered_dataframe.iterrows()]
            return ConvertData(transactions, self._accountMap, self._queries)
        except Exception as e:
            raise ValueError(f"Failed to execute query '{query}': {e}")

    def filterByNamedQuery(self, queryName: str) -> "ConvertData":
        """Apply a named query from the loaded configuration.

        Args:
            queryName (str): Name of the query as defined in the TOML configuration.

        Returns:
            ConvertData: New ConvertData instance with filtered transactions.

        Raises:
            ValueError: If the query name does not exist or execution fails.
        """
        if not self._queries:
            raise ValueError("No queries loaded.")

        if queryName not in self._queries:
            raise ValueError(f"Query '{queryName}' not found. Available queries: {', '.join(self._queries.keys())}")

        return self.filterByQuery(self._queries[queryName])

    def filterByNamedQueries(self, *queryNames: str, logic: str = "and") -> "ConvertData":
        """Apply multiple named queries combined with AND or OR logic.

        Args:
            *queryNames: Names of queries to apply.
            logic (str): "and" or "or" - how to combine query results. Defaults to "and".

        Returns:
            ConvertData: New ConvertData instance with filtered transactions.

        Raises:
            ValueError: If any query name doesn't exist or logic is invalid.
        """
        if logic not in ("and", "or"):
            raise ValueError("logic must be 'and' or 'or'")

        if not self._queries:
            raise ValueError("No queries loaded.")

        queries = []
        for queryName in queryNames:
            if queryName not in self._queries:
                raise ValueError(f"Query '{queryName}' not found. Available queries: {', '.join(self._queries.keys())}")
            queries.append(self._queries[queryName])

        combined_query = f" {logic} ".join(f"({q})" for q in queries)
        return self.filterByQuery(combined_query)

    def filterByNamedQueryExpression(self, parts: List[str]) -> "ConvertData":
        """Apply a sequence of named queries combined by explicit logic operators.

        The list must alternate query names and logic operators (`and` / `or`),
        starting and ending with a query name.

        Examples:
            ["large_transactions", "and", "deposits_only"]
            ["withdrawals_only", "or", "contains_interest"]
            ["deposits_only", "and", "large_transactions", "or", "contains_tax"]

        Args:
            parts (List[str]): Alternating query names and operators.

        Returns:
            ConvertData: New ConvertData instance with filtered transactions.

        Raises:
            ValueError: If queries are not loaded, the list is malformed, a query name
                is missing, or an operator is invalid.
        """
        if not self._queries:
            raise ValueError("No queries loaded.")

        if not parts:
            raise ValueError("Expression parts must not be empty.")

        if len(parts) % 2 == 0:
            raise ValueError("Expression must alternate query names and operators, starting with a query name.")

        combined_parts: List[str] = []
        for idx, token in enumerate(parts):
            if idx % 2 == 0:
                # Expect a query name
                if token not in self._queries:
                    raise ValueError(f"Query '{token}' not found. Available queries: {', '.join(self._queries.keys())}")
                combined_parts.append(f"({self._queries[token]})")
            else:
                # Expect an operator
                op = token.lower()
                if op not in ("and", "or"):
                    raise ValueError("Only 'and' or 'or' operators are supported.")
                combined_parts.append(f" {op} ")

        combined_query = "".join(combined_parts)
        return self.filterByQuery(combined_query)

    def listQueries(self) -> List[str]:
        """List all available named queries from the loaded configuration.

        Returns:
            List[str]: List of query names.
        """
        return list(self._queries.keys())

    @staticmethod
    def _loadQueryConfig(configPath: str) -> Dict[str, str]:
        """Load pandas query definitions from a TOML file.

        Args:
            configPath (str): Path to the TOML configuration file.

        Raises:
            FileNotFoundError: If the configuration file does not exist.
            ValueError: If the TOML file does not contain a [queries] section.
        """
        config_file = Path(configPath)
        if not config_file.exists():
            raise FileNotFoundError(f"Query configuration file not found: {configPath}")

        with open(config_file, "rb") as f:
            config = tomllib.load(f)

        if "queries" not in config:
            raise ValueError(f"Configuration file {configPath} must contain a [queries] section")

        return config["queries"]
