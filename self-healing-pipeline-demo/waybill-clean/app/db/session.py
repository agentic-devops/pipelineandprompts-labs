from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://waybill:waybill@localhost:5432/waybill"
)

_connect_args = {"connect_timeout": 5} if DATABASE_URL.startswith("postgresql") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # validates connection before use
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Used by the health endpoint to verify DB reachability."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
