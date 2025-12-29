import os
import unittest
from typing import Set

from gnucashConverter import data
from gnucashConverter import fireflyInterface as ffi
from gnucashConverter import loadData as ldb


class TestInterfaceBase(unittest.TestCase):
    def setUp(self):
        api_token = os.getenv("API_TOKEN")
        assert api_token is not None, "API_TOKEN environment variable must be set for tests."

        self._fireflyInterface = ffi.FireflyInterface(
            base_url="http://localhost",
            api_token=api_token,
        )
        self.addCleanup(self._removeFireflyData)
        self._transactions = ldb.DataLoaderCommon("test/data/common").load()

    def _removeFireflyData(self):
        self._fireflyInterface.deleteAccounts()
        self._fireflyInterface.purgeUserData()

    def _getAccountNames(self) -> Set[str]:
        account_names: Set[str] = set()

        for transaction in self._transactions:
            if transaction.source_name is not None:
                account_names.add(transaction.source_name)
            if transaction.destination_name is not None:
                account_names.add(transaction.destination_name)

        return account_names


class TestAccountInterface(TestInterfaceBase):
    def testCreateDeleteAccounts(self):
        account_names = self._getAccountNames()

        for account_name in account_names:
            self._fireflyInterface.createAccount(data.PostAssetAccount(account_name))

        for server_account in self._fireflyInterface.getAccounts():
            message = f"Account {server_account.name} was not created on the server."
            self.assertTrue(server_account.name in account_names, message)
            account_names.remove(server_account.name)

        self._fireflyInterface.deleteAccounts()
        self.assertEqual(len(self._fireflyInterface.getAccounts()), 0, "Accounts were not deleted from the server.")


class TestTransactionInterface(TestInterfaceBase):
    def setUp(self):
        super().setUp()

        for account_name in self._getAccountNames():
            self._fireflyInterface.createAccount(data.PostAssetAccount(account_name))

    def testCreateTransactions(self):
        for transaction in self._transactions:
            self._fireflyInterface.createTransaction(transaction)

        server_transactions = self._fireflyInterface.getTransactions(limit=100, page=1)
        self.assertEqual(
            len(server_transactions),
            len(self._transactions),
            "Number of transactions on the server does not match the number of created transactions.",
        )


if __name__ == "__main__":
    unittest.main()
