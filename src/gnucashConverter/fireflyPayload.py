from typing import Optional, Any

from gnucashConverter import data


class PayloadFactory:
    def __init__(self, format: str = "json") -> None:
        self._format = format.lower()

    def toPayload(self, transaction: data.Transaction) -> dict[str, Any]:
        isWithdrawal = transaction.Deposit < 0
        sourceName = transaction.SourceAccount or None
        destinationName = transaction.DestinationAccount or None

        return self.postTransaction(
            type="withdrawal" if isWithdrawal else "deposit",
            date=transaction.Date,
            amount=str(abs(transaction.Deposit)),
            description=transaction.Description,
            source_name=sourceName,
            destination_name=destinationName,
            currency_code="EUR",
        )

    def postTransaction(
        self,
        type: str,
        date: str,
        amount: str,
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
        error_if_duplicate_hash: bool = False,
        apply_rules: bool = False,
        fire_webhooks: bool = True,
    ) -> dict[str, Any]:
        """
        Build a transaction payload for the Firefly III API.

        Returns a dictionary containing the transaction data with wrapper fields
        (error_if_duplicate_hash, apply_rules, fire_webhooks, group_title) and
        a transactions array containing the individual transaction object.
        """
        # Build the transaction object
        transaction: dict[str, Any] = {
            "type": type,
            "date": date,
            "amount": amount,
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
            "error_if_duplicate_hash": error_if_duplicate_hash,
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
        account_role: Optional[str] = None,
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
        """
        Build an account payload for the Firefly III API (storeAccount).
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
        """
        Build query parameters for listing accounts (GET /v1/accounts).
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
