from __future__ import annotations

import ast
import enum
import logging
from typing import Dict, List, Optional, Union, overload

import requests

from fireflyConverter import data
from fireflyConverter.fireflyPayload import PayloadFactory

logger = logging.getLogger(__name__)


class DuplicateTransactionHandle(enum.Enum):
    """Enumeration for handling duplicate transaction detection.

    Defines the behavior when a duplicate transaction is detected during
    creation via the Firefly III API.

    Attributes:
        IGNORE (str): Ignore duplicate transactions and continue processing.
        ERROR (str): Raise an error when a duplicate transaction is detected.
    """

    IGNORE = "ignore"
    ERROR = "error"


class FireflyInterface:
    """Minimal Firefly III REST API interface for creating and managing transactions.

    This class provides methods to interact with a Firefly III instance via its REST API,
    including creating accounts, managing transactions, and retrieving account information.

    The class handles API authentication, duplicate transaction detection, and error handling.
    Transactions are created with a single side mapped to the provided account and a balancing
    side using the default balance account.

    Attributes:
        _base_url (str): Base URL of the Firefly III instance (without trailing slash).
        _api_url (str): Full API endpoint URL (base_url/api/v1).
        _api_token (str): API token for authentication.
        _duplicate_transaction (DuplicateTransactionHandle): How to handle duplicate transactions.
        _default_balance_account_id (Optional[int]): Default account ID for balancing transactions.
        _payloadFactory (PayloadFactory): Factory for building API payloads.
        _session (requests.Session): Persistent HTTP session with authentication headers.

    Notes:
        - Requires a Firefly III API token with permissions to create transactions and accounts.
        - Provide account mappings to convert between internal account names and Firefly account IDs.
        - For each transaction created, a balancing side is generated to keep transactions balanced.
    """

    def __init__(
        self,
        base_url: str,
        api_token: str,
        default_balance_account_id: Optional[int] = None,
        duplicate_transaction: DuplicateTransactionHandle | str = DuplicateTransactionHandle.ERROR,
    ) -> None:
        """Initialize the Firefly III API interface.

        Args:
            base_url (str): Base URL of the Firefly III instance (e.g., "https://firefly.example.com").
            api_token (str): API token for authentication with the Firefly III instance.
            default_balance_account_id (Optional[int]): Default account ID to use for balancing transactions.
                Defaults to None.
            duplicate_transaction (DuplicateTransactionHandle | str): How to handle duplicate transactions.
                Can be a DuplicateTransactionHandle enum or string value ("ignore" or "error").
                Defaults to DuplicateTransactionHandle.ERROR.
        """
        self._base_url = base_url.rstrip("/")
        self._api_url = f"{self._base_url}/api/v1"
        self._api_token = api_token
        self._duplicate_transaction = (
            duplicate_transaction
            if isinstance(duplicate_transaction, DuplicateTransactionHandle)
            else DuplicateTransactionHandle(duplicate_transaction)
        )
        self._default_balance_account_id = default_balance_account_id
        self._payloadFactory = PayloadFactory()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._api_token}",
                "accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _postTransaction(self, transaction: data.BaseTransaction) -> requests.Response:
        """Post a transaction to the Firefly III API with error handling.

        Sends a transaction to the API and handles duplicate transaction detection
        based on the configured duplicate transaction handling mode.

        Args:
            transaction (data.BaseTransaction): The transaction to post.

        Returns:
            requests.Response: The HTTP response from the API.

        Raises:
            Exception: If the API returns an error and duplicate handling is not set to IGNORE.
            requests.HTTPError: If the HTTP request fails with a non-422 status code.
        """
        logger.debug(f"Creating transaction: {transaction.description} (amount: {transaction.amount})")
        payload = self._payloadFactory.toPayload(transaction)
        url = f"{self._api_url}/transactions"
        resp = self._session.post(url, json=payload)

        if resp.status_code == 422:
            errorMessage: str = ast.literal_eval(resp.text).get("message")
            isDuplicate = "duplicate" in errorMessage.lower()
            if isDuplicate and self._duplicate_transaction == DuplicateTransactionHandle.IGNORE:
                logger.debug("Duplicate transaction detected.")
                return resp
            else:
                logger.error(f"Error creating transaction: {errorMessage}")
                raise Exception(f"Error creating transaction: {errorMessage}")

        resp.raise_for_status()
        return resp

    def getAccounts(self) -> List[data.GetAccount]:
        """Retrieve the list of accounts from the Firefly III server.

        Fetches all accounts configured in the Firefly III instance and converts
        the API response data into GetAccount objects.

        Returns:
            List[data.GetAccount]: List of account objects with their attributes and metadata.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        logger.info("Retrieving accounts from Firefly III")
        url = f"{self._api_url}/accounts"
        response = self._session.get(url)
        response.raise_for_status()
        accountResponses: Dict = response.json().get("data", [])

        accounts: List[data.GetAccount] = []
        for response in accountResponses:
            accountData = response.get("attributes", {})
            accountData["id"] = response.get("id")
            accounts.append(data.GetAccount(**accountData))
        logger.info(f"Retrieved {len(accounts)} accounts from Firefly III")
        return accounts

    def createAccount(self, account: data.PostAccount) -> requests.Response:
        """Create a new account on the Firefly III server.

        Args:
            account (data.PostAccount): The account object to create.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        logger.info(f"Creating account: {account.name}")
        url = f"{self._api_url}/accounts"
        payload = self._payloadFactory.toPayload(account)
        resp = self._session.post(url, json=payload)
        resp.raise_for_status()
        logger.debug(f"Account {account.name} created successfully (status: {resp.status_code})")
        return resp

    def deleteAccount(self, account_id: str) -> requests.Response:
        """Delete an account on the Firefly III server.

        Args:
            account_id (str): The Firefly account ID to delete.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        logger.info(f"Deleting account: {account_id}")
        url = f"{self._api_url}/accounts/{account_id}"
        resp = self._session.delete(url)
        resp.raise_for_status()
        logger.debug(f"Account {account_id} deleted successfully")
        return resp

    def deleteAccounts(self, account_ids: Optional[List[str]] = None) -> None:
        """Delete one or more accounts from the Firefly III server.

        If no account IDs are provided, fetches all accounts from the server and deletes them.
        Otherwise, deletes only the specified accounts.

        Args:
            account_ids (Optional[List[str]]): List of Firefly account IDs to delete.
                If None, all accounts on the server will be fetched and deleted.
                Defaults to None.

        Returns:
            None

        Raises:
            requests.HTTPError: If any deletion request fails.
        """
        if account_ids is None:
            logger.info("No account IDs provided, fetching all accounts for deletion")
            accounts = self.getAccounts()
            account_ids = [account.id for account in accounts]

        logger.info(f"Deleting {len(account_ids)} accounts from Firefly III")
        for account_id in account_ids:
            self.deleteAccount(account_id)
        logger.info(f"Successfully deleted all {len(account_ids)} accounts")

    def deleteTransaction(self, transaction_id: str) -> requests.Response:
        """Delete a transaction on the Firefly III server.

        Args:
            transaction_id (str): The transaction journal ID to delete.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        url = f"{self._api_url}/transactions/{transaction_id}"
        resp = self._session.delete(url)
        resp.raise_for_status()
        return resp

    def purgeUserData(self, user_id: Optional[int] = None) -> requests.Response:
        """Purge all data for a user from the Firefly III server.

        Args:
            user_id (Optional[int]): ID of the user to purge. Defaults to current authenticated user.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        url = f"{self._api_url}/data/purge"
        params = {"user": user_id} if user_id is not None else None
        resp = self._session.delete(url, params=params)
        resp.raise_for_status()
        return resp

    def createTransaction(self, transaction: data.BaseTransaction) -> requests.Response:
        """Create a single transaction on the Firefly III server.

        Posts a transaction to the Firefly III API. Handles duplicate transaction
        detection and error reporting based on the configured duplicate handling mode.

        Args:
            transaction (data.BaseTransaction): The transaction to create.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            Exception: If the API returns an error (422 status) and duplicate handling
                is not set to IGNORE.
            requests.HTTPError: If the HTTP request fails with a non-422 status code.
        """
        return self._postTransaction(transaction)

    def getTransactions(
        self,
        limit: Optional[int] = None,
        page: Optional[int] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        type: Optional[str] = None,
    ) -> List[data.GetTransaction]:
        """Retrieve the list of transactions from the Firefly III server.

        Fetches transactions from the Firefly III instance with optional filtering
        and pagination. Converts the API response data into GetTransaction objects.

        Args:
            limit (Optional[int]): Number of items per page. Defaults to None.
            page (Optional[int]): Page number for pagination. Defaults to None.
            start (Optional[str]): Start date (YYYY-MM-DD format). Defaults to None.
            end (Optional[str]): End date (YYYY-MM-DD format). Defaults to None.
            type (Optional[str]): Filter by transaction type (withdrawal, deposit, etc.). Defaults to None.

        Returns:
            List[data.GetTransaction]: List of transaction objects with their attributes and metadata.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        url = f"{self._api_url}/transactions"
        params = self._payloadFactory.getTransactions(limit, page, start, end, type)
        response = self._session.get(url, params=params)
        response.raise_for_status()
        transactionResponses: Dict = response.json().get("data", [])

        transactions: List[data.GetTransaction] = []

        for response in transactionResponses:
            transactionData = response.get("attributes", {})
            # The transactions array contains the actual transaction splits
            transactionSplits = transactionData.get("transactions", [])
            for split in transactionSplits:
                split["transaction_id"] = response.get("id")
                split["transaction_journal_id"] = split.get("transaction_journal_id")
                split["user"] = split.get("user")
                transactions.append(data.GetTransaction(**split))
        return transactions

    def getRules(
        self,
        limit: int = 100,
        page: int = 1,
    ) -> List[data.GetRule]:
        """Retrieve the list of rules from the Firefly III server.

        Fetches rules from the Firefly III instance with optional pagination.
        Converts the API response data into GetRule objects.

        Args:
            limit (int): Number of items per page. Defaults to 100.
            page (int): Page number for pagination. Defaults to 1.

        Returns:
            List[data.GetRule]: List of rule objects with their attributes and metadata.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        url = f"{self._api_url}/rules"
        params = self._payloadFactory.getRules(limit, page)
        response = self._session.get(url, params=params)
        response.raise_for_status()
        ruleResponses: Dict = response.json().get("data", [])

        rules: List[data.GetRule] = []
        for response in ruleResponses:
            ruleData = response.get("attributes", {})
            ruleData["id"] = int(response.get("id"))
            rules.append(data.GetRule(**ruleData))
        return rules

    def getRuleGroups(
        self,
        limit: int = 100,
        page: int = 1,
    ) -> List[data.GetRuleGroup]:
        """Retrieve the list of rule groups from the Firefly III server.

        Fetches rule groups from the Firefly III instance with optional pagination.
        Converts the API response data into GetRuleGroup objects.

        Args:
            limit (int): Number of items per page. Defaults to 100.
            page (int): Page number for pagination. Defaults to 1.

        Returns:
            List[data.GetRuleGroup]: List of rule group objects with their attributes and metadata.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        url = f"{self._api_url}/rule-groups"
        params = self._payloadFactory.getRuleGroups(limit, page)
        response = self._session.get(url, params=params)
        response.raise_for_status()
        ruleGroupResponses: Dict = response.json().get("data", [])

        rule_groups: List[data.GetRuleGroup] = []
        for response in ruleGroupResponses:
            ruleGroupData = response.get("attributes", {})
            ruleGroupData["id"] = int(response.get("id"))
            rule_groups.append(data.GetRuleGroup(**ruleGroupData))
        return rule_groups

    def createRule(self, rule: data.PostRule) -> requests.Response:
        """Create a new rule on the Firefly III server.

        Args:
            rule (data.PostRule): The rule object to create.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        logger.info(f"Creating rule: {rule.title}")
        url = f"{self._api_url}/rules"
        payload = self._payloadFactory.toPayload(rule)
        response = self._session.post(url, json=payload)
        response.raise_for_status()
        logger.debug(f"Rule {rule.title} created successfully (status: {response.status_code})")
        return response

    def deleteRule(self, rule_id: int) -> requests.Response:
        """Delete a rule on the Firefly III server.

        Args:
            rule_id (int): The Firefly rule ID to delete.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        logger.info(f"Deleting rule: {rule_id}")
        url = f"{self._api_url}/rules/{rule_id}"
        resp = self._session.delete(url)
        resp.raise_for_status()
        logger.debug(f"Rule {rule_id} deleted successfully")
        return resp

    def deleteRules(self, rule_ids: Optional[List[int]] = None) -> None:
        """Delete one or more rules from the Firefly III server.

        If no rule IDs are provided, fetches all rules from the server and deletes them.
        Otherwise, deletes only the specified rules.

        Args:
            rule_ids (Optional[List[int]]): List of Firefly rule IDs to delete.
                If None, all rules on the server will be fetched and deleted.
                Defaults to None.

        Returns:
            None

        Raises:
            requests.HTTPError: If any deletion request fails.
        """
        if rule_ids is None:
            logger.info("No rule IDs provided, fetching all rules for deletion")
            rules = self.getRules()
            rule_ids = [rule.id for rule in rules]

        logger.info(f"Deleting {len(rule_ids)} rules from Firefly III")
        for rule_id in rule_ids:
            self.deleteRule(rule_id)
        logger.info(f"Successfully deleted all {len(rule_ids)} rules")

    def createRuleGroup(self, rule_group: data.PostRuleGroup) -> requests.Response:
        """Create a new rule group on the Firefly III server.

        Args:
            rule_group (data.PostRuleGroup): The rule group object to create.
        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        logger.info(f"Creating rule group: {rule_group.title}")
        url = f"{self._api_url}/rule-groups"
        payload = self._payloadFactory.toPayload(rule_group)
        response = self._session.post(url, json=payload)
        response.raise_for_status()
        logger.debug(f"Rule group {rule_group.title} created successfully (status: {response.status_code})")
        return response

    @overload
    def applyRuleGroup(
        self,
        rule_group_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        accounts: Optional[List[str]] = None,
    ) -> requests.Response:
        """Trigger/apply a rule group to existing transactions on the Firefly III server.

        Posts a request to the trigger endpoint to apply a rule group's rules to
        existing transactions, optionally filtered by date range and accounts.

        Args:
            rule_group_id (int): The Firefly rule group ID to trigger.
            start_date (Optional[str]): Start date for transactions to apply rules to (YYYY-MM-DD format). Defaults to None.
            end_date (Optional[str]): End date for transactions to apply rules to (YYYY-MM-DD format). Defaults to None.
            accounts (Optional[List[str]]): Array of account IDs to limit rule application to. Defaults to None.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        ...

    @overload
    def applyRuleGroup(
        self,
        rule_group_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        accounts: Optional[List[str]] = None,
    ) -> requests.Response:
        """Trigger/apply a rule group to existing transactions on the Firefly III server.

        Posts a request to the trigger endpoint to apply a rule group's rules to
        existing transactions, optionally filtered by date range and accounts.

        Args:
            rule_group_id (str): The Firefly rule group title to trigger.
            start_date (Optional[str]): Start date for transactions to apply rules to (YYYY-MM-DD format). Defaults to None.
            end_date (Optional[str]): End date for transactions to apply rules to (YYYY-MM-DD format). Defaults to None.
            accounts (Optional[List[str]]): Array of account IDs to limit rule application to. Defaults to None.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            ValueError: If no matching rule group is found or multiple matches exist.
            requests.HTTPError: If the HTTP request fails.
        """
        ...

    def applyRuleGroup(
        self,
        rule_group_id: Union[int, str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        accounts: Optional[List[str]] = None,
    ) -> requests.Response:
        """Trigger/apply a rule group to existing transactions on the Firefly III server.

        Posts a request to the trigger endpoint to apply a rule group's rules to
        existing transactions, optionally filtered by date range and accounts.

        Args:
            rule_group_id (Union[int, str]): The Firefly rule group ID or title to trigger.
            start_date (Optional[str]): Start date for transactions to apply rules to (YYYY-MM-DD format). Defaults to None.
            end_date (Optional[str]): End date for transactions to apply rules to (YYYY-MM-DD format). Defaults to None.
            accounts (Optional[List[str]]): Array of account IDs to limit rule application to. Defaults to None.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            ValueError: If rule_group_id is a title and no matching rule group is found or multiple matches exist.
            requests.HTTPError: If the HTTP request fails.
        """
        # Resolve title to ID if needed
        if isinstance(rule_group_id, str):
            rule_groups = self.getRuleGroups()
            matches = [rg for rg in rule_groups if rg.title == rule_group_id]
            if len(matches) == 0:
                raise ValueError(f"No rule group found with title: {rule_group_id}")
            elif len(matches) > 1:
                raise ValueError(f"Ambiguous rule group title '{rule_group_id}': found {len(matches)} matches")
            rule_group_id = matches[0].id

        logger.info(f"Triggering rule group: {rule_group_id}")
        url = f"{self._api_url}/rule-groups/{rule_group_id}/trigger"
        payload = self._payloadFactory.postApplyRuleGroup(start_date, end_date, accounts)
        response = self._session.post(url, json=payload)
        response.raise_for_status()
        logger.debug(f"Rule group {rule_group_id} triggered successfully (status: {response.status_code})")
        return response

    @overload
    def deleteRuleGroup(self, rule_group_id: int) -> requests.Response:
        """Delete a rule group on the Firefly III server.

        Args:
            rule_group_id (int): The Firefly rule group ID to delete.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        ...

    @overload
    def deleteRuleGroup(self, rule_group_id: str) -> requests.Response:
        """Delete a rule group on the Firefly III server.

        Args:
            rule_group_id (str): The Firefly rule group title to delete.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            ValueError: If no matching rule group is found or multiple matches exist.
            requests.HTTPError: If the HTTP request fails.
        """
        ...

    def deleteRuleGroup(self, rule_group_id: Union[int, str]) -> requests.Response:
        """Delete a rule group on the Firefly III server.

        Args:
            rule_group_id (Union[int, str]): The Firefly rule group ID or title to delete.

        Returns:
            requests.Response: The HTTP response from the Firefly API.

        Raises:
            ValueError: If rule_group_id is a title and no matching rule group is found or multiple matches exist.
            requests.HTTPError: If the HTTP request fails.
        """
        # Resolve title to ID if needed
        if isinstance(rule_group_id, str):
            rule_groups = self.getRuleGroups()
            matches = [rg for rg in rule_groups if rg.title == rule_group_id]
            if len(matches) == 0:
                raise ValueError(f"No rule group found with title: {rule_group_id}")
            elif len(matches) > 1:
                raise ValueError(f"Ambiguous rule group title '{rule_group_id}': found {len(matches)} matches")
            rule_group_id = matches[0].id

        logger.info(f"Deleting rule group: {rule_group_id}")
        url = f"{self._api_url}/rule-groups/{rule_group_id}"
        resp = self._session.delete(url)
        resp.raise_for_status()
        logger.debug(f"Rule group {rule_group_id} deleted successfully")
        return resp

    @overload
    def deleteRuleGroups(self, rule_group_ids: Optional[List[int]] = None) -> None:
        """Delete one or more rule groups from the Firefly III server.

        If no rule group IDs are provided, fetches all rule groups from the server and deletes them.
        Otherwise, deletes only the specified rule groups.

        Args:
            rule_group_ids (Optional[List[int]]): List of Firefly rule group IDs to delete.
                If None, all rule groups on the server will be fetched and deleted.
                Defaults to None.

        Returns:
            None

        Raises:
            requests.HTTPError: If any deletion request fails.
        """
        ...

    @overload
    def deleteRuleGroups(self, rule_group_ids: Optional[List[str]] = None) -> None:
        """Delete one or more rule groups from the Firefly III server.

        If no rule group IDs are provided, fetches all rule groups from the server and deletes them.
        Otherwise, deletes only the specified rule groups.

        Args:
            rule_group_ids (Optional[List[str]]): List of Firefly rule group titles to delete.
                If None, all rule groups on the server will be fetched and deleted.
                Defaults to None.

        Returns:
            None

        Raises:
            ValueError: If any rule_group_id is a title and no matching rule group is found or multiple matches exist.
            requests.HTTPError: If any deletion request fails.
        """
        ...

    def deleteRuleGroups(self, rule_group_ids: Optional[Union[List[int], List[str]]] = None) -> None:
        """Delete one or more rule groups from the Firefly III server.

        If no rule group IDs are provided, fetches all rule groups from the server and deletes them.
        Otherwise, deletes only the specified rule groups.

        Args:
            rule_group_ids (Optional[Union[List[int], List[str]]]): List of Firefly rule group IDs or titles to delete.
                If None, all rule groups on the server will be fetched and deleted.
                Defaults to None.

        Returns:
            None

        Raises:
            ValueError: If any rule_group_id is a title and no matching rule group is found or multiple matches exist.
            requests.HTTPError: If any deletion request fails.
        """
        if rule_group_ids is None:
            logger.info("No rule group IDs provided, fetching all rule groups for deletion")
            rule_groups = self.getRuleGroups()
            rule_group_ids = [rule_group.id for rule_group in rule_groups]

        logger.info(f"Deleting {len(rule_group_ids)} rule groups from Firefly III")
        for rule_group_id in rule_group_ids:
            self.deleteRuleGroup(rule_group_id)
        logger.info(f"Successfully deleted all {len(rule_group_ids)} rule groups")
