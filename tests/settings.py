import os

# PostgreSQL and MongoDB are mandatory for the test suite. The defaults match the
# `postgres` and `mongo` services in docker-compose.yaml (`docker compose up -d --wait`).
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/requela"
)

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
