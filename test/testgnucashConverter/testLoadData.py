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

        self.assertEqual(self._loader.data[0].Date, "30.05.2025")
        self.assertEqual(self._loader.data[0].Deposit, -1619.25)
        self.assertEqual(self._loader.data[0].Description, "Test1")

        self.assertEqual(self._loader.data[1].Date, "30.05.2024")
        self.assertEqual(self._loader.data[1].Deposit, -13.32)
        self.assertEqual(self._loader.data[1].Description, "Test2")


class TestLoaderPaypal(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderPaypal("test/data/paypal.csv")

    def testLoad(self):
        """
        Test the load method of DataLoaderPaypal.
        """
        self._loader.load()

        self.assertEqual(self._loader.data[0].Date, "04.07.2025")
        self.assertEqual(self._loader.data[0].Deposit, 60.0)
        self.assertEqual(self._loader.data[0].Description, "Handyzahlung")

        self.assertEqual(self._loader.data[1].Date, "04.07.2025")
        self.assertEqual(self._loader.data[1].Deposit, -3.0)
        self.assertEqual(self._loader.data[1].Description, "Handyzahlung")

class TestLoaderTr(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderTr("test/data/trade_republic.csv")

    def testLoad(self):
        """
        Test the load method of DataLoaderTr.
        """
        self._loader.load()

        self.assertEqual(self._loader.data[0].Date, "06.02.2024")
        self.assertEqual(self._loader.data[0].Deposit, 10000.0)
        self.assertEqual(self._loader.data[0].Description, "asdf")

        self.assertEqual(self._loader.data[1].Date, "01.07.2025")
        self.assertEqual(self._loader.data[1].Deposit, 48.24)
        self.assertEqual(self._loader.data[1].Description, "ijkl")

        self.assertEqual(self._loader.data[2].Date, "02.07.2025")
        self.assertEqual(self._loader.data[2].Deposit, 128.74)
        self.assertEqual(self._loader.data[2].Description, "korrekt")

        self.assertEqual(self._loader.data[3].Date, "01.08.2025")
        self.assertEqual(self._loader.data[3].Deposit, -115.0)
        self.assertEqual(self._loader.data[3].Description, "money")

if __name__ == "__main__":
    unittest.main()
