import unittest
from unittest.mock import Mock

from gnucashConverter import fireflyInterface as ffi
from gnucashConverter import data


class TestFireflyInterface(unittest.TestCase):
    def setUp(self) -> None:
        # Create a simple account map mapping account names to Firefly account ids
        self.account_map = {"Expenses:Shopping": 10, "Expenses:Misc": 11}
        self.fi = ffi.FireflyInterface(
            base_url="https://firefly.example",
            api_token="fake-token",
            account_map=self.account_map,
            default_balance_account_id=99,
        )

    def test_create_transactions_posts_expected_payloads(self):
        # Prepare two transactions
        txs = [
            data.Transaction(Date="2025-05-30", Deposit=-1619.25, Description="Test1", AccountName="Expenses:Shopping"),
            data.Transaction(Date="2024-05-30", Deposit=-13.32, Description="Test2", AccountName="Expenses:Misc"),
        ]

        # Mock the session.post method to capture calls and return a fake response
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.status_code = 201
        self.fi.session.post = Mock(return_value=mock_resp)

        responses = self.fi.create_transactions(txs)

        # Ensure we received two responses
        self.assertEqual(len(responses), 2)

        # Ensure post was called twice
        self.assertEqual(self.fi.session.post.call_count, 2)

        # Inspect the JSON payload of the first call
        first_call_args, first_call_kwargs = self.fi.session.post.call_args_list[0]
        # URL should be the transactions endpoint
        self.assertTrue(str(first_call_args[0]).endswith("/api/v1/transactions"))
        payload = first_call_kwargs.get("json")
        self.assertIsNotNone(payload)

        # Payload should contain two transaction entries
        self.assertIn("transactions", payload)
        self.assertEqual(len(payload["transactions"]), 2)

        # The mapped account id for the first transaction should match the account_map
        self.assertEqual(payload["transactions"][0]["account_id"], self.account_map[txs[0].AccountName])


if __name__ == "__main__":
    unittest.main()
