import abc
import dataclasses as dc
import enum
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd

from gnucashConverter import data


class Fields(enum.IntEnum):
    DESCRIPTION = 0
    DATE = 1
    DEPOSIT = 2


class DataLoader(abc.ABC):
    @property
    def data(self) -> List[data.Transaction]:
        return self._data

    def __init__(self, dataPath: str):
        self._dataPath = dataPath
        self._data: List[data.Transaction] = []
        self._fieldNames: List[str] = [field.name for field in dc.fields(data.Transaction)]
        self._fieldTypes: List[type] = [str, str, float]
        self._fieldAliases: Dict[str, Fields] = {fieldName: Fields[fieldName.upper()] for fieldName in self._fieldNames}
        self._fieldFilters: List[Callable] = [lambda content: content for fieldName in self._fieldNames]

    @abc.abstractmethod
    def load(self):
        pass


class DataLoaderXlsx(DataLoader):

    def load(self):
        """
        Load data from an Excel file.

        Returns:
            pd.DataFrame: Data loaded from the Excel file.
        """
        self._data = self._parseData(pd.read_excel(self._dataPath))

    @abc.abstractmethod
    def _parseData(self, dataFrame: pd.DataFrame) -> List[data.Transaction]:
        """
        Parse the data from the DataFrame.

        Args:
            dataFrame (pd.DataFrame): The DataFrame to parse.

        Returns:
            List[data.Transaction]: Parsed transaction data.
        """


class DataLoaderBarclays(DataLoaderXlsx):

    def __init__(self, dataPath):
        super().__init__(dataPath)

        self._fieldAliases = {"Beschreibung": Fields.DESCRIPTION, "Buchungsdatum": Fields.DATE, "Originalbetrag": Fields.DEPOSIT}
        self._fieldFilters[Fields.DEPOSIT] = lambda content: content.replace(",", ".").replace(" €", "")
        self._headerRowIdx = 11

    def _parseData(self, dataFrame: pd.DataFrame) -> List[data.Transaction]:
        """
        Parse the data from the DataFrame specific to Barclays format.

        Args:
            dataFrame (pd.DataFrame): The DataFrame to parse.

        Returns:
            acc.Account: Parsed account data.
        """

        # Determine the column indices for the thought transaction fields
        colIdcs: List[int] = []
        for fieldAlias in self._fieldAliases:
            fieldIdcs = np.where(dataFrame.values[self._headerRowIdx, :] == fieldAlias)[0]
            if fieldIdcs.size == 1:
                colIdcs.append(int(fieldIdcs))
            else:
                colIdcs.append(int(fieldIdcs[0]))

        # Parse the transactions from the DataFrame
        transactions: List[data.Transaction] = []
        for rowIdx in range(self._headerRowIdx + 1, dataFrame.shape[0]):
            # Create a dictionary to hold the current transaction data
            transactionData: Dict[str, Any] = {}
            for colIdx, fieldAlias in zip(colIdcs, self._fieldAliases):
                content = dataFrame.values[rowIdx, colIdx]
                field = self._fieldAliases[fieldAlias]
                transactionData[self._fieldNames[field]] = self._fieldTypes[field](self._fieldFilters[field](content))

            # Only add the transaction if it contains data
            if len(transactionData) > 0:
                transactions.append(data.Transaction(**transactionData))

        return transactions
