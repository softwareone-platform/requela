from collections.abc import Awaitable, Callable, Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from bson import Decimal128, ObjectId
from pymongo import AsyncMongoClient, MongoClient
from pymongo.database import Database

from requela.builders.mongo import MongoQuery
from tests.mongo.models import Level, Source, Tag
from tests.settings import MONGO_URL

DATABASE_NAME = "requela_test"

FindDocuments = Callable[[str, MongoQuery], Awaitable[list[dict[str, Any]]]]


@pytest.fixture(scope="session")
def mongo_client() -> Iterator[MongoClient]:
    """A blocking client connected to the MongoDB test server."""
    client: MongoClient = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    yield client
    client.close()


@pytest.fixture
def database(mongo_client: MongoClient) -> Iterator[Database]:
    """An empty test database, dropped at the end of the test."""
    mongo_client.drop_database(DATABASE_NAME)
    yield mongo_client[DATABASE_NAME]
    mongo_client.drop_database(DATABASE_NAME)


@pytest.fixture(params=["sync", "async"])
def find_documents(request: pytest.FixtureRequest, database: Database) -> FindDocuments:
    """Run a `MongoQuery` with the blocking or the asyncio PyMongo client."""

    async def _find(collection_name: str, query: MongoQuery) -> list[dict[str, Any]]:
        if request.param == "sync":
            cursor = database[collection_name].find(query.filter)
            if query.sort:
                cursor = cursor.sort(query.sort)
            return list(cursor)

        client: AsyncMongoClient = AsyncMongoClient(MONGO_URL)
        try:
            async_cursor = client[DATABASE_NAME][collection_name].find(query.filter)
            if query.sort:
                async_cursor = async_cursor.sort(query.sort)
            return await async_cursor.to_list()
        finally:
            await client.close()

    return _find


@pytest.fixture
def event_factory(database: Database) -> Callable[..., ObjectId]:
    """Insert an event document with overridable defaults; `missing` omits fields."""

    def _build(
        *,
        description: str,
        level: Level = Level.INFO,
        time: datetime = datetime(2024, 1, 1, tzinfo=UTC),
        ack: bool = False,
        count: int = 0,
        note: str | None = None,
        tags: list[Tag] | None = None,
        source: Source | None = None,
        missing: tuple[str, ...] = (),
    ) -> ObjectId:
        document = {
            "_id": ObjectId(),
            "organization_id": "ORG-1",
            "time": time,
            "level": level.value,
            "evt_class": "quota",
            "description": description,
            "ack": ack,
            "count": count,
            "note": note,
            "tags": [tag.model_dump() for tag in tags or []],
            "source": source.model_dump() if source else None,
        }
        for key in missing:
            del document[key]
        database["events"].insert_one(document)
        return document["_id"]

    return _build


@pytest.fixture
def sample_events(event_factory: Callable[..., ObjectId]) -> None:
    """Four events covering null and missing fields, nested lists and nested models."""
    event_factory(
        description="disk full",
        level=Level.ERROR,
        time=datetime(2024, 1, 3, tzinfo=UTC),
        count=5,
        note="check",
        tags=[
            Tag(name="env", value="prod"),
            Tag(name="team", value="ops", aliases=[{"name": "operations"}]),
        ],
        source=Source(name="aws", region="eu"),
    )
    event_factory(
        description="quota exceeded",
        level=Level.WARNING,
        time=datetime(2024, 1, 2, tzinfo=UTC),
        ack=True,
        count=2,
        note=None,
        tags=[Tag(name="env", value="dev"), Tag(name="team", value="ops")],
        source=Source(name="gcp"),
    )
    event_factory(
        description="Quota reset",
        time=datetime(2024, 1, 1, tzinfo=UTC),
        missing=("note",),
    )
    event_factory(
        description="a.b literal",
        time=datetime(2024, 1, 4, tzinfo=UTC),
        ack=True,
        count=1,
        note="x",
        tags=[Tag(name="env", value="prod"), Tag(name="team", value="dev")],
        missing=("source",),
    )


@pytest.fixture
def keeper_event_factory(database: Database) -> Callable[[datetime], ObjectId]:
    """Insert a keeper event, which stores `time` as an int Unix timestamp."""

    def _build(time: datetime) -> ObjectId:
        result = database["keeper_events"].insert_one({"time": int(time.timestamp())})
        return result.inserted_id

    return _build


@pytest.fixture
def item_factory(database: Database) -> Callable[..., ObjectId]:
    """Insert an item document, as stored for the `Item` dataclass."""

    def _build(*, name: str, price: Decimal, created: datetime) -> ObjectId:
        result = database["items"].insert_one(
            {"name": name, "price": Decimal128(price), "created": created}
        )
        return result.inserted_id

    return _build
