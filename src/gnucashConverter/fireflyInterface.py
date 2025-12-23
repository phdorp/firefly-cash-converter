from __future__ import annotations

from typing import List, Optional, Dict, Any
import requests

from gnucashConverter import data
from gnucashConverter.fireflyPayload import PayloadFactory


class FireflyInterface:
    """Minimal Firefly III REST API interface for creating transactions.

    Notes:
    - This class expects a Firefly III API token with permission to create transactions.
        - Provide `account_map` as a mapping from the account values used in
            `data.Transaction` (``SourceAccountName`` / ``DestinationAccountName``)
            to Firefly account IDs (integers).
        - For each transaction we create two sides: the mapped account and the
            balancing account (provided as `default_balance_account_id`). The amounts
            are opposite to keep transactions balanced.
    """

    def __init__(
        self,
        base_url: str,
        api_token: str,
        default_balance_account_id: Optional[int] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_url = f"{self._base_url}/api/v1"
        self._api_token = api_token
        self._default_balance_account_id = default_balance_account_id
        self._payloadFactory = PayloadFactory(format="json")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._api_token}",
                "accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _postTransaction(self, transaction: data.Transaction) -> requests.Response:
        payload = self._payloadFactory.toPayload(transaction)
        url = f"{self._api_url}/transactions"
        resp = self._session.post(url, json=payload)
        resp.raise_for_status()
        return resp

    def getAccounts(self) -> List[data.GetAccount]:
        """Retrieve the list of accounts from the Firefly III server.

        Returns:
            List of account dictionaries as returned by the Firefly API.
        """
        url = f"{self._api_url}/accounts"
        response = self._session.get(url)
        response.raise_for_status()
        accountResponses: Dict = response.json().get("data", [])

        accounts: List[data.GetAccount] = []
        for response in accountResponses:
            accountData = response.get("attributes", {})
            accountData["id"] = response.get("id")
            accounts.append(data.GetAccount(**accountData))
        return accounts

    def createAccount(self, account: data.PostAccount) -> requests.Response:
        """Create a new account on the Firefly III server.

        Args:
            name: Name of the new account.
            account_type: Type of the account (default: "asset").

        Returns:
            The `requests.Response` from the Firefly API.
        """
        url = f"{self._api_url}/accounts"
        payload = self._payloadFactory.toPayload(account)
        resp = self._session.post(url, json=payload)
        resp.raise_for_status()
        return resp

    def deleteAccount(self, account_id: str) -> requests.Response:
        """Delete an account on the Firefly III server.

        Args:
            account_id: The Firefly account id to delete.

        Returns:
            The `requests.Response` from the Firefly API.
        """
        url = f"{self._api_url}/accounts/{account_id}"
        resp = self._session.delete(url)
        resp.raise_for_status()
        return resp

    def createTransaction(self, transaction: data.Transaction) -> requests.Response:
        """Create a single transaction on the Firefly III server.

        Args:
            transaction: The `data.Transaction` to create.
            balance_account_id: The Firefly account id used to balance the transaction.
                If not provided, `self.default_balance_account_id` is used.
            currency: Currency code (default: "EUR").

        Returns:
            The `requests.Response` from the Firefly API.
        """
        accounts = self.getAccounts()
        transaction.SourceAccountName
        return self._postTransaction(transaction)
