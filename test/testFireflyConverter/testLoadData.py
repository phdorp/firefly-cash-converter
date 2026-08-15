import logging
import unittest

import pandas as pd

from fireflyConverter import data
from fireflyConverter import loadData as ldb


class TestLoaderBarclays(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderBarclays("test/data/barclays", "Barclays")

    def testLoad(self):
        """
        Test the load method of DataLoaderTr.
        """
        transactions = self._loader.load()

        self.assertEqual(transactions[0].date, "2025-05-30")
        self.assertEqual(transactions[0].amount, 1619.25)
        self.assertEqual(transactions[0].description, "Test1 - Test2Händler")
        self.assertEqual(transactions[0].source_name, "Barclays")
        self.assertEqual(transactions[0].type, data.TransactionType.WITHDRAWAL.value)

        self.assertEqual(transactions[1].date, "2024-05-30")
        self.assertEqual(transactions[1].amount, 13.32)
        self.assertEqual(transactions[1].description, "Test2 - Test1h")
        self.assertEqual(transactions[1].source_name, "Barclays")
        self.assertEqual(transactions[1].type, data.TransactionType.WITHDRAWAL.value)


class TestLoaderPaypal(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderPaypal("test/data/paypal", "Paypal")

    def testLoad(self):
        """
        Test the load method of DataLoaderPaypal.
        """
        transactions = self._loader.load()

        self.assertEqual(transactions[0].date, "2025-07-04")
        self.assertEqual(transactions[0].amount, 60.0)
        self.assertEqual(transactions[0].description, "Handyzahlung; asdf - rf@gmx.net - asdf")
        self.assertEqual(transactions[0].destination_name, "Paypal")
        self.assertEqual(transactions[0].type, data.TransactionType.DEPOSIT.value)

        self.assertEqual(transactions[1].date, "2025-07-04")
        self.assertEqual(transactions[1].amount, 3.0)
        self.assertEqual(transactions[1].description, "Handyzahlung - pbfd")
        self.assertEqual(transactions[1].source_name, "Paypal")
        self.assertEqual(transactions[1].type, data.TransactionType.WITHDRAWAL.value)


class TestLoaderTr(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderTr("test/data/trade_republic", "tr")

    def testLoad(self):
        """
        Test the load method of DataLoaderTr.
        """
        transactions = self._loader.load()

        self.assertEqual(transactions[0].date, "2024-02-06T15:46:07")
        self.assertEqual(transactions[0].amount, 10000.0)
        self.assertEqual(transactions[0].description, "asdf - Deposit")
        self.assertEqual(transactions[0].destination_name, "tr")
        self.assertIs(transactions[0].source_name, None)
        self.assertEqual(transactions[0].type, data.TransactionType.DEPOSIT.value)

        self.assertEqual(transactions[1].date, "2025-07-01T05:22:12")
        self.assertEqual(transactions[1].amount, 48.24)
        self.assertEqual(transactions[1].description, "ijkl - Interest")
        self.assertEqual(transactions[1].destination_name, "tr")
        self.assertIs(transactions[1].source_name, None)
        self.assertEqual(transactions[1].type, data.TransactionType.DEPOSIT.value)

        self.assertEqual(transactions[2].date, "2025-07-02T00:41:26")
        self.assertEqual(transactions[2].amount, 128.74)
        self.assertEqual(transactions[2].description, "korrekt - Tax Refund")
        self.assertEqual(transactions[2].destination_name, "tr")
        self.assertIs(transactions[2].source_name, None)
        self.assertEqual(transactions[2].type, data.TransactionType.DEPOSIT.value)

        self.assertEqual(transactions[3].date, "2025-08-01T12:14:31")
        self.assertEqual(transactions[3].amount, 115.0)
        self.assertEqual(transactions[3].description, "money - Removal")
        self.assertEqual(transactions[3].source_name, "tr")
        self.assertIs(transactions[3].destination_name, None)
        self.assertEqual(transactions[3].type, data.TransactionType.WITHDRAWAL.value)


class TestLoaderCommon(TestLoaderTr):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderCommon("test/data/common")


class TestLoaderWarnings(unittest.TestCase):
    """Test that rows missing the amount field are skipped with a warning."""

    def setUp(self) -> None:
        self._loader = ldb.DataLoaderCommon("test/data/common")

    def _parseDataCaptureWarnings(self, dataFrame):
        """Parse data while capturing warnings, restoring the prior logging state."""
        previousDisable = logging.Logger.manager.disable
        logging.disable(logging.NOTSET)
        try:
            with self.assertLogs("fireflyConverter.loadData", level="WARNING") as cm:
                transactions = self._loader._parseData(dataFrame)
        finally:
            logging.disable(previousDisable)
        return transactions, cm

    def testMissingAmountEmitsWarning(self):
        dataFrame = pd.DataFrame(
            [
                ["date", "amount", "description", "source_name", "destination_name", "type"],
                ["2025-01-01", 10.0, "valid", None, "tr", "deposit"],
                ["2025-01-02", None, "no amount", None, "tr", "deposit"],
            ]
        )

        transactions, cm = self._parseDataCaptureWarnings(dataFrame)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].description, "valid")
        self.assertEqual(len(cm.output), 1)
        self.assertEqual(
            cm.output[0],
            "WARNING:fireflyConverter.loadData:Skipping row 2: missing required field 'amount'",
        )

    def testMissingAmountInUncommonLoaderDoesNotCrash(self):
        dataFrame = pd.DataFrame(
            [
                ["Beschreibung", "Absender E-Mail-Adresse", "Name", "Datum", "Brutto"],
                ["Test", None, None, "05.07.2025", None],
            ]
        )
        self._loader = ldb.DataLoaderPaypal("test/data/paypal", "Paypal")

        transactions, cm = self._parseDataCaptureWarnings(dataFrame)

        self.assertEqual(len(transactions), 0)
        self.assertEqual(len(cm.output), 1)
        self.assertIn("missing required field 'amount'", cm.output[0])


if __name__ == "__main__":
    unittest.main()
