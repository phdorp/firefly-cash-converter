import dataclasses as dc
import enum


class TransactionType(enum.Enum):
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"


@dc.dataclass
class BaseTransaction:
    """Base transaction data class for financial transactions.

    Attributes:
        date (str): Transaction date.
        amount (float): Transaction amount.
        description (str): Transaction description or memo.
        type (str): Transaction type (withdrawal or deposit).
        reconciled (bool): Whether transaction is reconciled.
        order (int): Transaction sequence order.
        source_name (str | None): Source account name.
        destination_name (str | None): Destination account name.
        currency_id (int | None): Transaction currency ID.
        currency_code (str | None): Transaction currency code.
        foreign_amount (float | None): Amount in foreign currency.
        foreign_currency_id (int | None): Foreign currency ID.
        foreign_currency_code (str | None): Foreign currency code.
        budget_id (int | None): Associated budget ID.
        budget_name (str | None): Associated budget name.
        category_id (int | None): Transaction category ID.
        category_name (str | None): Transaction category name.
        source_id (int | None): Source account ID.
        destination_id (int | None): Destination account ID.
        piggy_bank_id (int | None): Associated piggy bank ID.
        piggy_bank_name (str | None): Associated piggy bank name.
        bill_id (int | None): Associated bill ID.
        bill_name (str | None): Associated bill name.
        tags (str | None): Transaction tags.
        notes (str | None): Additional notes.
        internal_reference (str | None): Internal reference number.
        external_id (str | None): External system reference ID.
        external_url (str | None): External system reference URL.
        sepa_cc (str | None): SEPA clearing code.
        sepa_ct_op (str | None): SEPA credit transfer operation.
        sepa_ct_id (str | None): SEPA credit transfer ID.
        sepa_db (str | None): SEPA direct debit.
        sepa_country (str | None): SEPA country code.
        sepa_ep (str | None): SEPA end-to-end reference.
        sepa_ci (str | None): SEPA creditor identifier.
        sepa_batch_id (str | None): SEPA batch ID.
        interest_date (str | None): Interest calculation date.
        book_date (str | None): Book date.
        process_date (str | None): Process date.
    """

    date: str
    amount: float
    description: str
    type: str
    reconciled: bool
    order: int
    source_name: str | None
    destination_name: str | None
    currency_id: int | None
    currency_code: str | None
    foreign_amount: float | None
    foreign_currency_id: int | None
    foreign_currency_code: str | None
    budget_id: int | None
    budget_name: str | None
    category_id: int | None
    category_name: str | None
    source_id: int | None
    destination_id: int | None
    piggy_bank_id: int | None
    piggy_bank_name: str | None
    bill_id: int | None
    bill_name: str | None
    tags: str | None
    notes: str | None
    internal_reference: str | None
    external_id: str | None
    external_url: str | None
    sepa_cc: str | None
    sepa_ct_op: str | None
    sepa_ct_id: str | None
    sepa_db: str | None
    sepa_country: str | None
    sepa_ep: str | None
    sepa_ci: str | None
    sepa_batch_id: str | None
    interest_date: str | None
    book_date: str | None
    process_date: str | None
    due_date: str | None
    payment_date: str | None
    invoice_date: str | None


@dc.dataclass
class GetTransaction(BaseTransaction):
    """Transaction data class for retrieving transaction information from Firefly III.

    Extends BaseTransaction with additional fields returned from the API including
    transaction metadata, user information, and related entity details.

    Attributes:
        transaction_id (int): Transaction identifier. Defaults to 0.
        transaction_journal_id (str | None): ID of the underlying transaction journal. Defaults to None.
        user (str | None): User ID who created the transaction. Defaults to None.
        created_at (str | None): Transaction creation timestamp. Defaults to None.
        updated_at (str | None): Last update timestamp. Defaults to None.
        currency_name (str | None): Transaction currency name. Defaults to None.
        currency_symbol (str | None): Transaction currency symbol. Defaults to None.
        currency_decimal_places (int | None): Currency decimal places. Defaults to None.
        foreign_currency_name (str | None): Foreign currency name. Defaults to None.
        foreign_currency_symbol (str | None): Foreign currency symbol. Defaults to None.
        foreign_currency_decimal_places (int | None): Foreign currency decimal places. Defaults to None.
        primary_currency_id (int | None): Primary currency ID. Defaults to None.
        primary_currency_code (str | None): Primary currency code. Defaults to None.
        primary_currency_name (str | None): Primary currency name. Defaults to None.
        primary_currency_symbol (str | None): Primary currency symbol. Defaults to None.
        primary_currency_decimal_places (int | None): Primary currency decimal places. Defaults to None.
        source_iban (str | None): Source account IBAN. Defaults to None.
        source_type (str | None): Source account type. Defaults to None.
        destination_iban (str | None): Destination account IBAN. Defaults to None.
        destination_type (str | None): Destination account type. Defaults to None.
        latitude (float | None): Transaction location latitude. Defaults to None.
        longitude (float | None): Transaction location longitude. Defaults to None.
        zoom_level (int | None): Transaction location zoom level. Defaults to None.
        has_attachments (bool | None): Whether transaction has attachments. Defaults to None.
        import_hash_v2 (str | None): Hash value of original import transaction. Defaults to None.
        recurrence_id (str | None): Associated recurring transaction ID. Defaults to None.
        recurrence_total (int | None): Total number of recurrences. Defaults to None.
        recurrence_count (int | None): Current recurrence count. Defaults to None.
        object_has_currency_setting (bool | None): Whether object has currency setting. Defaults to None.
        pc_amount (str | None): Primary currency amount. Defaults to None.
        pc_foreign_amount (str | None): Primary currency foreign amount. Defaults to None.
        source_balance_after (str | None): Source account balance after transaction. Defaults to None.
        source_balance_dirty (str | None): Source account balance dirty flag. Defaults to None.
        pc_source_balance_after (str | None): Primary currency source balance after transaction. Defaults to None.
        destination_balance_after (str | None): Destination account balance after transaction. Defaults to None.
        destination_balance_dirty (str | None): Destination account balance dirty flag. Defaults to None.
        pc_destination_balance_after (str | None): Primary currency destination balance after transaction. Defaults to None.
        subscription_id (str | None): Associated subscription ID. Defaults to None.
        subscription_name (str | None): Associated subscription name. Defaults to None.
        original_source (str | None): Original source of transaction. Defaults to None.
    """

    transaction_id: int = 0
    transaction_journal_id: str | None = None
    user: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    currency_name: str | None = None
    currency_symbol: str | None = None
    currency_decimal_places: int | None = None
    foreign_currency_name: str | None = None
    foreign_currency_symbol: str | None = None
    foreign_currency_decimal_places: int | None = None
    primary_currency_id: int | None = None
    primary_currency_code: str | None = None
    primary_currency_name: str | None = None
    primary_currency_symbol: str | None = None
    primary_currency_decimal_places: int | None = None
    source_iban: str | None = None
    source_type: str | None = None
    destination_iban: str | None = None
    destination_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    zoom_level: int | None = None
    has_attachments: bool | None = None
    import_hash_v2: str | None = None
    recurrence_id: str | None = None
    recurrence_total: int | None = None
    recurrence_count: int | None = None
    object_has_currency_setting: bool | None = None
    # Primary-currency converted amounts and balances
    pc_amount: str | None = None
    pc_foreign_amount: str | None = None
    source_balance_after: str | None = None
    source_balance_dirty: str | None = None
    pc_source_balance_after: str | None = None
    destination_balance_after: str | None = None
    destination_balance_dirty: str | None = None
    pc_destination_balance_after: str | None = None
    # Optional linkage and provenance
    subscription_id: str | None = None
    subscription_name: str | None = None
    original_source: str | None = None
    piggy_bank_id: int | None = None
    piggy_bank_name: str | None = None
    bill_id: int | None = None
    bill_name: str | None = None
    tags: str | None = None
    notes: str | None = None
    internal_reference: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    sepa_cc: str | None = None
    sepa_ct_op: str | None = None
    sepa_ct_id: str | None = None
    sepa_db: str | None = None
    sepa_country: str | None = None
    sepa_ep: str | None = None
    sepa_ci: str | None = None
    sepa_batch_id: str | None = None
    interest_date: str | None = None
    book_date: str | None = None
    process_date: str | None = None
    due_date: str | None = None
    payment_date: str | None = None
    invoice_date: str | None = None


@dc.dataclass
class PostTransaction(BaseTransaction):
    """Transaction data class for posting transactions to Firefly III.

    Extends BaseTransaction with default values optimized for API submission.
    All optional fields default to None, and required fields have sensible defaults.

    Attributes:
        order (int): Transaction sequence order. Defaults to 0.
        reconciled (bool): Whether transaction is reconciled. Defaults to True.
        source_name (str | None): Source account name. Defaults to None.
        destination_name (str | None): Destination account name. Defaults to None.
        currency_id (int | None): Transaction currency ID. Defaults to None.
        currency_code (str | None): Transaction currency code. Defaults to None.
        foreign_amount (float | None): Amount in foreign currency. Defaults to None.
        foreign_currency_id (int | None): Foreign currency ID. Defaults to None.
        foreign_currency_code (str | None): Foreign currency code. Defaults to None.
        budget_id (int | None): Associated budget ID. Defaults to None.
        budget_name (str | None): Associated budget name. Defaults to None.
        category_id (int | None): Transaction category ID. Defaults to None.
        category_name (str | None): Transaction category name. Defaults to None.
        source_id (int | None): Source account ID. Defaults to None.
        destination_id (int | None): Destination account ID. Defaults to None.
        piggy_bank_id (int | None): Associated piggy bank ID. Defaults to None.
        piggy_bank_name (str | None): Associated piggy bank name. Defaults to None.
        bill_id (int | None): Associated bill ID. Defaults to None.
        bill_name (str | None): Associated bill name. Defaults to None.
        tags (str | None): Transaction tags. Defaults to None.
        notes (str | None): Additional notes. Defaults to None.
        internal_reference (str | None): Internal reference number. Defaults to None.
        external_id (str | None): External system reference ID. Defaults to None.
        external_url (str | None): External system reference URL. Defaults to None.
        sepa_cc (str | None): SEPA clearing code. Defaults to None.
        sepa_ct_op (str | None): SEPA credit transfer operation. Defaults to None.
        sepa_ct_id (str | None): SEPA credit transfer ID. Defaults to None.
        sepa_db (str | None): SEPA direct debit. Defaults to None.
        sepa_country (str | None): SEPA country code. Defaults to None.
        sepa_ep (str | None): SEPA end-to-end reference. Defaults to None.
        sepa_ci (str | None): SEPA creditor identifier. Defaults to None.
        sepa_batch_id (str | None): SEPA batch ID. Defaults to None.
        interest_date (str | None): Interest calculation date. Defaults to None.
        book_date (str | None): Book date. Defaults to None.
        process_date (str | None): Process date. Defaults to None.
        due_date (str | None): Due date. Defaults to None.
        payment_date (str | None): Payment date. Defaults to None.
        invoice_date (str | None): Invoice date. Defaults to None.
    """

    order: int = 0
    reconciled: bool = True
    source_name: str | None = None
    destination_name: str | None = None
    currency_id: int | None = None
    currency_code: str | None = None
    foreign_amount: float | None = None
    foreign_currency_id: int | None = None
    foreign_currency_code: str | None = None
    budget_id: int | None = None
    budget_name: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    source_id: int | None = None
    destination_id: int | None = None
    piggy_bank_id: int | None = None
    piggy_bank_name: str | None = None
    bill_id: int | None = None
    bill_name: str | None = None
    tags: str | None = None
    notes: str | None = None
    internal_reference: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    sepa_cc: str | None = None
    sepa_ct_op: str | None = None
    sepa_ct_id: str | None = None
    sepa_db: str | None = None
    sepa_country: str | None = None
    sepa_ep: str | None = None
    sepa_ci: str | None = None
    sepa_batch_id: str | None = None
    interest_date: str | None = None
    book_date: str | None = None
    process_date: str | None = None
    due_date: str | None = None
    payment_date: str | None = None
    invoice_date: str | None = None


@dc.dataclass
class BaseAccount:
    """Base account data class for financial accounts.

    Attributes:
        name (str): Account name.
        type (str): Account type (asset, expense).
        account_role (str | None): Specific role of the account. Defaults to None.
        iban (str | None): International Bank Account Number. Defaults to None.
        bic (str | None): Bank Identifier Code. Defaults to None.
        account_number (str | None): Account number. Defaults to None.
        currency_id (str | None): Currency ID. Defaults to None.
        currency_code (str | None): Currency code. Defaults to None.
        active (bool | None): Whether account is active. Defaults to None.
        order (int | None): Account ordering. Defaults to None.
        include_net_worth (bool | None): Whether to include in net worth calculation. Defaults to None.
        credit_card_type (str | None): Credit card type. Defaults to None.
        monthly_payment_date (str | None): Monthly payment date for credit cards. Defaults to None.
        liability_type (str | None): Liability type. Defaults to None.
        liability_direction (str | None): Liability direction. Defaults to None.
        interest (str | None): Interest rate. Defaults to None.
        interest_period (str | None): Interest period. Defaults to None.
        opening_balance (str | None): Opening balance amount. Defaults to None.
        opening_balance_date (str | None): Opening balance date. Defaults to None.
        virtual_balance (str | None): Virtual balance amount. Defaults to None.
        notes (str | None): Account notes. Defaults to None.
        latitude (float | None): Account location latitude. Defaults to None.
        longitude (float | None): Account location longitude. Defaults to None.
        zoom_level (int | None): Account location zoom level. Defaults to None.
    """

    name: str
    type: str
    account_role: str | None
    iban: str | None
    bic: str | None
    account_number: str | None
    currency_id: str | None
    currency_code: str | None
    active: bool | None
    order: int | None
    include_net_worth: bool | None
    credit_card_type: str | None
    monthly_payment_date: str | None
    liability_type: str | None
    liability_direction: str | None
    interest: str | None
    interest_period: str | None
    opening_balance: str | None
    opening_balance_date: str | None
    virtual_balance: str | None
    notes: str | None
    latitude: float | None
    longitude: float | None
    zoom_level: int | None


@dc.dataclass
class GetAccount(BaseAccount):
    """Account data class for retrieving account information from Firefly III.

    Extends BaseAccount with additional fields returned from the API including
    account metadata, balances, and currency information.

    Attributes:
        id (str): Account ID.
        type (str): Account type (asset, expense).
        current_balance (str | None): Current account balance. Defaults to None.
        created_at (str | None): Account creation timestamp. Defaults to None.
        updated_at (str | None): Last update timestamp. Defaults to None.
        object_group_id (str | None): Account group ID. Defaults to None.
        object_group_order (int | None): Account group order. Defaults to None.
        object_group_title (str | None): Account group title. Defaults to None.
        object_has_currency_setting (bool | None): Whether account has currency setting. Defaults to None.
        currency_name (str | None): Account currency name. Defaults to None.
        currency_symbol (str | None): Account currency symbol. Defaults to None.
        currency_decimal_places (int | None): Currency decimal places. Defaults to None.
        primary_currency_id (str | None): Primary currency ID. Defaults to None.
        primary_currency_name (str | None): Primary currency name. Defaults to None.
        primary_currency_code (str | None): Primary currency code. Defaults to None.
        primary_currency_symbol (str | None): Primary currency symbol. Defaults to None.
        primary_currency_decimal_places (int | None): Primary currency decimal places. Defaults to None.
        pc_current_balance (str | None): Primary currency current balance. Defaults to None.
        balance_difference (str | None): Balance difference. Defaults to None.
        pc_balance_difference (str | None): Primary currency balance difference. Defaults to None.
        pc_opening_balance (str | None): Primary currency opening balance. Defaults to None.
        pc_virtual_balance (str | None): Primary currency virtual balance. Defaults to None.
        debt_amount (str | None): Debt amount. Defaults to None.
        pc_debt_amount (str | None): Primary currency debt amount. Defaults to None.
        current_balance_date (str | None): Current balance date. Defaults to None.
        last_activity (str | None): Last activity timestamp. Defaults to None.
    """

    id: str
    type: str
    current_balance: str | None
    created_at: str | None
    updated_at: str | None
    object_group_id: str | None
    object_group_order: int | None
    object_group_title: str | None
    object_has_currency_setting: bool | None
    currency_name: str | None
    currency_symbol: str | None
    currency_decimal_places: int | None
    primary_currency_id: str | None
    primary_currency_name: str | None
    primary_currency_code: str | None
    primary_currency_symbol: str | None
    primary_currency_decimal_places: int | None
    pc_current_balance: str | None
    balance_difference: str | None
    pc_balance_difference: str | None
    pc_opening_balance: str | None
    pc_virtual_balance: str | None
    debt_amount: str | None
    pc_debt_amount: str | None
    current_balance_date: str | None
    last_activity: str | None


@dc.dataclass
class PostAccount(BaseAccount):
    """Account data class for posting accounts to Firefly III.

    Extends BaseAccount with default values optimized for API submission.
    The account type is immutable and set via subclass specialization.

    Attributes:
        type (str): Account type (immutable, set by subclass).
        iban (str | None): International Bank Account Number. Defaults to None.
        bic (str | None): Bank Identifier Code. Defaults to None.
        account_number (str | None): Account number. Defaults to None.
        opening_balance (str | None): Opening balance amount. Defaults to None.
        opening_balance_date (str | None): Opening balance date. Defaults to None.
        virtual_balance (str | None): Virtual balance amount. Defaults to None.
        currency_id (str | None): Currency ID. Defaults to None.
        currency_code (str | None): Currency code. Defaults to None.
        active (bool | None): Whether account is active. Defaults to None.
        order (int | None): Account ordering. Defaults to None.
        include_net_worth (bool | None): Whether to include in net worth calculation. Defaults to None.
        account_role (str | None): Specific role of the account. Defaults to None.
        credit_card_type (str | None): Credit card type. Defaults to None.
        monthly_payment_date (str | None): Monthly payment date for credit cards. Defaults to None.
        liability_type (str | None): Liability type. Defaults to None.
        liability_direction (str | None): Liability direction. Defaults to None.
        interest (str | None): Interest rate. Defaults to None.
        interest_period (str | None): Interest period. Defaults to None.
        notes (str | None): Account notes. Defaults to None.
        latitude (float | None): Account location latitude. Defaults to None.
        longitude (float | None): Account location longitude. Defaults to None.
        zoom_level (int | None): Account location zoom level. Defaults to None.
    """

    type: str = dc.field(init=False)
    iban: str | None = None
    bic: str | None = None
    account_number: str | None = None
    opening_balance: str | None = None
    opening_balance_date: str | None = None
    virtual_balance: str | None = None
    currency_id: str | None = None
    currency_code: str | None = None
    active: bool | None = None
    order: int | None = None
    include_net_worth: bool | None = None
    account_role: str | None = None
    credit_card_type: str | None = None
    monthly_payment_date: str | None = None
    liability_type: str | None = None
    liability_direction: str | None = None
    interest: str | None = None
    interest_period: str | None = None
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    zoom_level: int | None = None

    def __setattr__(self, key, value):
        if key == "type" and "type" in self.__dict__:
            raise AttributeError("type is read-only for PostAccount")
        super().__setattr__(key, value)


@dc.dataclass
class PostAssetAccount(PostAccount):
    """Asset account data class for posting to Firefly III.

    Specializes PostAccount for asset accounts with immutable account type.
    The type field is automatically set to "asset" and cannot be modified.

    Attributes:
        account_role (str): Specific role for asset accounts. Defaults to "defaultAsset".
    """

    account_role: str = "defaultAsset"

    def __post_init__(self):
        # Lock down immutable account type for asset accounts
        object.__setattr__(self, "type", "asset")


@dc.dataclass
class PostExpenseAccount(PostAccount):
    """Expense account data class for posting to Firefly III.

    Specializes PostAccount for expense accounts with immutable account type.
    The type field is automatically set to "expense" and cannot be modified.
    """

    def __post_init__(self):
        # Lock down immutable account type for expense accounts
        object.__setattr__(self, "type", "expense")


@dc.dataclass
class BaseRule:
    """Base rule data class for Firefly III rules.

    Attributes:
        title (str): Rule title.
        description (str | None): Rule description. Defaults to None.
        rule_group_id (int | None): Associated rule group ID. Defaults to None.
        rule_group_title (str | None): Associated rule group title. Defaults to None.
        order (int | None): Rule execution order. Defaults to None.
        trigger (str | None): Rule trigger type (e.g., 'store-journal', 'update-journal'). Defaults to None.
        active (bool | None): Whether rule is active. Defaults to None.
        strict (bool | None): Whether rule uses strict matching. Defaults to None.
        stop_processing (bool | None): Whether to stop processing rules after this one. Defaults to None.
        triggers (list | None): List of rule triggers with conditions. Defaults to None.
        actions (list | None): List of rule actions to execute. Defaults to None.
    """

    title: str
    rule_group_id: int
    description: str | None
    rule_group_title: str | None
    order: int | None
    trigger: str | None
    active: bool | None
    strict: bool | None
    stop_processing: bool | None
    triggers: list | None
    actions: list | None


@dc.dataclass
class GetRule(BaseRule):
    """Rule data class for retrieving rule information from Firefly III.

    Extends BaseRule with additional fields returned from the API including
    rule metadata and timestamps.

    Attributes:
        id (int): Rule identifier.
        created_at (str): Rule creation timestamp.
        updated_at (str): Last update timestamp.
    """

    id: int
    created_at: str
    updated_at: str


@dc.dataclass
class PostRule(BaseRule):
    """Rule data class for posting rules to Firefly III.

    Extends BaseRule with default values optimized for API submission.
    All optional fields default to None.

    Attributes:
        title (str): Rule title.
        description (str | None): Rule description. Defaults to None.
        rule_group_id (int | None): Associated rule group ID. Defaults to None.
        rule_group_title (str | None): Associated rule group title. Defaults to None.
        order (int | None): Rule execution order. Defaults to None.
        trigger (str | None): Rule trigger type. Defaults to None.
        active (bool | None): Whether rule is active. Defaults to None.
        strict (bool | None): Whether rule uses strict matching. Defaults to None.
        stop_processing (bool | None): Whether to stop processing rules after this one. Defaults to None.
        triggers (list | None): List of rule triggers with conditions. Defaults to None.
        actions (list | None): List of rule actions to execute. Defaults to None.
    """

    rule_group_id: int
    description: str | None = None
    rule_group_title: str | None = None
    order: int | None = None
    trigger: str | None = None
    active: bool | None = None
    strict: bool | None = None
    stop_processing: bool | None = None
    triggers: list | None = None
    actions: list | None = None


@dc.dataclass
class BaseRuleGroup:
    """Base rule group data class for Firefly III rule groups.

    Attributes:
        title (str): Rule group title.
        description (str | None): Rule group description. Defaults to None.
        order (int | None): Rule group execution order. Defaults to None.
        active (bool | None): Whether rule group is active. Defaults to None.
    """

    title: str
    description: str | None
    order: int | None
    active: bool | None


@dc.dataclass
class GetRuleGroup(BaseRuleGroup):
    """Rule group data class for retrieving rule group information from Firefly III.

    Extends BaseRuleGroup with additional fields returned from the API including
    rule group metadata and timestamps.

    Attributes:
        id (int): Rule group identifier.
        created_at (str): Rule group creation timestamp.
        updated_at (str): Last update timestamp.
    """

    id: int
    created_at: str
    updated_at: str


@dc.dataclass
class PostRuleGroup(BaseRuleGroup):
    """Rule group data class for posting rule groups to Firefly III.

    Extends BaseRuleGroup with default values optimized for API submission.
    All optional fields default to None.

    Attributes:
        title (str): Rule group title.
        description (str | None): Rule group description. Defaults to None.
        order (int | None): Rule group execution order. Defaults to None.
        active (bool | None): Whether rule group is active. Defaults to None.
    """

    description: str | None = None
    order: int | None = None
    active: bool | None = None