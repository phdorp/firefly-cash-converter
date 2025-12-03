from __future__ import annotations

from typing import List, Optional, Dict, Any
import requests

from gnucashConverter import data


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
        account_map: Optional[Dict[str, int]] = None,
        default_balance_account_id: Optional[int] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.account_map = account_map or {}
        self.default_balance_account_id = default_balance_account_id
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _get_account_id(self, account_name: str) -> Optional[int]:
        """Return account id from the provided `account_map` or None."""
        return self.account_map.get(account_name)

    def _transaction_payload(self, tx: data.Transaction, balance_account_id: int, currency: str = "EUR") -> Dict[str, Any]:
        """Build a conservative Firefly transaction payload for a single transaction.

        The payload uses two 'transactions' entries (debit and credit) to represent
        a simple transfer between accounts.
        """
        amt = float(tx.Deposit)
        # Firefly expects decimal strings for amounts
        amt_str = f"{amt:.2f}"
        neg_amt_str = f"{-amt:.2f}"

        mapped_account_id = self._get_account_id(tx.AccountName)
        if mapped_account_id is None:
            raise ValueError(f"No Firefly account id for account name: {tx.AccountName}")

        return {
            "transactions": [
                {
                    "account_id": mapped_account_id,
                    "amount": amt_str,
                    "description": tx.Description,
                    "book_date": tx.Date,
                    "currency_code": currency,
                },
                {
                    "account_id": balance_account_id,
                    "amount": neg_amt_str,
                    "description": tx.Description,
                    "book_date": tx.Date,
                    "currency_code": currency,
                },
            ],
            "meta": {"source": "gnucash-convert"},
        }

    def create_transaction(self, tx: data.Transaction, balance_account_id: Optional[int] = None, currency: str = "EUR") -> requests.Response:
        """Create a single transaction on the Firefly III server.

        Args:
            tx: The `data.Transaction` to create.
            balance_account_id: The Firefly account id used to balance the transaction.
                If not provided, `self.default_balance_account_id` is used.
            currency: Currency code (default: "EUR").

        Returns:
            The `requests.Response` from the Firefly API.
        """
        bal_id = balance_account_id or self.default_balance_account_id
        if bal_id is None:
            raise ValueError("A balancing account id must be provided (either via constructor or call)")

        payload = self._transaction_payload(tx, bal_id, currency=currency)
        url = f"{self.base_url}/api/v1/transactions"
        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        return resp

    def create_transactions(self, transactions: List[data.Transaction], balance_account_id: Optional[int] = None, currency: str = "EUR") -> List[requests.Response]:
        """Create multiple transactions. Returns list of responses.

        This method stops and raises on the first HTTP error.
        """
        results: List[requests.Response] = []
        bal_id = balance_account_id or self.default_balance_account_id
        if bal_id is None:
            raise ValueError("A balancing account id must be provided (either via constructor or call)")

        for tx in transactions:
            resp = self.create_transaction(tx, balance_account_id=bal_id, currency=currency)
            results.append(resp)

        return results
