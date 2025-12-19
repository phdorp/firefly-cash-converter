from __future__ import annotations

from typing import List, Optional, Dict, Any
import requests

from gnucashConverter import data
from gnucashConverter.fireflyPayload import PayloadFactory


class FireflyInterface:
    """Minimal Firefly III REST API interface for creating transactions.

    Notes:
    - This class expects a Firefly III API token with permission to create transactions.
    - Provide `account_map` as a mapping from the `AccountName` values used in
      `data.Transaction` to Firefly account IDs (integers).
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
        payload = self._payloadFactory.toPayload(transaction)
        url = f"{self._api_url}/transactions"
        resp = self._session.post(url, json=payload)
        resp.raise_for_status()
        return resp
