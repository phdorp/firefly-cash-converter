import unittest
from unittest.mock import Mock

from gnucashConverter import fireflyInterface as ffi
from gnucashConverter import data


class TestFireflyInterface(unittest.TestCase):
    def setUp(self) -> None:
        self._fireflyInterface = ffi.FireflyInterface(
            base_url="https://firefly.example",
            api_token="fake-token",
            default_balance_account_id=99,
        )

    def testCreateTransactions(self):
        # Prepare two transactions
        transactions = [
            data.Transaction(Date="2025-05-30", Deposit=-1619.25, Description="Test1", SourceAccount="Expenses:Shopping", DestinationAccount="Assets:Current"),
            data.Transaction(Date="2024-05-30", Deposit=-13.32, Description="Test2", SourceAccount="Expenses:Misc", DestinationAccount="Assets:Current"),
        ]

        # Mock the session.post method to capture calls and return a fake response
        mockResponse = Mock()
        mockResponse.raise_for_status = Mock()
        mockResponse.status_code = 201
        self._fireflyInterface._session.post = Mock(return_value=mockResponse)

        # Create transactions individually
        responses = [self._fireflyInterface.createTransaction(transaction) for transaction in transactions]

        # Ensure we received two responses
        self.assertEqual(len(responses), 2)

        # Ensure post was called twice
        self.assertEqual(self._fireflyInterface._session.post.call_count, 2)

        # Inspect the JSON payload of the first call
        firstCallArgs, firstCallKwargs = self._fireflyInterface._session.post.call_args_list[0]
        # URL should be the transactions endpoint
        self.assertTrue(str(firstCallArgs[0]).endswith("/api/v1/transactions"))
        payload = firstCallKwargs.get("json")
        self.assertIsNotNone(payload)

        # Payload should contain one transaction entry
        self.assertIn("transactions", payload)
        self.assertEqual(len(payload["transactions"]), 1)

        # The first transaction should be a withdrawal with source_name matching the account name
        transactionData = payload["transactions"][0]
        self.assertEqual(transactionData["type"], "withdrawal")
        self.assertEqual(transactionData["source_name"], transactions[0].SourceAccount)
        self.assertEqual(transactionData["amount"], "1619.25")
        self.assertEqual(transactionData["description"], "Test1")
        self.assertEqual(transactionData["date"], "2025-05-30")


if __name__ == "__main__":
    unittest.main()
