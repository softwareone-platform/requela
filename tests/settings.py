import os

# PostgreSQL is mandatory for the test suite. The default matches the `postgres` service
# in docker-compose.yaml started with `docker compose up -d postgres`.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/requela"
)
