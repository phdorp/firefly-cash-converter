import dataclasses as dc


@dc.dataclass
class Transaction:
    Description: str
    Date: str
    Deposit: float
    SourceAccount: str = ""  # Account funds come from (for withdrawals)
    DestinationAccount: str = ""  # Account funds go to (for deposits)
