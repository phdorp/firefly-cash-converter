import unittest

from gnucashConverter import loadData as ldb


class TestLoaderBarclays(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderBarclays("test/data/barclays.xlsx")

    def testLoad(self):
        """
        Test the load method of DataLoaderXlsx.
        """
        self._loader.load()

        self.assertEqual(self._loader.data[0].Date, "30.05.2025")
        self.assertEqual(self._loader.data[0].Deposit, -19.25)
        self.assertEqual(self._loader.data[0].Description, "Test1")

        self.assertEqual(self._loader.data[1].Date, "30.05.2024")
        self.assertEqual(self._loader.data[1].Deposit, -13.32)
        self.assertEqual(self._loader.data[1].Description, "Test2")


class TestLoaderPaypal(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderPaypal("test/data/paypal.xlsx")

    def testLoad(self):
        """
        Test the load method of DataLoaderXlsx.
        """
        self._loader.load()

        self.assertEqual(self._loader.data[0].Date, "08.06.2024")
        self.assertEqual(self._loader.data[0].Deposit, -72.9)
        self.assertEqual(self._loader.data[0].Description, "Von Nutzer eingeleitete Abbuchung")

        self.assertEqual(self._loader.data[1].Date, "21.06.2024")
        self.assertEqual(self._loader.data[1].Deposit, -27.5)
        self.assertEqual(self._loader.data[1].Description, "Handyzahlung")

if __name__ == "__main__":
    unittest.main()
