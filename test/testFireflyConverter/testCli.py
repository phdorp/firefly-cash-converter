import os
import tempfile
import unittest
from argparse import ArgumentParser

from fireflyConverter import cli, data
from fireflyConverter import fireflyInterface as ffi
from .testFireflyInterface import create_test_rules


class TestTransferCli(unittest.TestCase):
    def setUp(self):
        api_token = os.getenv("TEST_API_TOKEN")
        assert api_token is not None, "TEST_API_TOKEN environment variable must be set for tests."

        self._fireflyInterface = ffi.FireflyInterface(
            base_url="http://localhost",
            api_token=api_token,
        )
        self.addCleanup(self._removeFireflyData)

        self._temp_config = tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False)
        self._temp_config.write(
            f'[firefly_interface]\nbase_url = "http://localhost"\napi_token = "{api_token}"\nduplicate_transaction = "ignore"\n'
        )
        self._temp_config.flush()
        self._temp_config.close()
        self.addCleanup(lambda: os.unlink(self._temp_config.name))

        self._parser = ArgumentParser()
        cli.defineTransferParser(self._parser.add_subparsers(dest="command"))

    def _removeFireflyData(self):
        """Purges data generated during test runs from test server.
        If an error occurs during clean up data left on server might lead to failure of future test runs.
        """
        self._fireflyInterface.deleteAccounts()
        self._fireflyInterface.deleteRules()
        self._fireflyInterface.deleteRuleGroups()
        self._fireflyInterface.purgeUserData()

    def testTransferCommon(self):
        """Test the transfer CLI command with transactions from common.csv."""
        # Prepare test data paths
        test_dir = os.path.dirname(__file__)
        test_data_dir = os.path.normpath(os.path.join(test_dir, "..", "data"))

        # Create the 'tr' account that's referenced in common.csv
        account = data.PostAssetAccount(name="tr")
        self._fireflyInterface.createAccount(account)

        # Parse CLI arguments as they would be supplied from command line
        args = self._parser.parse_args(
            [
                "transfer",
                "common",
                "--config_path",
                self._temp_config.name,
                "--input_directory",
                test_data_dir,
                "--input_name",
                "common",
                "--account_name",
                "tr",
            ]
        )

        # Execute the transfer command via CLI
        cli.transfer(args)

        # Verify transactions were transferred successfully
        server_transactions = self._fireflyInterface.getTransactions(limit=100, page=1)
        self.assertEqual(len(server_transactions), 5, "Expected at least 5 transactions to be created on the server")

        # Verify transaction details from common.csv
        transaction_descriptions = [transaction.description for transaction in server_transactions]
        expected_descriptions = [
            "asdf - Deposit",
            "ijkl - Interest",
            "korrekt - Tax Refund",
            "money - Removal",
            "year-end bonus",
        ]
        for description in expected_descriptions:
            self.assertIn(description, transaction_descriptions, f"Transaction '{description}' not found on server")

    def testApplyRuleGroups(self):
        """Test the transfer CLI command with rule group application by name."""
        # Prepare test data paths
        test_dir = os.path.dirname(__file__)
        test_data_dir = os.path.normpath(os.path.join(test_dir, "..", "data"))

        # Create the 'tr' account that's referenced in common.csv
        account = data.PostAssetAccount(name="tr")
        self._fireflyInterface.createAccount(account)

        # Create test rule groups (matching those in testFireflyInterface.py)
        rule_groups = [
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
        rule_group_responses = []
        for rule_group in rule_groups:
            response = self._fireflyInterface.createRuleGroup(rule_group)
            rule_group_responses.append(response)

        # Create and post test rules for each rule group
        rule_group_ids = [int(response.json()["data"]["id"]) for response in rule_group_responses]
        for rule_group_id in rule_group_ids:
            test_rules = create_test_rules(rule_group_id, "Apply Test" + str(rule_group_id))
            for rule in test_rules:
                self._fireflyInterface.createRule(rule)

        # Parse CLI arguments with --apply_rule_groups using rule group names
        args = self._parser.parse_args(
            [
                "transfer",
                "common",
                "--config_path",
                self._temp_config.name,
                "--input_directory",
                test_data_dir,
                "--input_name",
                "common",
                "--account_name",
                "tr",
                "--apply_rule_groups",
                "Test Rule Group 1",
                "Test Rule Group 2",
            ]
        )
        cli.transfer(args)

        # Verify transactions were transferred successfully
        server_transactions = self._fireflyInterface.getTransactions(limit=100, page=1)
        self.assertEqual(
            len(server_transactions),
            5,
            "Expected at least 5 transactions to be created on the server",
        )

        # Verify rule groups exist and can be accessed by name
        server_rule_groups = self._fireflyInterface.getRuleGroups()
        rule_group_names = {rg.title for rg in server_rule_groups}
        self.assertIn("Test Rule Group 1", rule_group_names, "Test Rule Group 1 should exist")
        self.assertIn("Test Rule Group 2", rule_group_names, "Test Rule Group 2 should exist")

        # Verify we can apply rule groups by name
        try:
            response1 = self._fireflyInterface.applyRuleGroup("Test Rule Group 1")
            self.assertEqual(
                response1.status_code,
                204,
                f"Expected status code 204 for Test Rule Group 1, got {response1.status_code}",
            )

            response2 = self._fireflyInterface.applyRuleGroup("Test Rule Group 2")
            self.assertEqual(
                response2.status_code,
                204,
                f"Expected status code 204 for Test Rule Group 2, got {response2.status_code}",
            )
        except Exception as e:
            self.fail(f"Applying rule groups by name raised an exception: {e}")


if __name__ == "__main__":
    unittest.main()
