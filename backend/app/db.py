import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sdp.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "print_jobs" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("print_jobs")}
    with engine.begin() as connection:
        if "image_base64" not in columns:
            connection.exec_driver_sql("ALTER TABLE print_jobs ADD COLUMN image_base64 TEXT")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
