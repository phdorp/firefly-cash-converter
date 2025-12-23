import dataclasses as dc


@dc.dataclass
class Transaction:
    Description: str
    Date: str
    Deposit: float
    SourceAccountName: str = ""  # Account funds come from (for withdrawals)
    DestinationAccountName: str = ""  # Account funds go to (for deposits)


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
    type: str = dc.field(init=False)
    account_role: str = "defaultAsset"

    def __post_init__(self):
        # Lock down immutable account type for asset accounts
        object.__setattr__(self, "type", "asset")

    def __setattr__(self, key, value):
        if key == "type" and "type" in self.__dict__:
            raise AttributeError("type is read-only for PostAssetAccount")
        super().__setattr__(key, value)

