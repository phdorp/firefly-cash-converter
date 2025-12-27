import dataclasses as dc
import enum


class TransactionType(enum.Enum):
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"


@dc.dataclass
class BaseTransaction:
    date: str
    amount: float
    description: str
    order: int
    reconciled: bool
    type: str
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
class PostTransaction(BaseTransaction):
    type: str = ""
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

    def __post_init__(self):
        if self.type == "":
            self.type = TransactionType.WITHDRAWAL.value if self.amount < 0 else TransactionType.DEPOSIT.value
            self.amount = abs(self.amount)


@dc.dataclass
class BaseAccount:
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


@dc.dataclass
class PostAssetAccount(PostAccount):
    account_role: str = "defaultAsset"

    def __post_init__(self):
        # Lock down immutable account type for asset accounts
        object.__setattr__(self, "type", "asset")

    def __setattr__(self, key, value):
        if key == "type" and "type" in self.__dict__:
            raise AttributeError("type is read-only for PostAssetAccount")
        super().__setattr__(key, value)


@dc.dataclass
class PostExpenseAccount(PostAccount):
    def __post_init__(self):
        # Lock down immutable account type for expense accounts
        object.__setattr__(self, "type", "expense")

    def __setattr__(self, key, value):
        if key == "type" and "type" in self.__dict__:
            raise AttributeError("type is read-only for PostExpenseAccount")
        super().__setattr__(key, value)
