from enum import StrEnum


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_class]


class Currency(StrEnum):
    ARS = "ARS"
    USD = "USD"


class RateType(StrEnum):
    OFICIAL = "oficial"
    BLUE = "blue"
    MEP = "mep"
    TARJETA = "tarjeta"
    CRYPTO = "crypto"


class TransactionType(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class RateProvider(StrEnum):
    DOLARAPI = "dolarapi"
