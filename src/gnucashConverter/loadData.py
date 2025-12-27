import abc
import dataclasses as dc
import enum
from typing import Any, Callable, Dict, List, get_args, Tuple, Optional
from types import UnionType, NoneType

import numpy as np
import pandas as pd

from gnucashConverter import data


class Fields(enum.IntEnum):
    description = 0
    date = 1
    amount = 2
    source_name = 3
    destination_name = 4
    type = 5


class DataLoader(abc.ABC):
    @property
    def transactions(self) -> List[data.BaseTransaction]:
        """Return the list of parsed transactions.

        Returns:
            List[data.Transaction]: Currently-loaded transactions.
        """
        return self._transactions

    def __init__(self, dataPath: str, accountName: Optional[str] = None):
        """Initialize the data loader with the path to the data file.

        Args:
            dataPath (str): Filesystem path to the data file to be loaded.
        """
        self._dataPath = dataPath
        self._accountName = str(accountName)
        self._transactions: List[data.BaseTransaction] = []

        self._fieldTypes: List[type] = []
        for field in dc.fields(data.BaseTransaction):
            if field.name in Fields.__members__:
                if isinstance(field.type, type):
                    self._fieldTypes.insert(Fields[field.name].value, field.type)
                elif isinstance(field.type, UnionType):
                    unionTypes: Tuple[type, NoneType] = get_args(field.type)
                    assert len(unionTypes) == 2 and unionTypes[1] is NoneType, "Second type must be NoneType"
                    self._fieldTypes.insert(Fields[field.name].value, unionTypes[0])

        self._fieldAliases: Dict[str, Fields] = {field.name: field for field in Fields}
        self._fieldFilters: List[Callable[[str], str]] = [lambda content: content for _ in Fields]
        self._fieldMergeSep = " - "  # Separator used when merging multiple entries into one field

    @abc.abstractmethod
    def load(self)-> List[data.Transaction]:
        """Load and parse data from the source file into `self._data`.

        Implementations should populate `self._data` with a list of
        `data.Transaction` instances parsed from the file located at
        `self._dataPath`.

        Returns:
            List[data.Transaction]: Parsed transactions.
        """


class TableDataLoader(DataLoader):
    """
    Base class for data loaders that operate on tabular data formats (e.g., CSV and Excel).
    Introduces the headerRowIdx attribute to specify the index of the header row in the data file.
    """

    def __init__(self, headerRowIdx: int, dataPath: str, accountName: Optional[str] = None):
        """Initialize a table-style loader.

        Args:
            headerRowIdx (int): Index of the header row inside the tabular
                data (used to locate column names).
            dataPath (str): Path to the source data file.
        """
        super().__init__(dataPath, accountName)
        self._headerRowIdx = headerRowIdx
        self._fieldFilters[Fields.description] = self._descriptionFilter  # Remove NaN descriptions

    @staticmethod
    def _descriptionFilter(content: str) -> str:
        """Filter function to clean up description fields.

        Args:
            content (str): Raw description content.

        Returns:
            str: Cleaned description.
        """
        if pd.isna(content):
            return ""

        return content.replace(",", ";")

    def _getTransactions(self, dataFrame: pd.DataFrame, colIdcs: List[int]) -> List[data.BaseTransaction]:
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
        transactions: List[data.BaseTransaction] = []
        for rowIdx in range(self._headerRowIdx + 1, dataFrame.shape[0]):
            # Create a dictionary to hold the current transaction data
            row = dataFrame.values[rowIdx]
            transactionData: Dict[str, Any] = {}
            for colIdx, fieldAlias in zip(colIdcs, self._fieldAliases):
                field = self._fieldAliases[fieldAlias]
                storedData = transactionData.get(field.name, None)
                inputData = self._fieldTypes[field](self._fieldFilters[field](row[colIdx]))

                if storedData is None:
                    transactionData[field.name] = inputData
                elif isinstance(inputData, str) and isinstance(storedData, str):
                    if inputData != "":
                        transactionData[field.name] += self._fieldMergeSep + inputData
                else:
                    raise ValueError(f"Cannot merge multiple values for non-string field {field.name}")

            # Only add the transaction if it contains data
            if len(transactionData) > 0:
                transactionType = transactionData.get(Fields.type.name, None)

                if transactionType is None:
                    isWithdrawal = transactionData[Fields.amount.name] < 0

                    if isWithdrawal:
                        transactionData[Fields.source_name.name] = self._accountName
                    else:
                        transactionData[Fields.destination_name.name] = self._accountName

                transactions.append(data.PostTransaction(**transactionData))

        return transactions

    def _parseData(self, dataFrame: pd.DataFrame) -> List[data.BaseTransaction]:
        """Parse the data from tabular data ``DataFrame``.

        Locates the header row at ``self._headerRowIdx`` to determine the
        column indices for the fields in ``self._fieldAliases`` and
        returns a list of parsed ``data.Transaction`` objects.

        Args:
            dataFrame (pd.DataFrame): The spreadsheet data as a DataFrame.

        Returns:
            List[data.Transaction]: Parsed transactions.
        """

        # Get column indices of the target fields
        colIdcs: List[int] = []
        for fieldAlias in self._fieldAliases:
            colIdcs.append(np.where(dataFrame.values[self._headerRowIdx, :] == fieldAlias)[0][0])

        return self._getTransactions(dataFrame, colIdcs)


class DataLoaderXlsx(TableDataLoader):

    def __init__(self, headerRowIdx: int, dataPath: str, accountName: Optional[str] = None):
        """Create an XLSX table loader.

        Args:
            headerRowIdx (int): Index of the header row in the spreadsheet.
            dataPath (str): Path to the Excel file.
        """
        super().__init__(headerRowIdx, dataPath, accountName)

    def load(self) -> List[data.Transaction]:
        """Load data from an Excel file and populate ``self._transactions``.

        This method reads the Excel file at ``self._dataPath`` and calls
        ``_parseData`` to convert the loaded ``DataFrame`` into
        ``data.Transaction`` objects which are stored in ``self._transactions``.

        Returns:
            List[data.Transaction]: Parsed transactions.
        """
        return self._parseData(pd.read_excel(self._dataPath))


class DataLoaderCsv(TableDataLoader):
    """
    Data loader for CSV files.
    This class loads transaction data from a CSV file, using the specified separator and header row index.
    Args:
        separator (str): The delimiter used in the CSV file.
        headerRowIdx (int): The index of the header row in the CSV file.
        dataPath (str): Path to the CSV file to load.
    """

    def __init__(self, separator: str, headerRowIdx: int, dataPath: str, accountName: Optional[str] = None):
        """Create a CSV table loader.

        Args:
            separator (str): Delimiter used in the CSV file.
            headerRowIdx (int): Index of the header row inside the CSV data.
            dataPath (str): Path to the CSV file.
        """
        self._separator = separator
        super().__init__(headerRowIdx, dataPath, accountName)

    def load(self) -> List[data.Transaction]:
        """Load data from a CSV file and populate ``self._transactions``.

        Reads the CSV at ``self._dataPath`` using the configured
        ``self._separator`` and passes the resulting ``DataFrame`` to
        ``_parseData``. The parsed transactions are stored in
        ``self._transactions``.

        Returns:
            List[data.Transaction]: Parsed transactions.
        """
        return self._parseData(pd.read_csv(self._dataPath, sep=self._separator, header=None))


class DataLoaderCommon(DataLoaderCsv):
    """
    Data loader for common CSV files.
    This class loads transaction data from a common CSV file format.
    Args:
        dataPath (str): Path to the CSV file to load.
    """

    def __init__(self, dataPath: str, accountName: Optional[str] = None):
        """Create a common CSV table loader.

        Args:
            dataPath (str): Path to the CSV file.
        """
        accountName = accountName if accountName is not None else "common"
        super().__init__(separator=",", headerRowIdx=0, dataPath=dataPath, accountName=accountName)


class DataLoaderPaypal(DataLoaderCsv):

    def __init__(self, dataPath: str, accountName: Optional[str] = None):
        """Initialize a PayPal CSV loader.

        Args:
            dataPath (str): Path to the PayPal CSV file.
        """
        accountName = accountName if accountName is not None else "paypal"
        super().__init__(separator=",", headerRowIdx=0, dataPath=dataPath, accountName=accountName)

        self._fieldAliases = {
            "Beschreibung": Fields.description,
            "Absender E-Mail-Adresse": Fields.description,
            "Name": Fields.description,
            "Datum": Fields.date,
            "Brutto": Fields.amount,
        }
        # Convert German-formatted numbers (e.g., "1.234,56 €") to standard float format ("1234.56")
        self._fieldFilters[Fields.amount] = lambda content: content.replace('"', "").replace(",", ".")
        self._fieldFilters[Fields.date] = lambda content: "-".join(str(content).split("T")[0].split(".")[::-1])


class DataLoaderBarclays(DataLoaderXlsx):

    def __init__(self, dataPath: str, accountName: Optional[str] = None):
        """Initialize a Barclays XLSX loader.

        Args:
            dataPath (str): Path to the Barclays Excel file.
        """
        accountName = accountName if accountName is not None else "barclays"
        super().__init__(headerRowIdx=11, dataPath=dataPath, accountName=accountName)

        self._fieldAliases = {
            "Beschreibung": Fields.description,
            "Händlerdetails": Fields.description,
            "Buchungsdatum": Fields.date,
            "Originalbetrag": Fields.amount,
        }
        # Convert German-formatted numbers (e.g., "1.234,56 €") to standard float format ("1234.56")
        self._fieldFilters[Fields.amount] = lambda content: content.replace(".", "").replace(",", ".").replace(" €", "")
        self._fieldFilters[Fields.date] = lambda content: "-".join(str(content).split(".")[::-1])


class DataLoaderTr(DataLoaderCsv):

    def __init__(self, dataPath: str, accountName: Optional[str] = None):
        """Initialize a Trade Republic CSV loader.

        Args:
            dataPath (str): Path to the Trade Republic CSV file.
        """
        accountName = accountName if accountName is not None else "trade_republic"
        super().__init__(separator=";", headerRowIdx=0, dataPath=dataPath, accountName=accountName)

        self._fieldAliases = {
            "Note": Fields.description,
            "Type": Fields.description,
            "Date": Fields.date,
            "Value": Fields.amount,
        }


loaderMapping: dict[str, type[DataLoader]] = {
    "barclays": DataLoaderBarclays,
    "paypal": DataLoaderPaypal,
    "trade_republic": DataLoaderTr,
}
