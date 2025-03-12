from requela.rules import FieldRule, ModelRQLRules, Operator, RelationshipRule
from tests.django.models import Account, User


class AccountRules(ModelRQLRules):
    __model__ = Account

    name = FieldRule()
    description = FieldRule()
    status = FieldRule()
    balance = FieldRule()
    created_at = FieldRule(
        alias="events.created.at",
    )


class UserRules(ModelRQLRules):
    __model__ = User

    name = FieldRule()
    role = FieldRule(
        allowed_operators=[Operator.IN, Operator.OUT],
    )
    is_active = FieldRule()
    birth_date = FieldRule(
        alias="events.born.at",
    )
    account = RelationshipRule(
        alias="account",
        rules=AccountRules(),
    )
