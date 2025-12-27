import unittest

from gnucashConverter import loadData as ldb
from gnucashConverter import data


class TestLoaderBarclays(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderBarclays("test/data/barclays.xlsx", "Barclays")

    def testLoad(self):
        """
        Test the load method of DataLoaderTr.
        """
        self._loader.load()

        self.assertEqual(self._loader.transactions[0].date, "2025-05-30")
        self.assertEqual(self._loader.transactions[0].amount, 1619.25)
        self.assertEqual(self._loader.transactions[0].description, "Test1 - Test2Händler")
        self.assertEqual(self._loader.transactions[0].source_name, "Barclays")
        self.assertEqual(self._loader.transactions[0].type, data.TransactionType.WITHDRAWAL.value)

        self.assertEqual(self._loader.transactions[1].date, "2024-05-30")
        self.assertEqual(self._loader.transactions[1].amount, 13.32)
        self.assertEqual(self._loader.transactions[1].description, "Test2 - Test1h")
        self.assertEqual(self._loader.transactions[1].source_name, "Barclays")
        self.assertEqual(self._loader.transactions[1].type, data.TransactionType.WITHDRAWAL.value)


class TestLoaderPaypal(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderPaypal("test/data/paypal.csv", "Paypal")

    def testLoad(self):
        """
        Test the load method of DataLoaderPaypal.
        """
        self._loader.load()

        self.assertEqual(self._loader.transactions[0].date, "2025-07-04")
        self.assertEqual(self._loader.transactions[0].amount, 60.0)
        self.assertEqual(self._loader.transactions[0].description, "Handyzahlung; asdf - rf@gmx.net - asdf")
        self.assertEqual(self._loader.transactions[0].destination_name, "Paypal")
        self.assertEqual(self._loader.transactions[0].type, data.TransactionType.DEPOSIT.value)

        self.assertEqual(self._loader.transactions[1].date, "2025-07-04")
        self.assertEqual(self._loader.transactions[1].amount, 3.0)
        self.assertEqual(self._loader.transactions[1].description, "Handyzahlung - pbfd")
        self.assertEqual(self._loader.transactions[1].source_name, "Paypal")
        self.assertEqual(self._loader.transactions[1].type, data.TransactionType.WITHDRAWAL.value)


class TestLoaderTr(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderTr("test/data/trade_republic.csv", "tr")

    def testLoad(self):
        """
        Test the load method of DataLoaderTr.
        """
        self._loader.load()

        self.assertEqual(self._loader.transactions[0].date, "2024-02-06T15:46:07")
        self.assertEqual(self._loader.transactions[0].amount, 10000.0)
        self.assertEqual(self._loader.transactions[0].description, "asdf - Deposit")
        self.assertEqual(self._loader.transactions[0].destination_name, "tr")
        self.assertEqual(self._loader.transactions[0].type, data.TransactionType.DEPOSIT.value)


        self.assertEqual(self._loader.transactions[1].date, "2025-07-01T05:22:12")
        self.assertEqual(self._loader.transactions[1].amount, 48.24)
        self.assertEqual(self._loader.transactions[1].description, "ijkl - Interest")
        self.assertEqual(self._loader.transactions[1].destination_name, "tr")
        self.assertEqual(self._loader.transactions[1].type, data.TransactionType.DEPOSIT.value)

        self.assertEqual(self._loader.transactions[2].date, "2025-07-02T00:41:26")
        self.assertEqual(self._loader.transactions[2].amount, 128.74)
        self.assertEqual(self._loader.transactions[2].description, "korrekt - Tax Refund")
        self.assertEqual(self._loader.transactions[2].destination_name, "tr")
        self.assertEqual(self._loader.transactions[2].type, data.TransactionType.DEPOSIT.value)

        self.assertEqual(self._loader.transactions[3].date, "2025-08-01T12:14:31")
        self.assertEqual(self._loader.transactions[3].amount, 115.0)
        self.assertEqual(self._loader.transactions[3].description, "money - Removal")
        self.assertEqual(self._loader.transactions[3].source_name, "tr")
        self.assertEqual(self._loader.transactions[3].type, data.TransactionType.WITHDRAWAL.value)

class TestLoaderCommon(TestLoaderTr):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderCommon("test/data/common.csv")

if __name__ == "__main__":
    unittest.main()
