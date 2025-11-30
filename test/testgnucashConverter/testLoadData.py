import unittest

from gnucashConverter import loadData as ldb


class TestLoaderBarclays(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderBarclays("test/data/barclays.xlsx")

    def testLoad(self):
        """
        Test the load method of DataLoaderTr.
        """
        self._loader.load()

        self.assertEqual(self._loader.transactions[0].Date, "2025-05-30")
        self.assertEqual(self._loader.transactions[0].Deposit, -1619.25)
        self.assertEqual(self._loader.transactions[0].Description, "Test1 - Test2Händler")

        self.assertEqual(self._loader.transactions[1].Date, "2024-05-30")
        self.assertEqual(self._loader.transactions[1].Deposit, -13.32)
        self.assertEqual(self._loader.transactions[1].Description, "Test2 - Test1h")

class TestLoaderPaypal(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderPaypal("test/data/paypal.csv")

    def testLoad(self):
        """
        Test the load method of DataLoaderPaypal.
        """
        self._loader.load()

        self.assertEqual(self._loader.transactions[0].Date, "2025-07-04")
        self.assertEqual(self._loader.transactions[0].Deposit, 60.0)
        self.assertEqual(self._loader.transactions[0].Description, "Handyzahlung; asdf - rf@gmx.net - asdf")

        self.assertEqual(self._loader.transactions[1].Date, "2025-07-04")
        self.assertEqual(self._loader.transactions[1].Deposit, -3.0)
        self.assertEqual(self._loader.transactions[1].Description, "Handyzahlung - pbfd")


class TestLoaderTr(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderTr("test/data/trade_republic.csv")

    def testLoad(self):
        """
        Test the load method of DataLoaderTr.
        """
        self._loader.load()

        self.assertEqual(self._loader.transactions[0].Date, "2024-02-06")
        self.assertEqual(self._loader.transactions[0].Deposit, 10000.0)
        self.assertEqual(self._loader.transactions[0].Description, "asdf - Deposit")

        self.assertEqual(self._loader.transactions[1].Date, "2025-07-01")
        self.assertEqual(self._loader.transactions[1].Deposit, 48.24)
        self.assertEqual(self._loader.transactions[1].Description, "ijkl - Interest")
        self.assertEqual(self._loader.transactions[2].Date, "2025-07-02")
        self.assertEqual(self._loader.transactions[2].Deposit, 128.74)
        self.assertEqual(self._loader.transactions[2].Description, "korrekt - Tax Refund")

        self.assertEqual(self._loader.transactions[3].Date, "2025-08-01")
        self.assertEqual(self._loader.transactions[3].Deposit, -115.0)
        self.assertEqual(self._loader.transactions[3].Description, "money - Removal")

if __name__ == "__main__":
    unittest.main()
