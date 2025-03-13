from requela.dataclasses import Operator
from requela.rules import FieldRule, ModelRQLRules, RelationshipRule
from tests.sqlalchemy.models import Account, Actor, User


class NameMixin:
    name = FieldRule()


class ActorRules(NameMixin, ModelRQLRules):
    __model__ = Actor




class AccountRules(ModelRQLRules, NameMixin):
    __model__ = Account

    description = FieldRule()
    status = FieldRule()
    balance = FieldRule()
    created_at = FieldRule(
        alias="events.created.at",
    )
    created_by = RelationshipRule(
        alias="events.created.by",
        rules=ActorRules(),
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
