from datetime import datetime

from requela.builders.mongo import MongoQueryBuilder
from requela.dataclasses import Operator
from requela.rules import FieldRule, ModelRQLRules, RelationshipRule
from tests.mongo.models import Alias, Event, Item, KeeperEvent, Source, Tag


def to_timestamp(value: datetime) -> int:
    return int(value.timestamp())


class MongoRules(ModelRQLRules):
    __abstract__ = True
    __builder__ = MongoQueryBuilder


class AliasRules(MongoRules):
    __model__ = Alias

    name = FieldRule()


class TagRules(MongoRules):
    __model__ = Tag

    name = FieldRule(alias="key")
    value = FieldRule()
    aliases = RelationshipRule(rules=AliasRules())


class SourceRules(MongoRules):
    __model__ = Source

    name = FieldRule()
    region = FieldRule()


class EventRules(MongoRules):
    __model__ = Event

    id = FieldRule()
    time = FieldRule()
    level = FieldRule()
    severity = FieldRule()
    type = FieldRule(source="evt_class")
    description = FieldRule(allowed_operators={Operator.EQ, Operator.LIKE, Operator.ILIKE})
    ack = FieldRule(allow_ordering=False)
    count = FieldRule()
    note = FieldRule()
    day = FieldRule()
    tags = RelationshipRule(rules=TagRules())
    source = RelationshipRule(alias="origin", rules=SourceRules())


class KeeperEventRules(MongoRules):
    __model__ = KeeperEvent

    id = FieldRule()
    time = FieldRule(value_converter=to_timestamp)


class ItemRules(MongoRules):
    __model__ = Item

    id = FieldRule()
    name = FieldRule()
    price = FieldRule()
    created = FieldRule()


class EventWithUnsupportedFieldsRules(MongoRules):
    """Rules on fields whose type can't be filtered: they fail when instantiated."""

    __model__ = Event

    labels = FieldRule()
    payload = FieldRule()
    extra = FieldRule()
    code = FieldRule()
    reference = FieldRule()
    payload_key = FieldRule(source="payload.key")


def reject(value: object) -> object:
    raise ValueError(f"Rejected value {value!r}")


class EventWithConvertersRules(MongoRules):
    __model__ = Event

    count = FieldRule(value_converter=str)
    description = FieldRule(value_converter=str.upper)
    note = FieldRule(value_converter=reject)
