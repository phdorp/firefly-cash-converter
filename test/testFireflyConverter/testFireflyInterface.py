import os
import unittest
from typing import Set

from fireflyConverter import data
from fireflyConverter import fireflyInterface as ffi
from fireflyConverter import loadData as ldb


class TestInterfaceBase(unittest.TestCase):
    def setUp(self):
        api_token = os.getenv("TEST_API_TOKEN")
        assert api_token is not None, "TEST_API_TOKEN environment variable must be set for tests."

        self._fireflyInterface = ffi.FireflyInterface(
            base_url="http://localhost",
            api_token=api_token,
        )
        self.addCleanup(self._removeFireflyData)
        self._transactions = ldb.DataLoaderCommon("test/data/common").load()

    def _removeFireflyData(self):
        """Purges data generated during test runs from test server.
        If an error occurs during clean up data left on server might lead to failure of future test runs.
        """
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

        server_account_names = self._fireflyInterface.getAccounts()

        for server_account in server_account_names:
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


class TestRuleInterface(TestInterfaceBase):
    def setUp(self):
        super().setUp()

        # Create two minimal test rules
        self._rule1 = data.PostRule(
            title="Test Rule 1",
            description="First test rule",
            trigger="store-journal",
            active=True,
            strict=False,
            stop_processing=False,
            triggers=[
                {
                    "type": "description_is",
                    "value": "test",
                    "order": 1,
                    "active": True,
                    "prohibited": False,
                    "stop_processing": False,
                },
                {
                    "type": "amount_more",
                    "value": "50",
                    "order": 2,
                    "active": True,
                    "prohibited": False,
                    "stop_processing": False,
                },
            ],
            actions=[
                {
                    "type": "set_category",
                    "value": "Test Category",
                    "order": 1,
                    "active": True,
                    "stop_processing": False,
                },
                {
                    "type": "add_tag",
                    "value": "test-tag",
                    "order": 2,
                    "active": True,
                    "stop_processing": False,
                },
            ],
        )

        self._rule2 = data.PostRule(
            title="Test Rule 2",
            description="Second test rule",
            trigger="store-journal",
            active=True,
            strict=False,
            stop_processing=False,
            triggers=[
                {
                    "type": "amount_more",
                    "value": "100",
                    "order": 1,
                    "active": True,
                    "prohibited": False,
                    "stop_processing": False,
                },
                {
                    "type": "source_account_starts",
                    "value": "Savings",
                    "order": 2,
                    "active": True,
                    "prohibited": False,
                    "stop_processing": False,
                },
            ],
            actions=[
                {
                    "type": "set_budget",
                    "value": "Test Budget",
                    "order": 1,
                    "active": True,
                    "stop_processing": False,
                },
                {
                    "type": "prepend_description",
                    "value": "[Large] ",
                    "order": 2,
                    "active": True,
                    "stop_processing": False,
                },
            ],
        )

        # Create the rules on the server
        self._fireflyInterface.createRule(self._rule1)
        self._fireflyInterface.createRule(self._rule2)

    def testCreateRules(self):
        # Retrieve all rules from the server
        server_rules = self._fireflyInterface.getRules()

        # Verify we have at least 2 rules
        self.assertGreaterEqual(
            len(server_rules),
            2,
            "Expected at least 2 rules on the server.",
        )

        # Check that our test rules exist on the server
        rule_titles = {rule.title for rule in server_rules}
        self.assertIn("Test Rule 1", rule_titles, "Test Rule 1 was not found on the server.")
        self.assertIn("Test Rule 2", rule_titles, "Test Rule 2 was not found on the server.")


if __name__ == "__main__":
    unittest.main()
