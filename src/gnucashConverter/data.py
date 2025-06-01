import dataclasses as dc


@dc.dataclass
class Transaction:
    Description: str
    Date: str
    Deposit: float
