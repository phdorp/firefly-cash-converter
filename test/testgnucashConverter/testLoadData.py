import unittest

from gnucashConverter import data
from gnucashConverter import loadData as ldb


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
        self.assertEqual(transactions[0].type, data.TransactionType.DEPOSIT.value)

        self.assertEqual(transactions[1].date, "2025-07-01T05:22:12")
        self.assertEqual(transactions[1].amount, 48.24)
        self.assertEqual(transactions[1].description, "ijkl - Interest")
        self.assertEqual(transactions[1].destination_name, "tr")
        self.assertEqual(transactions[1].type, data.TransactionType.DEPOSIT.value)

        self.assertEqual(transactions[2].date, "2025-07-02T00:41:26")
        self.assertEqual(transactions[2].amount, 128.74)
        self.assertEqual(transactions[2].description, "korrekt - Tax Refund")
        self.assertEqual(transactions[2].destination_name, "tr")
        self.assertEqual(transactions[2].type, data.TransactionType.DEPOSIT.value)

        self.assertEqual(transactions[3].date, "2025-08-01T12:14:31")
        self.assertEqual(transactions[3].amount, 115.0)
        self.assertEqual(transactions[3].description, "money - Removal")
        self.assertEqual(transactions[3].source_name, "tr")
        self.assertEqual(transactions[3].type, data.TransactionType.WITHDRAWAL.value)


class TestLoaderCommon(TestLoaderTr):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderCommon("test/data/common")


if __name__ == "__main__":
    unittest.main()
