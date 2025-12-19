import dataclasses as dc


@dc.dataclass
class Transaction:
    Description: str
    Date: str
    Deposit: float
    SourceAccountName: str = ""  # Account funds come from (for withdrawals)
    DestinationAccountName: str = ""  # Account funds go to (for deposits)
