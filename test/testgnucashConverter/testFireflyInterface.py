import unittest
from unittest.mock import Mock, patch

import requests

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
            data.PostTransaction(
                date="2025-05-30",
                amount=-1619.25,
                description="Test1",
                source_name="Expenses:Shopping",
                destination_name="Assets:Current",
            ),
            data.PostTransaction(
                date="2024-05-30",
                amount=-13.32,
                description="Test2",
                source_name="Expenses:Misc",
                destination_name="Assets:Current",
            ),
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
        self.assertEqual(transactionData["source_name"], transactions[0].source_name)
        self.assertEqual(transactionData["amount"], "1619.25")
        self.assertEqual(transactionData["description"], "Test1")
        self.assertEqual(transactionData["date"], "2025-05-30")

    def testGetAccounts(self):
        """Test retrieving accounts from Firefly III API."""
        # Create mock response data based on Firefly III API structure
        # Include all required fields for GetAccount dataclass
        mockApiResponse = {
            "data": [
                {
                    "id": "1",
                    "type": "accounts",
                    "attributes": {
                        "name": "Checking Account",
                        "type": "asset",
                        "account_role": "defaultAsset",
                        "current_balance": "1500.50",
                        "currency_code": "EUR",
                        "currency_id": None,
                        "active": True,
                        "order": 1,
                        "include_net_worth": True,
                        "iban": "DE89370400440532013000",
                        "bic": "COBADEFFXXX",
                        "account_number": "532013000",
                        "credit_card_type": None,
                        "monthly_payment_date": None,
                        "liability_type": None,
                        "liability_direction": None,
                        "interest": None,
                        "interest_period": None,
                        "opening_balance": None,
                        "opening_balance_date": None,
                        "virtual_balance": None,
                        "notes": None,
                        "latitude": None,
                        "longitude": None,
                        "zoom_level": None,
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-01T00:00:00Z",
                        "object_group_id": None,
                        "object_group_order": None,
                        "object_group_title": None,
                        "object_has_currency_setting": False,
                        "currency_name": "Euro",
                        "currency_symbol": "€",
                        "currency_decimal_places": 2,
                        "primary_currency_id": None,
                        "primary_currency_name": None,
                        "primary_currency_code": None,
                        "primary_currency_symbol": None,
                        "primary_currency_decimal_places": None,
                        "pc_current_balance": "1500.50",
                        "balance_difference": None,
                        "pc_balance_difference": None,
                        "pc_opening_balance": None,
                        "pc_virtual_balance": None,
                        "debt_amount": None,
                        "pc_debt_amount": None,
                        "current_balance_date": "2025-01-01",
                        "last_activity": "2025-01-01T00:00:00Z",
                    },
                },
                {
                    "id": "2",
                    "type": "accounts",
                    "attributes": {
                        "name": "Savings Account",
                        "type": "asset",
                        "account_role": "defaultAsset",
                        "current_balance": "5000.00",
                        "currency_code": "EUR",
                        "currency_id": None,
                        "active": True,
                        "order": 2,
                        "include_net_worth": True,
                        "iban": None,
                        "bic": None,
                        "account_number": None,
                        "credit_card_type": None,
                        "monthly_payment_date": None,
                        "liability_type": None,
                        "liability_direction": None,
                        "interest": None,
                        "interest_period": None,
                        "opening_balance": None,
                        "opening_balance_date": None,
                        "virtual_balance": None,
                        "notes": None,
                        "latitude": None,
                        "longitude": None,
                        "zoom_level": None,
                        "created_at": "2025-01-02T00:00:00Z",
                        "updated_at": "2025-01-02T00:00:00Z",
                        "object_group_id": None,
                        "object_group_order": None,
                        "object_group_title": None,
                        "object_has_currency_setting": False,
                        "currency_name": "Euro",
                        "currency_symbol": "€",
                        "currency_decimal_places": 2,
                        "primary_currency_id": None,
                        "primary_currency_name": None,
                        "primary_currency_code": None,
                        "primary_currency_symbol": None,
                        "primary_currency_decimal_places": None,
                        "pc_current_balance": "5000.00",
                        "balance_difference": None,
                        "pc_balance_difference": None,
                        "pc_opening_balance": None,
                        "pc_virtual_balance": None,
                        "debt_amount": None,
                        "pc_debt_amount": None,
                        "current_balance_date": "2025-01-02",
                        "last_activity": "2025-01-02T00:00:00Z",
                    },
                },
            ]
        }

        # Mock the session.get method
        mockResponse = Mock()
        mockResponse.json = Mock(return_value=mockApiResponse)
        mockResponse.raise_for_status = Mock()
        self._fireflyInterface._session.get = Mock(return_value=mockResponse)

        # Call getAccounts
        accounts = self._fireflyInterface.getAccounts()

        # Verify the GET request was made to the correct endpoint
        self._fireflyInterface._session.get.assert_called_once()
        callArgs = self._fireflyInterface._session.get.call_args
        self.assertTrue(str(callArgs[0][0]).endswith("/api/v1/accounts"))

        # Verify we got the correct number of accounts
        self.assertEqual(len(accounts), 2)

        # Verify first account data
        first_account = accounts[0]
        self.assertEqual(first_account.id, "1")
        self.assertEqual(first_account.name, "Checking Account")
        self.assertEqual(first_account.type, "asset")
        self.assertEqual(first_account.account_role, "defaultAsset")
        self.assertEqual(first_account.current_balance, "1500.50")
        self.assertEqual(first_account.currency_code, "EUR")
        self.assertTrue(first_account.active)
        self.assertEqual(first_account.iban, "DE89370400440532013000")

        # Verify second account data
        second_account = accounts[1]
        self.assertEqual(second_account.id, "2")
        self.assertEqual(second_account.name, "Savings Account")
        self.assertEqual(second_account.current_balance, "5000.00")
        self.assertIsNone(second_account.iban)

    def testCreateAccount(self):
        """Test creating a new account via Firefly III API."""
        # Create an asset account to post
        new_account = data.PostAssetAccount(
            name="New Investment Account",
            account_role="defaultAsset",
            iban="DE89370400440532013001",
            currency_code="EUR",
            active=True,
            notes="Test investment account",
        )

        # Mock response data based on Firefly III API structure
        mockApiResponse = {
            "data": {
                "id": "3",
                "type": "accounts",
                "attributes": {
                    "name": "New Investment Account",
                    "type": "asset",
                    "account_role": "defaultAsset",
                    "current_balance": "0.00",
                    "currency_code": "EUR",
                    "active": True,
                    "iban": "DE89370400440532013001",
                    "bic": None,
                    "account_number": None,
                    "created_at": "2025-12-25T10:00:00Z",
                    "updated_at": "2025-12-25T10:00:00Z",
                },
            }
        }

        # Mock the session.post method
        mockResponse = Mock()
        mockResponse.json = Mock(return_value=mockApiResponse)
        mockResponse.raise_for_status = Mock()
        mockResponse.status_code = 201
        self._fireflyInterface._session.post = Mock(return_value=mockResponse)

        # Create the account
        response = self._fireflyInterface.createAccount(new_account)

        # Verify the POST request was made to the correct endpoint
        self._fireflyInterface._session.post.assert_called_once()
        callArgs = self._fireflyInterface._session.post.call_args
        self.assertTrue(str(callArgs[0][0]).endswith("/api/v1/accounts"))

        # Verify the payload contains the account data
        payload = callArgs[1].get("json")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["name"], "New Investment Account")
        self.assertEqual(payload["type"], "asset")
        self.assertEqual(payload["currency_code"], "EUR")
        self.assertTrue(payload["active"])

        # Verify response
        self.assertEqual(response.status_code, 201)

    def testGetAccountsEmptyList(self):
        """Test retrieving accounts when no accounts exist."""
        # Mock empty response
        mockApiResponse = {"data": []}

        mockResponse = Mock()
        mockResponse.json = Mock(return_value=mockApiResponse)
        mockResponse.raise_for_status = Mock()
        self._fireflyInterface._session.get = Mock(return_value=mockResponse)

        # Call getAccounts
        accounts = self._fireflyInterface.getAccounts()

        # Verify we got an empty list
        self.assertEqual(len(accounts), 0)

    def testCreateAccountWithMinimalData(self):
        """Test creating an account with minimal required data."""
        # Create an expense account with minimal data
        new_account = data.PostExpenseAccount(
            name="Office Supplies",
        )

        # Mock response
        mockApiResponse = {
            "data": {
                "id": "4",
                "type": "accounts",
                "attributes": {
                    "name": "Office Supplies",
                    "type": "expense",
                    "current_balance": "0.00",
                    "active": True,
                    "created_at": "2025-12-25T10:00:00Z",
                    "updated_at": "2025-12-25T10:00:00Z",
                },
            }
        }

        mockResponse = Mock()
        mockResponse.json = Mock(return_value=mockApiResponse)
        mockResponse.raise_for_status = Mock()
        mockResponse.status_code = 201
        self._fireflyInterface._session.post = Mock(return_value=mockResponse)

        # Create the account
        response = self._fireflyInterface.createAccount(new_account)

        # Verify the response
        self.assertEqual(response.status_code, 201)

        # Verify the payload
        callArgs = self._fireflyInterface._session.post.call_args
        payload = callArgs[1].get("json")
        self.assertEqual(payload["name"], "Office Supplies")
        self.assertEqual(payload["type"], "expense")


if __name__ == "__main__":
    unittest.main()
