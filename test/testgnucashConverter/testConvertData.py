import unittest

from gnucashConverter import convertData as cvd
from gnucashConverter import data


class TestConvertData(unittest.TestCase):
    def setUp(self) -> None:
        self._currentAccount = "Assets:Current"
        self._converter = cvd.ConvertData(
            [
                data.PostTransaction(date="30.05.2025", amount=-1619.25, description="Test1, Test2Händler", source_name=self._currentAccount),
                data.PostTransaction(date="30.05.2024", amount=-13.32, description="Test2, Test1h", source_name=self._currentAccount),
            ],
            accountMap={
                "Expenses:Shopping": "Händler",
                "Expenses:Misc": "h$",
            },
        )
        self._converter.assignAccounts()

    def testAssignAccounts(self):
        """
        Test the assignAccounts method of ConvertData to ensure transactions are assigned the correct account names based on the account map.
        """
        self.assertIs(self._converter.transactions[0].source_name, self._currentAccount)
        self.assertIs(self._converter.transactions[0].destination_name, "Expenses:Shopping")
        self.assertIs(self._converter.transactions[1].source_name, self._currentAccount)
        self.assertIs(self._converter.transactions[1].destination_name, "Expenses:Misc")


if __name__ == "__main__":
    unittest.main()
