import os
import tempfile
import unittest
from argparse import ArgumentParser

from gnucashConverter import cli, data
from gnucashConverter import fireflyInterface as ffi


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
        self._fireflyInterface.purgeUserData()

    def testTransferCommon(self):
        """Test the transfer CLI command with transactions from common.csv."""
        # Prepare test data paths
        test_dir = os.path.dirname(__file__)
        test_data_dir = os.path.join(test_dir, "..", "data")

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
        server_transactions = self._fireflyInterface.getTransactions()
        self.assertGreaterEqual(
            len(server_transactions), 5, "Expected at least 5 transactions to be created on the server"
        )

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


if __name__ == "__main__":
    unittest.main()
