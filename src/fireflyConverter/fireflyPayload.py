from typing import Any, Optional, Union, overload

from fireflyConverter.data import BaseTransaction, PostAccount, PostRule, PostRuleGroup


class PayloadFactory:
    """Factory class for building Firefly III API payloads.

    Converts transaction and account data objects into API-compatible payload dictionaries.
    Supports configurable duplicate transaction checking.

    Attributes:
        _duplicate_transaction_check (bool): Whether to check for duplicate transactions.
    """

    def __init__(self, duplicate_transaction_check: bool = True) -> None:
        """Initialize the payload factory.

        Args:
            duplicate_transaction_check (bool): Enable duplicate transaction checking. Defaults to True.
        """
        self._duplicate_transaction_check = duplicate_transaction_check

    @overload
    def toPayload(self, data: BaseTransaction) -> dict[str, Any]:
        """Convert a BaseTransaction to a payload dictionary."""

    @overload
    def toPayload(self, data: PostAccount) -> dict[str, Any]:
        """Convert a PostAccount to a payload dictionary."""

    @overload
    def toPayload(self, data: PostRule) -> dict[str, Any]:
        """Convert a PostRule to a payload dictionary."""

    @overload
    def toPayload(self, data: PostRuleGroup) -> dict[str, Any]:
        """Convert a PostRuleGroup to a payload dictionary."""

    def toPayload(self, data: Union[BaseTransaction, PostAccount, PostRule, PostRuleGroup]) -> dict[str, Any]:
        """Convert transaction, account, rule, or rule group data to a payload dictionary.

        Routes the conversion based on the input data type to the appropriate
        internal conversion method.

        Args:
            data (Union[BaseTransaction, PostAccount, PostRule, PostRuleGroup]): The data object to convert.

        Returns:
            dict[str, Any]: API-compatible payload dictionary.

        Raises:
            TypeError: If data is not a BaseTransaction, PostAccount, PostRule, or PostRuleGroup.
        """
        if isinstance(data, PostAccount):
            return self._toAccountPayload(data)
        elif isinstance(data, BaseTransaction):
            return self._toTransactionPayload(data)
        elif isinstance(data, PostRule):
            return self._toRulePayload(data)
        elif isinstance(data, PostRuleGroup):
            return self._toRuleGroupPayload(data)
        else:
            raise TypeError(f"Unsupported data type for payload conversion: {type(data)}")

    def _toTransactionPayload(self, transaction: BaseTransaction) -> dict[str, Any]:
        """Convert a BaseTransaction to a transaction payload.

        Args:
            transaction (BaseTransaction): The transaction to convert.

        Returns:
            dict[str, Any]: Transaction payload dictionary.
        """
        return self.postTransaction(**transaction.__dict__)

    def _toAccountPayload(self, account: PostAccount) -> dict[str, Any]:
        """Convert a PostAccount to an account payload.

        Args:
            account (PostAccount): The account to convert.

        Returns:
            dict[str, Any]: Account payload dictionary.
        """
        return self.postAccount(**account.__dict__)

    def _toRulePayload(self, rule: PostRule) -> dict[str, Any]:
        """Convert a PostRule to a rule payload.

        Args:
            rule (PostRule): The rule to convert.
        Returns:
            dict[str, Any]: Rule payload dictionary.
        """
        return self.postRule(**rule.__dict__)

    def _toRuleGroupPayload(self, rule_group: PostRuleGroup) -> dict[str, Any]:
        """Convert a PostRuleGroup to a rule group payload.

        Args:
            rule_group (PostRuleGroup): The rule group to convert.
        Returns:
            dict[str, Any]: Rule group payload dictionary.
        """
        return self.postRuleGroup(**rule_group.__dict__)

    def postTransaction(
        self,
        type: str,
        date: str,
        amount: Union[str, float],
        description: str,
        source_name: Optional[str] = None,
        source_id: Optional[str] = None,
        destination_name: Optional[str] = None,
        destination_id: Optional[str] = None,
        category_name: Optional[str] = None,
        category_id: Optional[str] = None,
        budget_name: Optional[str] = None,
        budget_id: Optional[str] = None,
        bill_name: Optional[str] = None,
        bill_id: Optional[str] = None,
        currency_code: Optional[str] = None,
        currency_id: Optional[str] = None,
        foreign_amount: Optional[str] = None,
        foreign_currency_code: Optional[str] = None,
        foreign_currency_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        notes: Optional[str] = None,
        internal_reference: Optional[str] = None,
        external_id: Optional[str] = None,
        external_url: Optional[str] = None,
        reconciled: bool = False,
        piggy_bank_id: Optional[int] = None,
        piggy_bank_name: Optional[str] = None,
        order: int = 0,
        sepa_cc: Optional[str] = None,
        sepa_ct_op: Optional[str] = None,
        sepa_ct_id: Optional[str] = None,
        sepa_db: Optional[str] = None,
        sepa_country: Optional[str] = None,
        sepa_ep: Optional[str] = None,
        sepa_ci: Optional[str] = None,
        sepa_batch_id: Optional[str] = None,
        interest_date: Optional[str] = None,
        book_date: Optional[str] = None,
        process_date: Optional[str] = None,
        due_date: Optional[str] = None,
        payment_date: Optional[str] = None,
        invoice_date: Optional[str] = None,
        group_title: Optional[str] = None,
        apply_rules: bool = False,
        fire_webhooks: bool = True,
    ) -> dict[str, Any]:
        """Build a transaction payload for the Firefly III API.

        Constructs a complete API request payload for creating a transaction, including
        wrapper fields for duplicate checking, rule application, and webhook firing.
        Returns a dictionary with a transactions array containing the transaction object.

        Args:
            type (str): Transaction type ("withdrawal", "deposit").
            date (str): Transaction date in ISO 8601 format.
            amount (Union[str, float]): Transaction amount.
            description (str): Transaction description.
            source_name (Optional[str]): Source account name. Defaults to None.
            source_id (Optional[str]): Source account ID. Defaults to None.
            destination_name (Optional[str]): Destination account name. Defaults to None.
            destination_id (Optional[str]): Destination account ID. Defaults to None.
            category_name (Optional[str]): Category name. Defaults to None.
            category_id (Optional[str]): Category ID. Defaults to None.
            budget_name (Optional[str]): Budget name. Defaults to None.
            budget_id (Optional[str]): Budget ID. Defaults to None.
            bill_name (Optional[str]): Bill name. Defaults to None.
            bill_id (Optional[str]): Bill ID. Defaults to None.
            currency_code (Optional[str]): Transaction currency code. Defaults to None.
            currency_id (Optional[str]): Transaction currency ID. Defaults to None.
            foreign_amount (Optional[str]): Foreign currency amount. Defaults to None.
            foreign_currency_code (Optional[str]): Foreign currency code. Defaults to None.
            foreign_currency_id (Optional[str]): Foreign currency ID. Defaults to None.
            tags (Optional[list[str]]): Transaction tags. Defaults to None.
            notes (Optional[str]): Additional notes. Defaults to None.
            internal_reference (Optional[str]): Internal reference number. Defaults to None.
            external_id (Optional[str]): External system reference ID. Defaults to None.
            external_url (Optional[str]): External system reference URL. Defaults to None.
            reconciled (bool): Whether transaction is reconciled. Defaults to False.
            piggy_bank_id (Optional[int]): Piggy bank ID. Defaults to None.
            piggy_bank_name (Optional[str]): Piggy bank name. Defaults to None.
            order (int): Transaction order. Defaults to 0.
            sepa_cc (Optional[str]): SEPA clearing code. Defaults to None.
            sepa_ct_op (Optional[str]): SEPA credit transfer operation. Defaults to None.
            sepa_ct_id (Optional[str]): SEPA credit transfer ID. Defaults to None.
            sepa_db (Optional[str]): SEPA direct debit. Defaults to None.
            sepa_country (Optional[str]): SEPA country code. Defaults to None.
            sepa_ep (Optional[str]): SEPA end-to-end reference. Defaults to None.
            sepa_ci (Optional[str]): SEPA creditor identifier. Defaults to None.
            sepa_batch_id (Optional[str]): SEPA batch ID. Defaults to None.
            interest_date (Optional[str]): Interest calculation date. Defaults to None.
            book_date (Optional[str]): Book date. Defaults to None.
            process_date (Optional[str]): Process date. Defaults to None.
            due_date (Optional[str]): Due date. Defaults to None.
            payment_date (Optional[str]): Payment date. Defaults to None.
            invoice_date (Optional[str]): Invoice date. Defaults to None.
            group_title (Optional[str]): Title for transaction group. Defaults to None.
            apply_rules (bool): Whether to apply Firefly III rules. Defaults to False.
            fire_webhooks (bool): Whether to fire webhooks. Defaults to True.

        Returns:
            dict[str, Any]: API payload with transaction data and configuration options.
        """
        # Build the transaction object
        transaction: dict[str, Any] = {
            "type": type,
            "date": date,
            "amount": str(amount),
            "description": description,
            "order": order,
            "reconciled": reconciled,
        }

        # Add optional account information
        if source_id:
            transaction["source_id"] = source_id
        if source_name:
            transaction["source_name"] = source_name
        if destination_id:
            transaction["destination_id"] = destination_id
        if destination_name:
            transaction["destination_name"] = destination_name

        # Add optional category/budget/bill information
        if category_id:
            transaction["category_id"] = category_id
        if category_name:
            transaction["category_name"] = category_name
        if budget_id:
            transaction["budget_id"] = budget_id
        if budget_name:
            transaction["budget_name"] = budget_name
        if bill_id:
            transaction["bill_id"] = bill_id
        if bill_name:
            transaction["bill_name"] = bill_name

        # Add optional currency information
        if currency_code:
            transaction["currency_code"] = currency_code
        if currency_id:
            transaction["currency_id"] = currency_id
        if foreign_amount:
            transaction["foreign_amount"] = foreign_amount
        if foreign_currency_code:
            transaction["foreign_currency_code"] = foreign_currency_code
        if foreign_currency_id:
            transaction["foreign_currency_id"] = foreign_currency_id

        # Add optional metadata
        if tags:
            transaction["tags"] = tags
        if notes:
            transaction["notes"] = notes
        if internal_reference:
            transaction["internal_reference"] = internal_reference
        if external_id:
            transaction["external_id"] = external_id
        if external_url:
            transaction["external_url"] = external_url

        # Add optional piggy bank information
        if piggy_bank_id:
            transaction["piggy_bank_id"] = piggy_bank_id
        if piggy_bank_name:
            transaction["piggy_bank_name"] = piggy_bank_name

        # Add optional SEPA information
        if sepa_cc:
            transaction["sepa_cc"] = sepa_cc
        if sepa_ct_op:
            transaction["sepa_ct_op"] = sepa_ct_op
        if sepa_ct_id:
            transaction["sepa_ct_id"] = sepa_ct_id
        if sepa_db:
            transaction["sepa_db"] = sepa_db
        if sepa_country:
            transaction["sepa_country"] = sepa_country
        if sepa_ep:
            transaction["sepa_ep"] = sepa_ep
        if sepa_ci:
            transaction["sepa_ci"] = sepa_ci
        if sepa_batch_id:
            transaction["sepa_batch_id"] = sepa_batch_id

        # Add optional date information
        if interest_date:
            transaction["interest_date"] = interest_date
        if book_date:
            transaction["book_date"] = book_date
        if process_date:
            transaction["process_date"] = process_date
        if due_date:
            transaction["due_date"] = due_date
        if payment_date:
            transaction["payment_date"] = payment_date
        if invoice_date:
            transaction["invoice_date"] = invoice_date

        # Build the payload wrapper
        payload: dict[str, Any] = {
            "error_if_duplicate_hash": self._duplicate_transaction_check,
            "apply_rules": apply_rules,
            "fire_webhooks": fire_webhooks,
            "transactions": [transaction],
        }

        # Add optional group title
        if group_title:
            payload["group_title"] = group_title

        return payload

    def postAccount(
        self,
        name: str,
        type: str,
        account_role: str,
        iban: Optional[str] = None,
        bic: Optional[str] = None,
        account_number: Optional[str] = None,
        opening_balance: Optional[str] = None,
        opening_balance_date: Optional[str] = None,
        virtual_balance: Optional[str] = None,
        currency_id: Optional[str] = None,
        currency_code: Optional[str] = None,
        active: Optional[bool] = None,
        order: Optional[int] = None,
        include_net_worth: Optional[bool] = None,
        credit_card_type: Optional[str] = None,
        monthly_payment_date: Optional[str] = None,
        liability_type: Optional[str] = None,
        liability_direction: Optional[str] = None,
        interest: Optional[str] = None,
        interest_period: Optional[str] = None,
        notes: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        zoom_level: Optional[int] = None,
    ) -> dict[str, Any]:
        """Build an account payload for the Firefly III API.

        Constructs an API request payload for creating or updating an account.
        Only non-None values are included in the payload.

        Args:
            name (str): Account name.
            type (str): Account type (asset, expense).
            account_role (str): Specific role for the account.
            iban (Optional[str]): International Bank Account Number. Defaults to None.
            bic (Optional[str]): Bank Identifier Code. Defaults to None.
            account_number (Optional[str]): Account number. Defaults to None.
            opening_balance (Optional[str]): Opening balance amount. Defaults to None.
            opening_balance_date (Optional[str]): Opening balance date. Defaults to None.
            virtual_balance (Optional[str]): Virtual balance amount. Defaults to None.
            currency_id (Optional[str]): Currency ID. Defaults to None.
            currency_code (Optional[str]): Currency code. Defaults to None.
            active (Optional[bool]): Whether account is active. Defaults to None.
            order (Optional[int]): Account ordering. Defaults to None.
            include_net_worth (Optional[bool]): Include in net worth calculation. Defaults to None.
            credit_card_type (Optional[str]): Credit card type. Defaults to None.
            monthly_payment_date (Optional[str]): Monthly payment date for credit cards. Defaults to None.
            liability_type (Optional[str]): Liability type. Defaults to None.
            liability_direction (Optional[str]): Liability direction. Defaults to None.
            interest (Optional[str]): Interest rate. Defaults to None.
            interest_period (Optional[str]): Interest period. Defaults to None.
            notes (Optional[str]): Account notes. Defaults to None.
            latitude (Optional[float]): Account location latitude. Defaults to None.
            longitude (Optional[float]): Account location longitude. Defaults to None.
            zoom_level (Optional[int]): Account location zoom level. Defaults to None.

        Returns:
            dict[str, Any]: API payload with account data.
        """
        payload: dict[str, Any] = {
            "name": name,
            "type": type,
        }

        if iban:
            payload["iban"] = iban
        if bic:
            payload["bic"] = bic
        if account_number:
            payload["account_number"] = account_number
        if opening_balance:
            payload["opening_balance"] = opening_balance
        if opening_balance_date:
            payload["opening_balance_date"] = opening_balance_date
        if virtual_balance:
            payload["virtual_balance"] = virtual_balance

        if currency_id:
            payload["currency_id"] = currency_id
        if currency_code:
            payload["currency_code"] = currency_code

        if active is not None:
            payload["active"] = active
        if order is not None:
            payload["order"] = order
        if include_net_worth is not None:
            payload["include_net_worth"] = include_net_worth

        if account_role:
            payload["account_role"] = account_role
        if credit_card_type:
            payload["credit_card_type"] = credit_card_type
        if monthly_payment_date:
            payload["monthly_payment_date"] = monthly_payment_date

        if liability_type:
            payload["liability_type"] = liability_type
        if liability_direction:
            payload["liability_direction"] = liability_direction
        if interest:
            payload["interest"] = interest
        if interest_period:
            payload["interest_period"] = interest_period

        if notes:
            payload["notes"] = notes
        if latitude is not None:
            payload["latitude"] = latitude
        if longitude is not None:
            payload["longitude"] = longitude
        if zoom_level is not None:
            payload["zoom_level"] = zoom_level

        return payload

    def getAccounts(
        self,
        limit: Optional[int] = None,
        page: Optional[int] = None,
        account_type: Optional[str] = None,
        date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Build query parameters for listing accounts.

        Constructs parameters for a GET request to the Firefly III accounts endpoint
        (/v1/accounts). Only non-None parameters are included.

        Args:
            limit (Optional[int]): Maximum number of accounts to return. Defaults to None.
            page (Optional[int]): Page number for pagination. Defaults to None.
            account_type (Optional[str]): Filter by account type. Defaults to None.
            date (Optional[str]): Filter by date in ISO 8601 format. Defaults to None.

        Returns:
            dict[str, Any]: Query parameters dictionary.
        """
        params: dict[str, Any] = {}

        if limit is not None:
            params["limit"] = limit
        if page is not None:
            params["page"] = page
        if account_type:
            params["type"] = account_type
        if date:
            params["date"] = date

        return params

    def getTransactions(
        self,
        limit: Optional[int] = None,
        page: Optional[int] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        type: Optional[str] = None,
    ) -> dict[str, Any]:
        """Build query parameters for listing transactions.

        Constructs parameters for a GET request to the Firefly III transactions endpoint
        (/v1/transactions). Only non-None parameters are included.

        Args:
            limit (Optional[int]): Number of items per page. Defaults to None.
            page (Optional[int]): Page number for pagination. Defaults to None.
            start (Optional[str]): Start date of the range (inclusive) in YYYY-MM-DD format. Defaults to None.
            end (Optional[str]): End date of the range (inclusive) in YYYY-MM-DD format. Defaults to None.
            type (Optional[str]): Filter on transaction type(s). Available values: all, withdrawal,
                withdrawals, expense, deposit, deposits, income, transfer, transfers, opening_balance,
                reconciliation, special, specials, default. Defaults to None.

        Returns:
            dict[str, Any]: Query parameters dictionary.
        """
        params: dict[str, Any] = {}

        if limit is not None:
            params["limit"] = limit
        if page is not None:
            params["page"] = page
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if type:
            params["type"] = type

        return params

    def getRules(
        self,
        limit: int = 100,
        page: int = 1,
    ) -> dict[str, Any]:
        """Build query parameters for listing rules.

        Constructs parameters for a GET request to the Firefly III rules endpoint
        (/v1/rules). Only non-None parameters are included.

        Args:
            limit (int): Number of items per page. The default pagination is per 50 items. Defaults to 100.
            page (int): Page number. The default pagination is per 50 items. Defaults to 1.

        Returns:
            dict[str, Any]: Query parameters dictionary.
        """
        return {"limit": limit, "page": page}

    def getRuleGroups(
        self,
        limit: int = 100,
        page: int = 1,
    ) -> dict[str, Any]:
        """Build query parameters for listing rule groups.

        Constructs parameters for a GET request to the Firefly III rule groups endpoint
        (/v1/rule-groups). Only non-None parameters are included.

        Args:
            limit (int): Number of items per page. The default pagination is per 50 items. Defaults to 100.
            page (int): Page number. The default pagination is per 50 items. Defaults to 1.

        Returns:
            dict[str, Any]: Query parameters dictionary.
        """
        return {"limit": limit, "page": page}

    def postRule(
        self,
        title: str,
        description: Optional[str] = None,
        rule_group_id: Optional[int] = None,
        rule_group_title: Optional[str] = None,
        order: Optional[int] = None,
        trigger: Optional[str] = None,
        active: Optional[bool] = None,
        strict: Optional[bool] = None,
        stop_processing: Optional[bool] = None,
        triggers: Optional[list] = None,
        actions: Optional[list] = None,
    ) -> dict[str, Any]:
        """Build a rule payload for the Firefly III API.

        Constructs a complete API request payload for creating a rule, including
        triggers and actions. Returns a dictionary with the rule object.

        Args:
            title (str): Rule title.
            description (Optional[str]): Rule description. Defaults to None.
            rule_group_id (Optional[int]): Associated rule group ID. Defaults to None.
            rule_group_title (Optional[str]): Associated rule group title. Defaults to None.
            order (Optional[int]): Rule execution order. Defaults to None.
            trigger (Optional[str]): Rule trigger type (e.g., 'store-journal', 'update-journal'). Defaults to None.
            active (Optional[bool]): Whether rule is active. Defaults to None.
            strict (Optional[bool]): Whether rule uses strict matching. Defaults to None.
            stop_processing (Optional[bool]): Whether to stop processing rules after this one. Defaults to None.
            triggers (Optional[list]): List of rule triggers with conditions. Each trigger should be a dict
                with 'type', 'value', 'order', 'active', 'prohibited', and 'stop_processing' keys. Defaults to None.
            actions (Optional[list]): List of rule actions to execute. Each action should be a dict
                with 'type', 'value', 'order', 'active', and 'stop_processing' keys. Defaults to None.

        Returns:
            dict[str, Any]: API payload with rule data.
        """
        payload: dict[str, Any] = {"title": title}
        payload.update(
            {
                key: value
                for key, value in {
                    "description": description,
                    "rule_group_id": rule_group_id,
                    "rule_group_title": rule_group_title,
                    "order": order,
                    "trigger": trigger,
                    "active": active,
                    "strict": strict,
                    "stop_processing": stop_processing,
                    "triggers": triggers,
                    "actions": actions,
                }.items()
                if value is not None
            }
        )
        return payload

    def postRuleGroup(
        self,
        title: str,
        description: Optional[str] = None,
        order: Optional[int] = None,
        active: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Build a rule group payload for the Firefly III API.

        Constructs a complete API request payload for creating a rule group.
        Returns a dictionary with the rule group object.

        Args:
            title (str): Rule group title.
            description (Optional[str]): Rule group description. Defaults to None.
            order (Optional[int]): Rule group execution order. Defaults to None.
            active (Optional[bool]): Whether rule group is active. Defaults to None.

        Returns:
            dict[str, Any]: API payload with rule group data.
        """
        payload: dict[str, Any] = {"title": title}
        payload.update(
            {
                key: value
                for key, value in {
                    "description": description,
                    "order": order,
                    "active": active,
                }.items()
                if value is not None
            }
        )
        return payload

    def postApplyRuleGroup(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        accounts: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Build a payload for triggering/applying a rule group to transactions.

        Constructs a payload for the POST /v1/rule-groups/{id}/trigger endpoint
        which applies a rule group to existing transactions.

        Args:
            start_date (Optional[str]): Start date for transactions to apply rules to (YYYY-MM-DD format). Defaults to None.
            end_date (Optional[str]): End date for transactions to apply rules to (YYYY-MM-DD format). Defaults to None.
            accounts (Optional[list[str]]): Array of account IDs to limit rule application to. Defaults to None.

        Returns:
            dict[str, Any]: API payload for triggering rule group application.
        """
        payload: dict[str, Any] = {}
        payload.update(
            {
                key: value
                for key, value in {
                    "start_date": start_date,
                    "end_date": end_date,
                    "accounts": accounts,
                }.items()
                if value is not None
            }
        )
        return payload
