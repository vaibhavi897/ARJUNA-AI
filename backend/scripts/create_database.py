"""Create the PostgreSQL database named in DATABASE_URL, if it does not exist.

    python -m scripts.create_database

Connects to the server's maintenance database using the same credentials, so
no separate admin configuration is needed. Credentials are never printed.
"""

from __future__ import annotations

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, ProgrammingError


def main() -> int:
    from app.core.config import settings

    url = make_url(settings.DATABASE_URL)
    target = url.database
    if not target:
        print("DATABASE_URL does not name a database.")
        return 2

    print(f"Server : {url.host}:{url.port or 5432}")
    print(f"User   : {url.username}")
    print(f"Target : {target}")

    admin_url = url.set(database="postgres")
    try:
        engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": target},
            ).scalar()
            if exists:
                print(f"Database '{target}' already exists - nothing to do.")
            else:
                # Identifier cannot be bound as a parameter; it comes from our
                # own .env, and is quoted to stay safe with unusual names.
                connection.execute(text(f'CREATE DATABASE "{target}"'))
                print(f"Created database '{target}'.")
    except OperationalError as exc:
        print("Could not connect to PostgreSQL.")
        print(f"  {exc.__class__.__name__}: check host, port, user and password.")
        return 1
    except ProgrammingError as exc:
        print(f"PostgreSQL rejected the request: {exc.__class__.__name__}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
