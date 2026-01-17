import os
import unittest
from typing import Set

from fireflyConverter import data
from fireflyConverter import fireflyInterface as ffi
from fireflyConverter import loadData as ldb


def create_test_rules(rule_group_id: int, title_prefix: str = "Test") -> list:
    """Create a list of test rules for a given rule group.

    Args:
        rule_group_id: The ID of the rule group to assign rules to.
        title_prefix: Prefix for rule titles (default: "Test").

    Returns:
        List of PostRule objects.
    """
    # Test rule 1 definitions
    test_rule_1_triggers = [
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
    ]

    test_rule_1_actions = [
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
    ]

    # Test rule 2 definitions
    test_rule_2_triggers = [
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
    ]

    test_rule_2_actions = [
        {
            "type": "set_category",
            "value": "Large Transactions",
            "order": 1,
            "active": True,
            "stop_processing": False,
        },
        {
            "type": "add_tag",
            "value": "large-amount",
            "order": 2,
            "active": True,
            "stop_processing": False,
        },
    ]

    return [
        data.PostRule(
            title=f"{title_prefix} Rule 1",
            description="First test rule",
            trigger="store-journal",
            rule_group_id=rule_group_id,
            active=True,
            strict=False,
            stop_processing=False,
            triggers=test_rule_1_triggers,
            actions=test_rule_1_actions,
        ),
        data.PostRule(
            title=f"{title_prefix} Rule 2",
            description="Second test rule",
            trigger="store-journal",
            rule_group_id=rule_group_id,
            active=True,
            strict=False,
            stop_processing=False,
            triggers=test_rule_2_triggers,
            actions=test_rule_2_actions,
        ),
    ]


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
        self._fireflyInterface.deleteRules()
        self._fireflyInterface.deleteRuleGroups()
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

        # Create a rule group for the test rules
        test_rule_group = data.PostRuleGroup(
            title="Test Rule Group",
            description="Rule group for test rules",
            order=1,
            active=True,
        )
        response = self._fireflyInterface.createRuleGroup(test_rule_group)
        rule_group_id = int(response.json()["data"]["id"])

        # Create test rules in a list, all assigned to the rule group
        self._rules = create_test_rules(rule_group_id, "Test")

        # Create the rules on the server
        for rule in self._rules:
            self._fireflyInterface.createRule(rule)

    def testListRules(self):
        # Retrieve all rules from the server
        server_rules = self._fireflyInterface.getRules()

        # Verify we have at least the same number of rules as created
        self.assertGreaterEqual(
            len(server_rules),
            len(self._rules),
            f"Expected at least {len(self._rules)} rules on the server.",
        )

        # Check that our test rules exist on the server
        rule_titles = {rule.title for rule in server_rules}
        for rule in self._rules:
            self.assertIn(
                rule.title,
                rule_titles,
                f"{rule.title} was not found on the server.",
            )

    def testDeleteRules(self):
        # Verify rules exist before deletion
        server_rules_before = self._fireflyInterface.getRules()
        self.assertGreaterEqual(
            len(server_rules_before),
            len(self._rules),
            "Rules should exist before deletion.",
        )

        # Delete all rules
        self._fireflyInterface.deleteRules()

        # Verify all rules were deleted
        server_rules_after = self._fireflyInterface.getRules()
        self.assertEqual(
            len(server_rules_after),
            0,
            "Rules were not deleted from the server.",
        )


class TestRuleGroupInterface(TestInterfaceBase):
    def setUp(self):
        super().setUp()

        # Create test rule groups in a list
        self._ruleGroups = [
            data.PostRuleGroup(
                title="Test Rule Group 1",
                description="First test rule group",
                order=1,
                active=True,
            ),
            data.PostRuleGroup(
                title="Test Rule Group 2",
                description="Second test rule group",
                order=2,
                active=True,
            ),
        ]

        # Create the rule groups on the server
        for ruleGroup in self._ruleGroups:
            self._fireflyInterface.createRuleGroup(ruleGroup)

    def testGetRuleGroups(self):
        # Retrieve all rule groups from the server
        server_rule_groups = self._fireflyInterface.getRuleGroups()

        # Verify we have at least the same number of rule groups as created
        self.assertGreaterEqual(
            len(server_rule_groups),
            len(self._ruleGroups),
            f"Expected at least {len(self._ruleGroups)} rule groups on the server.",
        )

        # Check that our test rule groups exist on the server
        rule_group_titles = {rule_group.title for rule_group in server_rule_groups}
        for ruleGroup in self._ruleGroups:
            self.assertIn(
                ruleGroup.title,
                rule_group_titles,
                f"{ruleGroup.title} was not found on the server.",
            )

    def testDeleteRuleGroups(self):
        # Verify rule groups exist before deletion
        server_rule_groups_before = self._fireflyInterface.getRuleGroups()
        self.assertGreaterEqual(
            len(server_rule_groups_before),
            len(self._ruleGroups),
            "Rule groups should exist before deletion.",
        )

        # Delete all rule groups
        self._fireflyInterface.deleteRuleGroups()

        # Verify all rule groups were deleted
        server_rule_groups_after = self._fireflyInterface.getRuleGroups()
        self.assertEqual(
            len(server_rule_groups_after),
            0,
            "Rule groups were not deleted from the server.",
        )

    def testApplyRuleGroup(self):
        # Retrieve rule groups from the server to get an ID
        server_rule_groups = self._fireflyInterface.getRuleGroups()
        self.assertGreater(
            len(server_rule_groups),
            0,
            "At least one rule group should exist on the server.",
        )

        rule_group_id = int(server_rule_groups[0].id)

        for rule in create_test_rules(rule_group_id, "Apply Test"):
            self._fireflyInterface.createRule(rule)

        # Test 1: Apply the rule group by ID (should not raise an exception even without transactions)
        try:
            response = self._fireflyInterface.applyRuleGroup(rule_group_id)
            self.assertEqual(
                response.status_code,
                204,
                f"Expected status code 204, got {response.status_code}",
            )
        except Exception as e:
            self.fail(f"Applying rule group by ID raised an exception: {e}")

        # Test 2: Apply the rule group by title
        rule_group_title = server_rule_groups[0].title
        try:
            response = self._fireflyInterface.applyRuleGroup(rule_group_title)
            self.assertEqual(
                response.status_code,
                204,
                f"Expected status code 204 when applying by title, got {response.status_code}",
            )
        except Exception as e:
            self.fail(f"Applying rule group by title raised an exception: {e}")

        # Test 3: Test error handling for non-existent title
        with self.assertRaises(ValueError) as context:
            self._fireflyInterface.applyRuleGroup("Non-Existent Rule Group")
        self.assertIn(
            "No rule group found with title",
            str(context.exception),
            "Expected error message about missing rule group title",
        )


if __name__ == "__main__":
    unittest.main()
