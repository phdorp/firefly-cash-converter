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


if __name__ == "__main__":
    unittest.main()
