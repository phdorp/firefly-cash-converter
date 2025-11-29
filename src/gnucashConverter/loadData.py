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
        self._fieldFilters: List[Callable[[str], str]] = [lambda content: content for _ in self._fieldNames]

    @abc.abstractmethod
    def load(self):
        pass

class TableDataLoader(DataLoader):    
    """
    Base class for data loaders that operate on tabular data formats (e.g., CSV and Excel).
    Introduces the headerRowIdx attribute to specify the index of the header row in the data file.
    """
    def __init__(self, headerRowIdx: int, dataPath: str):
        self._headerRowIdx = headerRowIdx
        super().__init__(dataPath)
    
    def _getDataRow(self, dataFrame: pd.DataFrame, rowIdx: int) -> np.ndarray:
        return dataFrame.values[rowIdx]

    def _getTransactions(self, dataFrame: pd.DataFrame, colIdcs: List[int]) -> List[data.Transaction]:
        # Parse the transactions from the DataFrame
        transactions: List[data.Transaction] = []
        for rowIdx in range(self._headerRowIdx + 1, dataFrame.shape[0]):
            # Create a dictionary to hold the current transaction data
            row = self._getDataRow(dataFrame, rowIdx)
            transactionData: Dict[str, Any] = {}
            for colIdx, fieldAlias in zip(colIdcs, self._fieldAliases):
                field = self._fieldAliases[fieldAlias]
                transactionData[self._fieldNames[field]] = self._fieldTypes[field](self._fieldFilters[field](row[colIdx]))

            # Only add the transaction if it contains data
            if len(transactionData) > 0:
                transactions.append(data.Transaction(**transactionData))
        
        return transactions

class DataLoaderXlsx(TableDataLoader):

    def __init__(self, headerRowIdx: int, dataPath: str):
        super().__init__(headerRowIdx, dataPath)

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

    @abc.abstractmethod
    def _getDataRow(self, dataFrame: pd.DataFrame, rowIdx: int) -> np.ndarray:
        """
        Get the data row from the DataFrame.

        Args:
            dataFrame (pd.DataFrame): The DataFrame to get the row from.
            rowIdx (int): The index of the row to get.

        Returns:
            np.ndarray: The data row.
        """

class DataLoaderCsv(TableDataLoader): 
    """
    Data loader for CSV files.
    This class loads transaction data from a CSV file, using the specified separator and header row index.
    Args:
        separator (str): The delimiter used in the CSV file.
        headerRowIdx (int): The index of the header row in the CSV file.
        dataPath (str): Path to the CSV file to load.
    """   
    def __init__(self, separator: str, headerRowIdx: int, dataPath: str):
        self._separator = separator
        super().__init__(headerRowIdx, dataPath)

    def load(self):
        """
        Load data from a CSV file.

        Returns:
            pd.DataFrame: Data loaded from the CSV file.
        """
        self._data = self._parseData(pd.read_csv(self._dataPath, sep=self._separator, header=None))

    @abc.abstractmethod
    def _parseData(self, dataFrame: pd.DataFrame) -> List[data.Transaction]:
        """
        Parse the data from the DataFrame.

        Args:
            dataFrame (pd.DataFrame): The DataFrame to parse.
        
        Returns:
            List[data.Transaction]: Parsed transaction data.
        """

class DataLoaderPaypal(DataLoaderCsv):

    def __init__(self, dataPath):
        super().__init__(separator=',', headerRowIdx=0, dataPath=dataPath)

        self._fieldAliases = {"Beschreibung": Fields.DESCRIPTION, "Datum": Fields.DATE, "Brutto": Fields.DEPOSIT}
        self._fieldFilters = [lambda content: content.replace('"', "") for _ in self._fieldFilters]
        # Convert German-formatted numbers (e.g., "1.234,56 €") to standard float format ("1234.56")
        self._fieldFilters[Fields.DEPOSIT] = lambda content: content.replace('"', "").replace(",", ".")

    def _getDataRow(self, dataFrame: pd.DataFrame, rowIdx: int) -> np.ndarray:
        return dataFrame.values[rowIdx]

    def _parseData(self, dataFrame: pd.DataFrame) -> List[data.Transaction]:
        """
        Parse the data from the DataFrame specific to Barclays format.

        Args:
            dataFrame (pd.DataFrame): The DataFrame to parse.

        Returns:
            List[data.Transaction]: Parsed account data.
        """
        # Get column indices of the target fields
        colIdcs: List[int] = []
        for fieldAlias in self._fieldAliases:
            colIdcs.append(np.where(dataFrame.values[0, :] == fieldAlias)[0][0])

        return self._getTransactions(dataFrame, colIdcs)
    
class DataLoaderBarclays(DataLoaderXlsx):

    def __init__(self, dataPath):
        super().__init__(headerRowIdx=11, dataPath=dataPath)

        self._fieldAliases = {"Beschreibung": Fields.DESCRIPTION, "Buchungsdatum": Fields.DATE, "Originalbetrag": Fields.DEPOSIT}
        self._fieldFilters[Fields.DEPOSIT] = lambda content: content.replace(",", ".").replace(" €", "")

    def _getDataRow(self, dataFrame: pd.DataFrame, rowIdx: int) -> np.ndarray:
        return dataFrame.values[rowIdx]

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

        return self._getTransactions(dataFrame, colIdcs)

loaderMapping = {"barclays": DataLoaderBarclays, "paypal": DataLoaderPaypal}
