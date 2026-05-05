from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.db import get_db
from app.image_processing import validate_upload_image
from app.models import EventConfig, PrintJob, Printer

router = APIRouter(prefix="/api/public")


class PublicPrinterOut(BaseModel):
    id: int
    name: str
    location: str


class PublicConfigOut(BaseModel):
    printing_enabled: bool
    landing_title: str
    landing_body: str
    printer_mode: str
    allow_image_uploads: bool
    max_text_length: int
    max_image_bytes: int
    printers: list[PublicPrinterOut]


class PublicPrintRequest(BaseModel):
    text: str | None = Field(default=None, max_length=500)
    image_base64: str | None = None
    printer_ids: list[int] | None = None
    copies: int = Field(default=1, ge=1, le=1)

    @model_validator(mode="after")
    def validate_content(self) -> "PublicPrintRequest":
        if not (self.text and self.text.strip()) and not self.image_base64:
            raise ValueError("text or image is required")
        return self


class PublicPrintOut(BaseModel):
    created_jobs: int
    status: Literal["queued"] = "queued"


@router.get("/config", response_model=PublicConfigOut)
def get_public_config(db: Session = Depends(get_db)) -> PublicConfigOut:
    config = _get_config(db)
    printers: list[PublicPrinterOut] = []
    if config.printing_enabled and config.printer_mode == "select":
        printers = [
            PublicPrinterOut(id=printer.id, name=printer.name, location=printer.location)
            for printer in _selectable_printers(db)
        ]
    return PublicConfigOut(
        printing_enabled=config.printing_enabled,
        landing_title=config.landing_title,
        landing_body=config.landing_body,
        printer_mode=config.printer_mode,
        allow_image_uploads=config.allow_image_uploads,
        max_text_length=config.max_text_length,
        max_image_bytes=config.max_image_bytes,
        printers=printers,
    )


@router.post("/print", response_model=PublicPrintOut, status_code=201)
def create_public_print(payload: PublicPrintRequest, db: Session = Depends(get_db)) -> PublicPrintOut:
    config = _get_config(db)
    if not config.printing_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Printing is currently disabled")

    text = (payload.text or "").strip()
    if len(text) > config.max_text_length:
        raise HTTPException(status_code=400, detail=f"text must be {config.max_text_length} characters or fewer")

    if payload.image_base64:
        if not config.allow_image_uploads:
            raise HTTPException(status_code=400, detail="image uploads are disabled")
        try:
            validate_upload_image(payload.image_base64, config.max_image_bytes, config.max_image_pixels)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    printers = _resolve_target_printers(payload, config, db)
    for printer in printers:
        db.add(
            PrintJob(
                printer_id=printer.printer_sdp_id,
                type="composite",
                text=text,
                image_base64=payload.image_base64,
                copies=1,
                status="pending",
            )
        )
    db.commit()
    return PublicPrintOut(created_jobs=len(printers))


def _get_config(db: Session) -> EventConfig:
    config = db.get(EventConfig, 1)
    if not config:
        config = EventConfig(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _selectable_printers(db: Session) -> list[Printer]:
    return (
        db.query(Printer)
        .filter(Printer.enabled.is_(True), Printer.public_selectable.is_(True))
        .order_by(Printer.name, Printer.id)
        .all()
    )


def _resolve_target_printers(payload: PublicPrintRequest, config: EventConfig, db: Session) -> list[Printer]:
    if config.printer_mode == "all":
        printers = db.query(Printer).filter(Printer.enabled.is_(True)).order_by(Printer.name, Printer.id).all()
    elif config.printer_mode == "select":
        selected_ids = payload.printer_ids or []
        if not selected_ids:
            raise HTTPException(status_code=400, detail="printer selection is required")
        printers = (
            db.query(Printer)
            .filter(
                Printer.id.in_(selected_ids),
                Printer.enabled.is_(True),
                Printer.public_selectable.is_(True),
            )
            .all()
        )
        if len(printers) != len(set(selected_ids)):
            raise HTTPException(status_code=400, detail="one or more selected printers are unavailable")
    else:
        printer = db.get(Printer, config.default_printer_id) if config.default_printer_id else None
        if not printer or not printer.enabled:
            printer = db.query(Printer).filter(Printer.enabled.is_(True)).order_by(Printer.is_default.desc(), Printer.id).first()
        printers = [printer] if printer else []

    if not printers:
        raise HTTPException(status_code=400, detail="no enabled printers are configured")
    return printers
