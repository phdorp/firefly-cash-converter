import abc
import dataclasses as dc
import enum
from types import NoneType, UnionType
from typing import Any, Callable, Dict, List, Optional, Tuple, get_args

import numpy as np
import pandas as pd

from fireflyConverter import data


class Fields(enum.IntEnum):
    """Enumeration of supported transaction field positions.

    This enum defines the standard field positions for transaction data,
    allowing flexible mapping of source column indices to transaction fields.

    Attributes:
        description (int): Field position for transaction description.
        date (int): Field position for transaction date.
        amount (int): Field position for transaction amount.
        source_name (int): Field position for source account name.
        destination_name (int): Field position for destination account name.
        type (int): Field position for transaction type.
    """

    description = 0
    date = 1
    amount = 2
    source_name = 3
    destination_name = 4
    type = 5


class DataLoader(abc.ABC):
    """Abstract base class for loading transaction data from various sources.

    This class provides the foundation for implementing data loaders that parse
    transaction information from different file formats and data sources. It handles
    field mapping, type conversion, and filtering of transaction data.
    """

    def __init__(self, dataPath: str, **kwargs):
        """Initialize the data loader with the path to the data file.

        Args:
            dataPath (str): Filesystem path to the data file to be loaded.
        """
        self._dataPath = dataPath

        self._fieldTypes: List[type] = []
        for field in dc.fields(data.BaseTransaction):
            if field.name in Fields.__members__:
                if isinstance(field.type, type):
                    self._fieldTypes.insert(Fields[field.name].value, field.type)
                elif isinstance(field.type, UnionType):
                    unionTypes: Tuple[type, NoneType] = get_args(field.type)
                    assert len(unionTypes) == 2 and unionTypes[1] is NoneType, "Second type in BaseTransaction field union must be NoneType"
                    self._fieldTypes.insert(Fields[field.name].value, unionTypes[0])

        self._fieldAliases: Dict[str, Fields] = {field.name: field for field in Fields}
        self._dependentFields: Dict[Fields, Callable[[Dict], Any]] = {}
        self._fieldFilters: List[Callable[[str], str]] = [lambda content: content for _ in Fields]
        self._fieldMergeSep = " - "  # Separator used when merging multiple entries into one field

    @abc.abstractmethod
    def load(self) -> List[data.BaseTransaction]:
        """Load and parse data from the source file into `self._transactions`.

        Implementations should populate `self._transactions` with a list of
        `data.BaseTransaction` instances parsed from the file located at
        `self._dataPath`.

        Returns:
            List[data.BaseTransaction]: Parsed transactions.
        """


class TableDataLoader(DataLoader):
    """Base class for data loaders operating on tabular data formats.

    This class provides functionality for loading and parsing transaction data
    from tabular formats such as CSV and Excel spreadsheets. It introduces
    the headerRowIdx attribute to specify the index of the header row and provides
    common utilities for extracting and processing tabular data.

    Attributes:
        _headerRowIdx (int): The index of the header row in the source data.
    """

    def __init__(self, headerRowIdx: int, dataPath: str, **kwargs):
        """Initialize a table-style loader.

        Args:
            headerRowIdx (int): Index of the header row inside the tabular
                data (used to locate column names).
            dataPath (str): Path to the source data file.
        """
        super().__init__(dataPath, **kwargs)
        self._headerRowIdx = headerRowIdx
        self._fieldFilters[Fields.description] = self._descriptionFilter  # Remove NaN descriptions

    @staticmethod
    def _descriptionFilter(content: str) -> str:
        """Filter function to clean up description fields.

        Args:
            content (str): Raw description content.

        Returns:
            str: Cleaned description with commas replaced by semicolons, or empty string if NaN.
        """
        if pd.isna(content):
            return ""

        return content.replace(",", ";")

    def _getTransactions(self, dataFrame: pd.DataFrame, columnIdcs: List[int]) -> List[data.BaseTransaction]:
        """Extract transactions from a tabular DataFrame using resolved column indices.

        This helper iterates over data rows after the header row (as defined by
        `self._headerRowIdx`), applies any field filters and type conversions,
        and constructs `data.BaseTransaction` objects.

        Args:
            dataFrame (pd.DataFrame): The loaded table-like data.
            columnIdcs (List[int]): Column indices aligned with `self._fieldAliases`.

        Returns:
            List[data.BaseTransaction]: Parsed transactions as PostTransaction objects.
        """
        transactions: List[data.BaseTransaction] = []
        for rowIdx in range(self._headerRowIdx + 1, dataFrame.shape[0]):
            # Create a dictionary to hold the current transaction data
            row = dataFrame.values[rowIdx]
            transactionData: Dict[str, Any] = {}
            for columnIdx, fieldAlias in zip(columnIdcs, self._fieldAliases):
                field = self._fieldAliases[fieldAlias]
                storedData = transactionData.get(field.name, None)
                cellContent = row[columnIdx]

                if not pd.isna(cellContent):
                    inputData = self._fieldTypes[field](self._fieldFilters[field](cellContent))

                    if storedData is None:
                        transactionData[field.name] = inputData
                    elif isinstance(inputData, str) and isinstance(storedData, str):
                        if inputData != "":
                            transactionData[field.name] += self._fieldMergeSep + inputData
                    else:
                        raise ValueError(f"Cannot merge multiple values for non-string field {field.name}")

            # Only add the transaction if it contains data
            if len(transactionData) > 0:
                for field, function in self._dependentFields.items():
                    transactionData[field.name] = function(transactionData)

                transactions.append(data.PostTransaction(**transactionData))

        return transactions

    def _parseData(self, dataFrame: pd.DataFrame) -> List[data.BaseTransaction]:
        """Parse the data from tabular data DataFrame.

        Locates the header row at ``self._headerRowIdx`` to determine the
        column indices for the fields in ``self._fieldAliases`` and
        returns a list of parsed ``data.BaseTransaction`` objects.

        Args:
            dataFrame (pd.DataFrame): The spreadsheet data as a DataFrame.

        Returns:
            List[data.BaseTransaction]: Parsed transactions.
        """

        # Get column indices of the target fields
        colIdcs: List[int] = []
        for fieldAlias in self._fieldAliases:
            fields = np.where(dataFrame.values[self._headerRowIdx, :] == fieldAlias)[0]

            if len(fields) == 0:
                raise ValueError(f"Could not find required field '{fieldAlias}' in data")
            else:
                colIdcs.append(fields[0])

        return self._getTransactions(dataFrame, colIdcs)


class DataLoaderXlsx(TableDataLoader):
    """Data loader for Excel (XLSX) files.

    Extends TableDataLoader to provide functionality for loading and parsing
    transaction data from Excel spreadsheets.
    """

    def __init__(self, headerRowIdx: int, dataPath: str, **kwargs):
        """Create an XLSX table loader.

        Args:
            headerRowIdx (int): Index of the header row in the spreadsheet.
            dataPath (str): Path to the Excel file.
        """
        super().__init__(headerRowIdx, f"{dataPath}.xlsx", **kwargs)

    def load(self):
        """Load data from an Excel file and populate `self._transactions`.

        This method reads the Excel file at `self._dataPath` and calls
        `_parseData` to convert the loaded DataFrame into
        `data.BaseTransaction` objects which are stored in `self._transactions`.
        """
        return self._parseData(pd.read_excel(self._dataPath))


class DataLoaderCsv(TableDataLoader):
    """Data loader for CSV files.

    Extends TableDataLoader to load transaction data from CSV files using
    a configurable field separator and header row index.

    Attributes:
        _separator (str): The delimiter used in the CSV file.
    """

    def __init__(self, separator: str, headerRowIdx: int, dataPath: str, **kwargs):
        """Create a CSV table loader.

        Args:
            separator (str): Delimiter used in the CSV file.
            headerRowIdx (int): Index of the header row inside the CSV data.
            dataPath (str): Path to the CSV file.
        """
        self._separator = separator
        super().__init__(headerRowIdx, f"{dataPath}.csv", **kwargs)

    def load(self):
        """Load data from a CSV file and populate `self._transactions`.

        Reads the CSV at `self._dataPath` using the configured
        `self._separator` and passes the resulting DataFrame to
        `_parseData`. The parsed transactions are stored in
        `self._transactions`.
        """
        return self._parseData(pd.read_csv(self._dataPath, sep=self._separator, header=None))


class DataLoaderCommon(DataLoaderCsv):
    """Data loader for common CSV file format.

    Specializes DataLoaderCsv for the common CSV format with standard comma
    delimiter and header at row index 0.
    """

    def __init__(self, dataPath: str, **kwargs):
        """Create a common CSV table loader.

        Args:
            dataPath (str): Path to the CSV file.
        """
        super().__init__(separator=",", headerRowIdx=0, dataPath=dataPath, **kwargs)


class DataLoaderUncommon:
    """Mixin class providing common field transformation logic for specialized loaders.

    This class encapsulates dependent field transformations used by multiple
    specialized data loaders (PayPal, Barclays, Trade Republic). It handles
    conversion of transaction amounts to positive values and determines
    source/destination accounts based on transaction sign.

    Attributes:
        _dependentFields (Dict[Fields, Callable]): Mapping of fields to transformation functions.
    """

    def __init__(self, accountName: str):
        """Initialize the uncommon loader with account name.

        Args:
            accountName (str): Name of the account for source/destination mapping.
        """
        self._dependentFields = {
            Fields.type: lambda transactionData: (
                data.TransactionType.WITHDRAWAL.value
                if float(transactionData[Fields.amount.name]) < 0
                else data.TransactionType.DEPOSIT.value
            ),
            Fields.source_name: lambda transactionData: (
                accountName if float(transactionData[Fields.amount.name]) < 0 else None
            ),
            Fields.destination_name: lambda transactionData: (
                accountName if float(transactionData[Fields.amount.name]) >= 0 else None
            ),
            Fields.amount: lambda transactionData: abs(float(transactionData[Fields.amount.name])),
        }


class DataLoaderPaypal(DataLoaderCsv, DataLoaderUncommon):
    """Data loader for PayPal CSV exports.

    Specializes DataLoaderCsv for PayPal's CSV format, handling German-formatted
    numbers and currency symbols, and mapping PayPal transaction amounts to source/destination accounts.
    """

    def __init__(self, dataPath: str, accountName: Optional[str] = None, **kwargs):
        """Initialize a PayPal CSV loader.

        Args:
            dataPath (str): Path to the PayPal CSV file.
            accountName (Optional[str]): Name of the account. Defaults to "paypal".
        """
        accountName = accountName if accountName is not None else "paypal"
        DataLoaderCsv.__init__(self, separator=",", headerRowIdx=0, dataPath=dataPath, **kwargs)
        DataLoaderUncommon.__init__(self, accountName)

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


class DataLoaderBarclays(DataLoaderXlsx, DataLoaderUncommon):
    """Data loader for Barclays Excel exports.

    Specializes DataLoaderXlsx for Barclays' Excel format, handling German-formatted
    numbers and currency symbols, and mapping Barclays transaction amounts to source/destination accounts.
    """

    def __init__(self, dataPath: str, accountName: Optional[str] = None, **kwargs):
        """Initialize a Barclays XLSX loader.

        Args:
            dataPath (str): Path to the Barclays Excel file.
            accountName (Optional[str]): Name of the account. Defaults to "barclays".
        """
        accountName = accountName if accountName is not None else "barclays"
        DataLoaderXlsx.__init__(self, headerRowIdx=11, dataPath=dataPath, **kwargs)
        DataLoaderUncommon.__init__(self, accountName)

        self._fieldAliases = {
            "Beschreibung": Fields.description,
            "Details": Fields.description,
            "Buchungsdatum": Fields.date,
            "Originalbetrag": Fields.amount,
        }
        # Convert German-formatted numbers (e.g., "1.234,56 €") to standard float format ("1234.56")
        self._fieldFilters[Fields.amount] = lambda content: content.replace(".", "").replace(",", ".").replace(" €", "")
        self._fieldFilters[Fields.date] = lambda content: "-".join(str(content).split(".")[::-1])


class DataLoaderTr(DataLoaderCsv, DataLoaderUncommon):
    """Data loader for Trade Republic CSV exports.

    Specializes DataLoaderCsv for Trade Republic's CSV format, handling transaction
    data and mapping amounts to source/destination accounts.
    """

    def __init__(self, dataPath: str, accountName: Optional[str] = None, **kwargs):
        """Initialize a Trade Republic CSV loader.

        Args:
            dataPath (str): Path to the Trade Republic CSV file.
            accountName (Optional[str]): Name of the account. Defaults to "trade_republic".
        """
        accountName = accountName if accountName is not None else "trade_republic"
        DataLoaderCsv.__init__(self, separator=";", headerRowIdx=0, dataPath=dataPath, **kwargs)
        DataLoaderUncommon.__init__(self, accountName)

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
    "common": DataLoaderCommon,
}
