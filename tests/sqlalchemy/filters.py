from requela.filters import FieldDefinition, ModelFilter, Operator
from tests.sqlalchemy.models import Account, User


class AccountFilter(ModelFilter):
    __model__ = Account

    name = FieldDefinition()
    description = FieldDefinition()
    status = FieldDefinition()
    balance = FieldDefinition()
    created_at = FieldDefinition(
        alias="events.created.at",
    )


class UserFilter(ModelFilter):
    __model__ = User

    name = FieldDefinition()
    role = FieldDefinition(
        allowed_operators=[Operator.IN, Operator.OUT],
    )
    is_active = FieldDefinition()
    birth_date = FieldDefinition(
        alias="events.born.at",
    )
    account = AccountFilter()
