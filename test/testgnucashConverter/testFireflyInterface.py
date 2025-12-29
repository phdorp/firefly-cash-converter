import os
import unittest
from typing import Set
from unittest.mock import Mock

from gnucashConverter import data
from gnucashConverter import fireflyInterface as ffi
from gnucashConverter import loadData as ldb


class TestAccountInterface(unittest.TestCase):
    def setUp(self) -> None:
        api_token = os.getenv("API_TOKEN")
        assert api_token is not None, "API_TOKEN environment variable must be set for tests."

        self._fireflyInterface = ffi.FireflyInterface(
            base_url="http://localhost",
            api_token=api_token,
        )
        self._transactions = ldb.DataLoaderCommon("test/data/common").load()

    def tearDown(self) -> ldb.NoneType:
        self._fireflyInterface.deleteAccounts()

    def testCreateDeleteAccounts(self):
        account_names: Set[str] = set()

        for transaction in self._transactions:
            if transaction.source_name is not None:
                account_names.add(transaction.source_name)
            if transaction.destination_name is not None:
                account_names.add(transaction.destination_name)

        for account_name in account_names:
            self._fireflyInterface.createAccount(data.PostAssetAccount(account_name))

        for server_account in self._fireflyInterface.getAccounts():
            message = f"Account {server_account.name} was not created on the server."
            self.assertTrue(server_account.name in account_names, message)
            account_names.remove(server_account.name)

        self._fireflyInterface.deleteAccounts()
        self.assertEqual(len(self._fireflyInterface.getAccounts()), 0, "Accounts were not deleted from the server.")


class TestTransactionInterface(unittest.TestCase):
    pass

if __name__ == "__main__":
    unittest.main()
