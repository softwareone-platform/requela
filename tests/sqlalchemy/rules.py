from requela.dataclasses import Operator
from requela.rules import FieldRule, ModelRQLRules, RelationshipRule
from tests.sqlalchemy.models import Account, Actor, Tenant, User


class NameMixin:
    name = FieldRule()


class ActorRules(NameMixin, ModelRQLRules):
    __model__ = Actor


class TimestampMixin:
    created_at = FieldRule(
        alias="events.created.at",
    )


class AuditableMixin(TimestampMixin):
    created_by = RelationshipRule(
        alias="events.created.by",
        rules=ActorRules(),
    )


class TenantRules(ModelRQLRules):
    __model__ = Tenant

    name = FieldRule()


class AccountRules(ModelRQLRules, AuditableMixin, NameMixin):
    __model__ = Account

    description = FieldRule()
    status = FieldRule()
    balance = FieldRule()
    datasource_id = FieldRule()
    tenant = RelationshipRule(rules=TenantRules())


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
        rules=AccountRules(),
    )
    status = FieldRule(
        source="account.status",
    )
    is_inactive = FieldRule(allowed_operators=[Operator.EQ, Operator.NE])

    company_email = FieldRule()


class UserNameRules(ModelRQLRules):
    __model__ = User

    name = FieldRule()
    age = FieldRule()


class AccountWithAliasedUsersRules(ModelRQLRules):
    __model__ = Account

    name = FieldRule()
    users = RelationshipRule(alias="members", rules=UserNameRules())


class AccountWithPrefixedRelationsRules(ModelRQLRules):
    """Relation aliases where one ('tenant') is a prefix of the other ('tenants')."""

    __model__ = Account

    tenant = RelationshipRule(rules=TenantRules())
    users = RelationshipRule(alias="tenants", rules=UserNameRules())


class AccountWithDuplicatedRelationAliasRules(ModelRQLRules):
    """Misconfigured rules: two relationships share the alias 'owners'."""

    __model__ = Account

    tenant = RelationshipRule(alias="owners", rules=TenantRules())
    users = RelationshipRule(alias="owners", rules=UserNameRules())


class UserWithConvertersRules(ModelRQLRules):
    __model__ = User

    name = FieldRule(value_converter=str.upper)
    age = FieldRule(value_converter=lambda value: value * 12)
    is_active = FieldRule(value_converter=lambda value: not value)


class UserWithFlagStoredAsIntRules(ModelRQLRules):
    __model__ = User

    is_active = FieldRule(value_converter=int)
