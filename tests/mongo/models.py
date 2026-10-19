from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import IntEnum, StrEnum
from typing import Annotated, Any
from uuid import UUID

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class Level(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Severity(IntEnum):
    LOW = 1
    HIGH = 2


class Alias(BaseModel):
    name: str


class Tag(BaseModel):
    name: str
    value: str
    aliases: list[Alias] = []


class Source(BaseModel):
    name: str
    region: str | None = None


class Event(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: ObjectId = Field(alias="_id")
    organization_id: str
    time: datetime
    level: Level
    severity: Severity = Severity.LOW
    evt_class: str
    description: str
    ack: bool = False
    count: Annotated[int, Field(ge=0)] = 0
    cost: float = 0.0
    note: str | None = None
    day: date | None = None
    tags: list[Tag] = []
    source: Source | None = None
    labels: list[str] = []
    payload: dict[str, Any] = {}
    extra: Any = None
    code: int | str = 0
    reference: UUID | None = None


class KeeperEvent(BaseModel):
    """keeper stores `time` as an int Unix timestamp; users filter with datetimes."""

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: ObjectId = Field(alias="_id")
    time: datetime


class CamelEvent(BaseModel):
    """Stored keys differ from attribute names through aliases."""

    model_config = ConfigDict(populate_by_name=True)

    event_class: str = Field(alias="eventClass")
    created_by: str = Field(alias="createdBy", serialization_alias="author")


@dataclass
class Item:
    id: ObjectId = field(metadata={"mongo_key": "_id"})
    name: str
    price: Decimal
    created: date
