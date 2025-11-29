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
        """Return the list of parsed transactions.

        Returns:
            List[data.Transaction]: Currently-loaded transactions.
        """
        return self._data

    def __init__(self, dataPath: str):
        """Initialize the data loader with the path to the data file.

        Args:
            dataPath (str): Filesystem path to the data file to be loaded.
        """
        self._dataPath = dataPath
        self._data: List[data.Transaction] = []
        self._fieldNames: List[str] = [field.name for field in dc.fields(data.Transaction)]
        self._fieldTypes: List[type] = [str, str, float]
        self._fieldAliases: Dict[str, Fields] = {fieldName: Fields[fieldName.upper()] for fieldName in self._fieldNames}
        self._fieldFilters: List[Callable[[str], str]] = [lambda content: content for _ in self._fieldNames]

    @abc.abstractmethod
    def load(self):
        """Load and parse data from the source file into `self._data`.

        Implementations should populate `self._data` with a list of
        `data.Transaction` instances parsed from the file located at
        `self._dataPath`.
        """

class TableDataLoader(DataLoader):    
    """
    Base class for data loaders that operate on tabular data formats (e.g., CSV and Excel).
    Introduces the headerRowIdx attribute to specify the index of the header row in the data file.
    """
    def __init__(self, headerRowIdx: int, dataPath: str):
        """Initialize a table-style loader.

        Args:
            headerRowIdx (int): Index of the header row inside the tabular
                data (used to locate column names).
            dataPath (str): Path to the source data file.
        """
        self._headerRowIdx = headerRowIdx
        super().__init__(dataPath)

    def _getTransactions(self, dataFrame: pd.DataFrame, colIdcs: List[int]) -> List[data.Transaction]:
        """Extract transactions from a tabular DataFrame using resolved column indices.

        This helper iterates over data rows after the header row (as defined by
        `self._headerRowIdx`), applies any field filters and type conversions,
        and constructs `data.Transaction` objects.

        Args:
            dataFrame (pd.DataFrame): The loaded table-like data.
            colIdcs (List[int]): Column indices aligned with `self._fieldAliases`.

        Returns:
            List[data.Transaction]: Parsed transactions.
        """
        transactions: List[data.Transaction] = []
        for rowIdx in range(self._headerRowIdx + 1, dataFrame.shape[0]):
            # Create a dictionary to hold the current transaction data
            row = dataFrame.values[rowIdx]
            transactionData: Dict[str, Any] = {}
            for colIdx, fieldAlias in zip(colIdcs, self._fieldAliases):
                field = self._fieldAliases[fieldAlias]
                transactionData[self._fieldNames[field]] = self._fieldTypes[field](self._fieldFilters[field](row[colIdx]))

            # Only add the transaction if it contains data
            if len(transactionData) > 0:
                transactions.append(data.Transaction(**transactionData))

        return transactions

    @abc.abstractmethod
    def _parseData(self, dataFrame: pd.DataFrame) -> List[data.Transaction]:
        """Parse the data from the DataFrame.

        Args:
            dataFrame (pd.DataFrame): The DataFrame to parse.
        
        Returns:
            List[data.Transaction]: Parsed transaction data.
        """
        
class DataLoaderXlsx(TableDataLoader):

    def __init__(self, headerRowIdx: int, dataPath: str):
        """Create an XLSX table loader.

        Args:
            headerRowIdx (int): Index of the header row in the spreadsheet.
            dataPath (str): Path to the Excel file.
        """
        super().__init__(headerRowIdx, dataPath)

    def load(self):
        """Load data from an Excel file and populate ``self._data``.

        This method reads the Excel file at ``self._dataPath`` and calls
        ``_parseData`` to convert the loaded ``DataFrame`` into
        ``data.Transaction`` objects which are stored in ``self._data``.
        """
        self._data = self._parseData(pd.read_excel(self._dataPath))

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
        """Create a CSV table loader.

        Args:
            separator (str): Delimiter used in the CSV file.
            headerRowIdx (int): Index of the header row inside the CSV data.
            dataPath (str): Path to the CSV file.
        """
        self._separator = separator
        super().__init__(headerRowIdx, dataPath)

    def load(self):
        """Load data from a CSV file and populate ``self._data``.

        Reads the CSV at ``self._dataPath`` using the configured
        ``self._separator`` and passes the resulting ``DataFrame`` to
        ``_parseData``. The parsed transactions are stored in
        ``self._data``.
        """
        self._data = self._parseData(pd.read_csv(self._dataPath, sep=self._separator, header=None))

class DataLoaderPaypal(DataLoaderCsv):

    def __init__(self, dataPath):
        """Initialize a PayPal CSV loader.

        Args:
            dataPath (str): Path to the PayPal CSV file.
        """
        super().__init__(separator=',', headerRowIdx=0, dataPath=dataPath)

        self._fieldAliases = {"Beschreibung": Fields.DESCRIPTION, "Datum": Fields.DATE, "Brutto": Fields.DEPOSIT}
        self._fieldFilters = [lambda content: content.replace('"', "") for _ in self._fieldFilters]
        # Convert German-formatted numbers (e.g., "1.234,56 €") to standard float format ("1234.56")
        self._fieldFilters[Fields.DEPOSIT] = lambda content: content.replace('"', "").replace(",", ".")

    def _parseData(self, dataFrame: pd.DataFrame) -> List[data.Transaction]:
        """Parse the data from a PayPal CSV-formatted DataFrame.

        This method locates the PayPal CSV header row (as configured by
        ``headerRowIdx``) to determine the column indices for the fields
        listed in ``self._fieldAliases`` and returns the parsed
        transactions.

        Args:
            dataFrame (pd.DataFrame): The CSV data as a DataFrame.

        Returns:
            List[data.Transaction]: Parsed transactions.
        """
        # Get column indices of the target fields
        colIdcs: List[int] = []
        for fieldAlias in self._fieldAliases:
            colIdcs.append(np.where(dataFrame.values[self._headerRowIdx, :] == fieldAlias)[0][0])

        return self._getTransactions(dataFrame, colIdcs)
    
class DataLoaderBarclays(DataLoaderXlsx):

    def __init__(self, dataPath):
        """Initialize a Barclays XLSX loader.

        Args:
            dataPath (str): Path to the Barclays Excel file.
        """
        super().__init__(headerRowIdx=11, dataPath=dataPath)

        self._fieldAliases = {"Beschreibung": Fields.DESCRIPTION, "Buchungsdatum": Fields.DATE, "Originalbetrag": Fields.DEPOSIT}
        # Convert German-formatted numbers (e.g., "1.234,56 €") to standard float format ("1234.56")
        self._fieldFilters[Fields.DEPOSIT] = lambda content: content.replace(".", "").replace(",", ".").replace(" €", "")  

    def _parseData(self, dataFrame: pd.DataFrame) -> List[data.Transaction]:
        """Parse the data from a Barclays Excel ``DataFrame``.

        Locates the header row at ``self._headerRowIdx`` to determine the
        column indices for the fields in ``self._fieldAliases`` and
        returns a list of parsed ``data.Transaction`` objects.

        Args:
            dataFrame (pd.DataFrame): The spreadsheet data as a DataFrame.

        Returns:
            List[data.Transaction]: Parsed transactions.
        """

        # Determine the column indices for the transaction fields
        colIdcs: List[int] = []
        for fieldAlias in self._fieldAliases:
            fieldIdcs = np.where(dataFrame.values[self._headerRowIdx, :] == fieldAlias)[0]
            if fieldIdcs.size == 1:
                colIdcs.append(int(fieldIdcs))
            else:
                colIdcs.append(int(fieldIdcs[0]))

        return self._getTransactions(dataFrame, colIdcs)

loaderMapping = {"barclays": DataLoaderBarclays, "paypal": DataLoaderPaypal}
