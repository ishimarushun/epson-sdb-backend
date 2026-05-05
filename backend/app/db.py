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
    _seed_defaults()


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


def _seed_defaults() -> None:
    from app.auth import hash_password
    from app.models import AdminUser, EventConfig, Printer

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "change-me-admin")
    default_printer_sdp_id = os.getenv("DEFAULT_PRINTER_SDP_ID", "printer_001")

    with SessionLocal() as db:
        if not db.query(AdminUser).filter(AdminUser.username == admin_username).first():
            db.add(AdminUser(username=admin_username, password_hash=hash_password(admin_password)))

        default_printer = db.query(Printer).filter(Printer.printer_sdp_id == default_printer_sdp_id).first()
        if not default_printer:
            default_printer = Printer(
                name=os.getenv("DEFAULT_PRINTER_NAME", "Main printer"),
                printer_sdp_id=default_printer_sdp_id,
                location="",
                enabled=True,
                public_selectable=True,
                is_default=True,
            )
            db.add(default_printer)
            db.flush()

        config = db.get(EventConfig, 1)
        if not config:
            db.add(EventConfig(id=1, default_printer_id=default_printer.id))
        elif config.default_printer_id is None:
            config.default_printer_id = default_printer.id

        db.commit()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
