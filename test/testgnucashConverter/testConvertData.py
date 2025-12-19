import unittest

from gnucashConverter import convertData as cvd
from gnucashConverter import data


class TestConvertData(unittest.TestCase):
    def setUp(self) -> None:
        self._currentAccount = "Assets:Current"
        self._converter = cvd.ConvertData(
            self._currentAccount,
            [
                data.Transaction(Date="30.05.2025", Deposit=-1619.25, Description="Test1, Test2Händler"),
                data.Transaction(Date="30.05.2024", Deposit=-13.32, Description="Test2, Test1h"),
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
        self.assertIs(self._converter.transactions[0].SourceAccount, self._currentAccount)
        self.assertIs(self._converter.transactions[0].DestinationAccount, "Expenses:Shopping")
        self.assertIs(self._converter.transactions[1].SourceAccount, self._currentAccount)
        self.assertIs(self._converter.transactions[1].DestinationAccount, "Expenses:Misc")


if __name__ == "__main__":
    unittest.main()
