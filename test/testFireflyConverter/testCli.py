import os
import tempfile
import types
import unittest
from argparse import ArgumentParser, Namespace
from unittest import mock

import pymupdf

from fireflyConverter import billEnricher as be
from fireflyConverter import cli, data, llmInterface
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
            test_rules = create_test_rules(rule_group_id, f"Apply Test {rule_group_id}")
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
            "Expected at 5 transactions to be created on the server",
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


class _FakeLlm:
    """Stand-in for the local LLM that returns a fixed bill extraction."""

    def __init__(self, *args, **kwargs):
        pass

    def chat(self, messages, response_schema=None, temperature=0.0):
        return (
            '{"total": 115.0, "currency": "EUR", "date": "2025-08-01", "vendor": "money", '
            '"category": "Groceries", "account": "Groceries", "tags": [], "note": "Invoice 7", '
            '"confidence": 0.9}'
        )


class TestTransferParser(unittest.TestCase):
    """Offline tests for the new transfer arguments."""

    def setUp(self):
        parser = ArgumentParser()
        cli.defineTransferParser(parser.add_subparsers(dest="command"))
        self._parser = parser

    def testBillsOptionsAreParsed(self):
        args = self._parser.parse_args(["transfer", "common", "--bills_directory", "./bills", "--dry_run"])

        self.assertEqual(args.bills_directory, "./bills")
        self.assertTrue(args.dry_run)

    def testBillsOptionsDefaultToOff(self):
        args = self._parser.parse_args(["transfer", "common"])

        self.assertIsNone(args.bills_directory)
        self.assertFalse(args.dry_run)

    def testApplyRulesDefaultsToOff(self):
        args = self._parser.parse_args(["transfer", "common"])

        self.assertFalse(args.apply_rules)

    def testApplyRulesIsParsed(self):
        args = self._parser.parse_args(["transfer", "common", "--apply_rules"])

        self.assertTrue(args.apply_rules)


class TestBillDirectorySelection(unittest.TestCase):
    """Offline tests for the opt-in trigger of bill enrichment."""

    def testCommandLineDirectoryWinsOverConfig(self):
        arguments = Namespace(bills_directory="./from-flag")

        selected = cli._configuredBillDirectory(arguments, {"bills": {"directory": "./from-config"}})

        self.assertEqual(selected, "./from-flag")

    def testConfigDirectoryEnablesEnrichmentWithoutFlag(self):
        arguments = Namespace(bills_directory=None)

        selected = cli._configuredBillDirectory(arguments, {"bills": {"directory": "./from-config"}})

        self.assertEqual(selected, "./from-config")

    def testBillsSectionWithoutDirectoryLeavesEnrichmentOff(self):
        arguments = Namespace(bills_directory=None)

        selected = cli._configuredBillDirectory(arguments, {"bills": {"report_path": "./report.md"}})

        self.assertIsNone(selected)

    def testLoadBillConfigUsesSectionValuesAndDirectory(self):
        config = cli._loadBillConfig({"bills": {"date_window_days": 7}}, "/bills")

        self.assertEqual(config.directory, "/bills")
        self.assertEqual(config.date_window_days, 7)
        self.assertEqual(config.marker_tag, "bill-matched")


class TestRuleUsageGuard(unittest.TestCase):
    """Offline tests for the rule flag interactions with bill enrichment."""

    def testRuleGroupsWithBillEnrichmentAreRejected(self):
        with self.assertRaises(ValueError):
            cli._validateRuleUsage(False, ["Test Rule Group"], object())

    def testRuleGroupsWithoutBillEnrichmentAreAllowed(self):
        cli._validateRuleUsage(False, ["Test Rule Group"], None)

    def testBillEnrichmentWithoutRuleGroupsIsAllowed(self):
        cli._validateRuleUsage(False, None, object())

    def testApplyRulesAndRuleGroupsTogetherAreRejected(self):
        with self.assertRaises(ValueError):
            cli._validateRuleUsage(True, ["Test Rule Group"], None)

    def testApplyRulesWithoutRuleGroupsIsAllowed(self):
        cli._validateRuleUsage(True, None, None)


class TestAutoLabeledTag(unittest.TestCase):
    """Offline tests for the auto_labeled audit tag."""

    def _transaction(self, **overrides):
        values = {"date": "2025-01-01", "amount": 1.0, "description": "coffee", "type": "withdrawal"}
        values.update(overrides)
        return data.PostTransaction(**values)

    def testTagIsAddedWhenRulesRunDuringABilledImport(self):
        transaction = self._transaction()

        cli._tagAutoLabeled(transaction, applyRules=True, autoLabeled=True)

        self.assertEqual(transaction.tags, [cli.AUTO_LABELED_TAG])

    def testTagIsNotAddedWithoutBillEnrichment(self):
        transaction = self._transaction()

        cli._tagAutoLabeled(transaction, applyRules=True, autoLabeled=False)

        self.assertIsNone(transaction.tags)

    def testTagIsNotAddedWhenNoRulesRun(self):
        transaction = self._transaction()

        cli._tagAutoLabeled(transaction, applyRules=False, autoLabeled=True)

        self.assertIsNone(transaction.tags)

    def testExistingTagsAreKeptAndTheTagIsAddedOnce(self):
        transaction = self._transaction(tags=["existing", cli.AUTO_LABELED_TAG])

        cli._tagAutoLabeled(transaction, applyRules=True, autoLabeled=True)

        self.assertEqual(transaction.tags, ["existing", cli.AUTO_LABELED_TAG])


class TestRuleApplicationTargets(unittest.TestCase):
    """Offline tests for which transactions Firefly III rules are applied to."""

    def _transaction(self):
        return data.PostTransaction(date="2025-01-01", amount=1.0, description="coffee", type="withdrawal")

    def testRulesRunWhenRequestedAndNoBillMatched(self):
        transaction = self._transaction()

        self.assertTrue(cli._rulesApplyTo(transaction, set(), True))

    def testRulesStayOffWhenNotRequested(self):
        transaction = self._transaction()

        self.assertFalse(cli._rulesApplyTo(transaction, set(), False))

    def testBillMatchedTransactionsNeverGetRules(self):
        transaction = self._transaction()

        self.assertFalse(cli._rulesApplyTo(transaction, {id(transaction)}, True))

    def testMatchedTransactionsComeFromTheReport(self):
        transaction = self._transaction()
        report = be.EnrichmentReport(matched_transactions=[transaction])

        self.assertEqual(cli._matchedTransactionIds(report), {id(transaction)})

    def testWithoutAReportNothingIsMatched(self):
        self.assertEqual(cli._matchedTransactionIds(None), set())


class TestMatchedBillPaths(unittest.TestCase):
    def testIncludesPrimaryAndSplitBills(self):
        transaction = data.PostTransaction(date="2025-01-01", amount=3.0, description="shop", type="withdrawal")
        report = be.EnrichmentReport(
            matched=[
                be.MatchRecord(
                    bill_path="/b/one.pdf",
                    description="shop",
                    category=None,
                    tags=[],
                    additional_bills=[data.Bill(path="/b/two.png")],
                )
            ],
            matched_transactions=[transaction],
        )

        self.assertEqual(cli._matchedBillPaths(report), {id(transaction): ["/b/one.pdf", "/b/two.png"]})

    def testRejectsMismatchedReport(self):
        report = be.EnrichmentReport(
            matched=[be.MatchRecord(bill_path="/b/one.pdf", description="shop", category=None, tags=[])]
        )

        with self.assertRaises(ValueError):
            cli._matchedBillPaths(report)


class TestBillAccountPool(unittest.TestCase):
    """Offline tests for the accounts offered to the bill reader."""

    def _accounts(self, *pairs):
        return [types.SimpleNamespace(name=name, active=active, type=accountType) for name, active, accountType in pairs]

    def testReturnsActiveAccountsWithoutTheImportedOne(self):
        interface = mock.Mock()
        interface.getAccounts.return_value = self._accounts(
            ("tr", True, "asset"), ("Groceries", True, "expense"), ("Closed account", False, "expense")
        )

        accounts = cli._accountNamesForBills(interface, "tr", enabled=True)

        self.assertEqual(accounts, ["Groceries"])

    def testAccountsWithoutAnActiveFlagAreKept(self):
        interface = mock.Mock()
        interface.getAccounts.return_value = self._accounts(("Groceries", None, "expense"))

        accounts = cli._accountNamesForBills(interface, "tr", enabled=True)

        self.assertEqual(accounts, ["Groceries"])

    def testReturnsNothingWhenAccountMappingIsOff(self):
        interface = mock.Mock()

        accounts = cli._accountNamesForBills(interface, "tr", enabled=False)

        self.assertEqual(accounts, [])
        interface.getAccounts.assert_not_called()

    def testOnlyConfiguredAccountTypesAreReturned(self):
        interface = mock.Mock()
        interface.getAccounts.return_value = self._accounts(
            ("Groceries", True, "expense"), ("Salary", True, "income"), ("Checking", True, "asset")
        )

        accounts = cli._accountNamesForBills(interface, "tr", enabled=True, accountTypes=["income"])

        self.assertEqual(accounts, ["Salary"])

    def testImportedAccountComparisonIsCaseInsensitive(self):
        interface = mock.Mock()
        interface.getAccounts.return_value = self._accounts(("TR", True, "expense"), ("Groceries", True, "expense"))

        accounts = cli._accountNamesForBills(interface, "tr", enabled=True)

        self.assertEqual(accounts, ["Groceries"])


class TestTransactionJournalId(unittest.TestCase):
    def testExtractsJournalIdFromTransactionSplit(self):
        response = mock.Mock()
        response.json.return_value = {
            "data": {
                "id": "transaction-group",
                "attributes": {"transactions": [{"transaction_journal_id": "17"}]},
            }
        }

        self.assertEqual(cli._transactionJournalId(response), "17")


class TestTransferWithBills(unittest.TestCase):
    def setUp(self):
        api_token = os.getenv("TEST_API_TOKEN")
        assert api_token is not None, "TEST_API_TOKEN environment variable must be set for tests."

        self._fireflyInterface = ffi.FireflyInterface(base_url="http://localhost", api_token=api_token)
        self.addCleanup(self._removeFireflyData)

        self._tempConfig = tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False)
        self.addCleanup(lambda: os.unlink(self._tempConfig.name))

        self._tempBills = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempBills.cleanup)
        self._reportPath = os.path.join(self._tempBills.name, "report.md")

    def _removeFireflyData(self):
        self._fireflyInterface.deleteAccounts()
        self._fireflyInterface.deleteRules()
        self._fireflyInterface.deleteRuleGroups()
        self._fireflyInterface.purgeUserData()

    def _writeConfig(self, accounts=True):
        api_token = os.getenv("TEST_API_TOKEN")
        self._tempConfig.write(
            f'[firefly_interface]\nbase_url = "http://localhost"\napi_token = "{api_token}"\n'
            'duplicate_transaction = "ignore"\n\n'
            f'[bills]\nreport_path = "{self._reportPath}"\naccounts = {str(accounts).lower()}\n\n'
            '[llm]\nbase_url = "http://127.0.0.1:1234/v1"\nmodel = "test"\n'
        )
        self._tempConfig.flush()
        self._tempConfig.close()

    def _writeBill(self):
        path = os.path.join(self._tempBills.name, "acme.pdf")
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 72), "Invoice from money, total 115,00 EUR")
        document.save(path)
        document.close()
        return path

    @mock.patch.object(llmInterface, "LLMInterface", _FakeLlm)
    def testDryRunEnrichesWithoutPostingOrArchiving(self):
        test_dir = os.path.dirname(__file__)
        test_data_dir = os.path.normpath(os.path.join(test_dir, "..", "data"))
        self._fireflyInterface.createAccount(data.PostAssetAccount(name="tr"))
        self._writeConfig()
        billPath = self._writeBill()

        parser = ArgumentParser()
        cli.defineTransferParser(parser.add_subparsers(dest="command"))
        args = parser.parse_args(
            [
                "transfer",
                "common",
                "--config_path",
                self._tempConfig.name,
                "--input_directory",
                test_data_dir,
                "--input_name",
                "common",
                "--account_name",
                "tr",
                "--bills_directory",
                self._tempBills.name,
                "--dry_run",
            ]
        )

        cli.transfer(args)

        self.assertEqual(len(self._fireflyInterface.getTransactions(limit=100, page=1)), 0, "Dry run must not post")
        self.assertTrue(os.path.exists(billPath), "Dry run must not archive bills")

        with open(self._reportPath, encoding="utf-8") as handle:
            report = handle.read()
        self.assertIn("money - Removal", report)
        self.assertIn("acme.pdf", report)

    @mock.patch.object(llmInterface, "LLMInterface", _FakeLlm)
    def testRunPostsTransactionsThenArchivesBills(self):
        test_dir = os.path.dirname(__file__)
        test_data_dir = os.path.normpath(os.path.join(test_dir, "..", "data"))
        self._fireflyInterface.createAccount(data.PostAssetAccount(name="tr"))
        self._writeConfig()
        billPath = self._writeBill()

        parser = ArgumentParser()
        cli.defineTransferParser(parser.add_subparsers(dest="command"))
        args = parser.parse_args(
            [
                "transfer",
                "common",
                "--config_path",
                self._tempConfig.name,
                "--input_directory",
                test_data_dir,
                "--input_name",
                "common",
                "--account_name",
                "tr",
                "--bills_directory",
                self._tempBills.name,
            ]
        )

        cli.transfer(args)

        self.assertEqual(len(self._fireflyInterface.getTransactions(limit=100, page=1)), 5)
        self.assertFalse(os.path.exists(billPath), "Matched bill should be archived")
        self.assertTrue(os.path.exists(os.path.join(self._tempBills.name, "processed", "acme.pdf")))

    @mock.patch.object(llmInterface, "LLMInterface", _FakeLlm)
    def testBillSetsTheCounterAccount(self):
        test_dir = os.path.dirname(__file__)
        test_data_dir = os.path.normpath(os.path.join(test_dir, "..", "data"))
        self._fireflyInterface.createAccount(data.PostAssetAccount(name="tr"))
        self._fireflyInterface.createAccount(data.PostExpenseAccount(name="Groceries"))
        self._writeConfig()
        self._writeBill()

        parser = ArgumentParser()
        cli.defineTransferParser(parser.add_subparsers(dest="command"))
        args = parser.parse_args(
            [
                "transfer",
                "common",
                "--config_path",
                self._tempConfig.name,
                "--input_directory",
                test_data_dir,
                "--input_name",
                "common",
                "--account_name",
                "tr",
                "--bills_directory",
                self._tempBills.name,
            ]
        )

        cli.transfer(args)

        transactions = self._fireflyInterface.getTransactions(limit=100, page=1)
        billMatched = [transaction for transaction in transactions if transaction.description == "money - Removal"]
        self.assertEqual(len(billMatched), 1, "Exactly one transaction should be bill-matched")
        self.assertEqual(billMatched[0].destination_name, "Groceries")

    @mock.patch.object(llmInterface, "LLMInterface", _FakeLlm)
    def testCounterAccountIsLeftAloneWhenMappingIsOff(self):
        test_dir = os.path.dirname(__file__)
        test_data_dir = os.path.normpath(os.path.join(test_dir, "..", "data"))
        self._fireflyInterface.createAccount(data.PostAssetAccount(name="tr"))
        self._fireflyInterface.createAccount(data.PostExpenseAccount(name="Groceries"))
        self._writeConfig(accounts=False)
        self._writeBill()

        parser = ArgumentParser()
        cli.defineTransferParser(parser.add_subparsers(dest="command"))
        args = parser.parse_args(
            [
                "transfer",
                "common",
                "--config_path",
                self._tempConfig.name,
                "--input_directory",
                test_data_dir,
                "--input_name",
                "common",
                "--account_name",
                "tr",
                "--bills_directory",
                self._tempBills.name,
            ]
        )

        cli.transfer(args)

        transactions = self._fireflyInterface.getTransactions(limit=100, page=1)
        billMatched = [transaction for transaction in transactions if transaction.description == "money - Removal"]
        self.assertEqual(len(billMatched), 1, "Exactly one transaction should be bill-matched")
        self.assertNotEqual(billMatched[0].destination_name, "Groceries")

    @mock.patch.object(llmInterface, "LLMInterface", _FakeLlm)
    def testApplyRulesLabelsOnlyTheNonBillTransactions(self):
        test_dir = os.path.dirname(__file__)
        test_data_dir = os.path.normpath(os.path.join(test_dir, "..", "data"))
        self._fireflyInterface.createAccount(data.PostAssetAccount(name="tr"))
        self._writeConfig()
        self._writeBill()

        parser = ArgumentParser()
        cli.defineTransferParser(parser.add_subparsers(dest="command"))
        args = parser.parse_args(
            [
                "transfer",
                "common",
                "--config_path",
                self._tempConfig.name,
                "--input_directory",
                test_data_dir,
                "--input_name",
                "common",
                "--account_name",
                "tr",
                "--bills_directory",
                self._tempBills.name,
                "--apply_rules",
            ]
        )

        cli.transfer(args)

        transactions = self._fireflyInterface.getTransactions(limit=100, page=1)
        self.assertEqual(len(transactions), 5)

        billMatched = [transaction for transaction in transactions if transaction.description == "money - Removal"]
        self.assertEqual(len(billMatched), 1, "Exactly one transaction should be bill-matched")
        self.assertIn("bill-matched", billMatched[0].tags or [])
        self.assertNotIn(cli.AUTO_LABELED_TAG, billMatched[0].tags or [])

        ruleLabeled = [transaction for transaction in transactions if transaction.description != "money - Removal"]
        self.assertEqual(len(ruleLabeled), 4)
        for transaction in ruleLabeled:
            self.assertIn(cli.AUTO_LABELED_TAG, transaction.tags or [])

    @mock.patch.object(llmInterface, "LLMInterface", _FakeLlm)
    def testFailedTransferDoesNotArchiveBills(self):
        test_dir = os.path.dirname(__file__)
        test_data_dir = os.path.normpath(os.path.join(test_dir, "..", "data"))
        self._fireflyInterface.createAccount(data.PostAssetAccount(name="tr"))
        self._writeConfig()
        billPath = self._writeBill()

        parser = ArgumentParser()
        cli.defineTransferParser(parser.add_subparsers(dest="command"))
        args = parser.parse_args(
            [
                "transfer",
                "common",
                "--config_path",
                self._tempConfig.name,
                "--input_directory",
                test_data_dir,
                "--input_name",
                "common",
                "--account_name",
                "tr",
                "--bills_directory",
                self._tempBills.name,
            ]
        )

        with mock.patch.object(ffi.FireflyInterface, "createTransaction", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                cli.transfer(args)

        self.assertTrue(os.path.exists(billPath), "Bills must survive a failed transfer")
        self.assertFalse(os.path.exists(os.path.join(self._tempBills.name, "processed", "acme.pdf")))


if __name__ == "__main__":
    unittest.main()
