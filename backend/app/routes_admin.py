from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth import SESSION_COOKIE_NAME, clear_admin_session, create_admin_session, require_admin_user, verify_password
from app.db import get_db
from app.models import AdminUser, EventConfig, PrintJob, Printer

router = APIRouter(prefix="/api")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class AdminMeOut(BaseModel):
    username: str


class PrinterIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    printer_sdp_id: str = Field(min_length=1, max_length=128)
    location: str = Field(default="", max_length=256)
    enabled: bool = True
    public_selectable: bool = True
    is_default: bool = False


class PrinterOut(PrinterIn):
    id: int

    model_config = {"from_attributes": True}


class ConfigIn(BaseModel):
    printing_enabled: bool
    landing_title: str = Field(min_length=1, max_length=200)
    landing_body: str = Field(min_length=1, max_length=2000)
    printer_mode: Literal["single", "select", "all"]
    default_printer_id: int | None = None
    allow_image_uploads: bool = True
    max_text_length: int = Field(default=500, ge=1, le=500)
    max_image_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=10 * 1024 * 1024)
    max_image_pixels: int = Field(default=20_000_000, ge=1, le=20_000_000)


class ConfigOut(ConfigIn):
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: int
    printer_id: str
    type: str
    text: str
    image_base64: str | None
    copies: int
    status: str
    printer_response: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.post("/auth/login", response_model=AdminMeOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AdminMeOut:
    user = db.query(AdminUser).filter(AdminUser.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    create_admin_session(user, response, db)
    return AdminMeOut(username=user.username)


@router.post("/auth/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    clear_admin_session(response, session_token, db)
    return {"status": "ok"}


@router.get("/auth/me", response_model=AdminMeOut)
def me(user: AdminUser = Depends(require_admin_user)) -> AdminMeOut:
    return AdminMeOut(username=user.username)


@router.get("/admin/config", response_model=ConfigOut)
def get_config(_: AdminUser = Depends(require_admin_user), db: Session = Depends(get_db)) -> EventConfig:
    return _get_config(db)


@router.put("/admin/config", response_model=ConfigOut)
def update_config(
    payload: ConfigIn,
    _: AdminUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> EventConfig:
    if payload.default_printer_id is not None and not db.get(Printer, payload.default_printer_id):
        raise HTTPException(status_code=400, detail="default printer does not exist")
    config = _get_config(db)
    for key, value in payload.model_dump().items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config


@router.get("/admin/printers", response_model=list[PrinterOut])
def list_printers(_: AdminUser = Depends(require_admin_user), db: Session = Depends(get_db)) -> list[Printer]:
    return db.query(Printer).order_by(Printer.name, Printer.id).all()


@router.post("/admin/printers", response_model=PrinterOut, status_code=201)
def create_printer(
    payload: PrinterIn,
    _: AdminUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> Printer:
    printer = Printer(**payload.model_dump())
    db.add(printer)
    db.flush()
    if printer.is_default:
        _clear_other_defaults(db, printer.id)
        config = _get_config(db)
        config.default_printer_id = printer.id
    db.commit()
    db.refresh(printer)
    return printer


@router.put("/admin/printers/{printer_id}", response_model=PrinterOut)
def update_printer(
    printer_id: int,
    payload: PrinterIn,
    _: AdminUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> Printer:
    printer = db.get(Printer, printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="printer not found")
    for key, value in payload.model_dump().items():
        setattr(printer, key, value)
    if printer.is_default:
        _clear_other_defaults(db, printer.id)
        config = _get_config(db)
        config.default_printer_id = printer.id
    db.commit()
    db.refresh(printer)
    return printer


@router.get("/admin/jobs", response_model=list[JobOut])
def list_admin_jobs(_: AdminUser = Depends(require_admin_user), db: Session = Depends(get_db)) -> list[PrintJob]:
    return (
        db.query(PrintJob)
        .order_by(desc(PrintJob.created_at), desc(PrintJob.id))
        .limit(100)
        .all()
    )


def _get_config(db: Session) -> EventConfig:
    config = db.get(EventConfig, 1)
    if not config:
        config = EventConfig(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _clear_other_defaults(db: Session, keep_id: int) -> None:
    for printer in db.query(Printer).filter(Printer.id != keep_id, Printer.is_default.is_(True)).all():
        printer.is_default = False
