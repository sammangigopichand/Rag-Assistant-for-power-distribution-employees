import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()



DATABASE_URL = os.getenv("DATABASE_URL")

# Railway supplies PostgreSQL URLs without a driver suffix. Use psycopg 3,
# which is the PostgreSQL driver installed by requirements.txt.
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    # Allow Railway's individual Postgres variables as an alternative to
    # DATABASE_URL. DATABASE_URL remains preferred when explicitly provided.
    pg_host = os.getenv("PGHOST")
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_database = os.getenv("PGDATABASE")
    if all(value is not None for value in (pg_host, pg_user, pg_password, pg_database)):
        DATABASE_URL = URL.create(
            "postgresql+psycopg",
            username=pg_user,
            password=pg_password,
            host=pg_host,
            port=int(os.getenv("PGPORT", "5432")),
            database=pg_database,
        )
    else:
        raise RuntimeError(
            "Database configuration missing: set DATABASE_URL or Railway's "
            "PGHOST, PGUSER, PGPASSWORD, and PGDATABASE variables (PGPORT is optional)."
        )


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def test_connection():

    with engine.connect() as connection:

        result = connection.execute(
            text("SELECT current_database();")
        )

        print(
            "Connected to:",
            result.scalar()
        )


if __name__ == "__main__":
    test_connection()
