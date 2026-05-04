from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.image_processing import prepare_image_for_80mm_203dpi
from app.models import PrintJob
from app.security import require_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


class JobCreate(BaseModel):
    printer_id: str = Field(min_length=1, max_length=128)
    type: Literal["text", "image"] = "text"
    text: str | None = Field(default=None)
    image_base64: str | None = Field(default=None)
    copies: int = Field(default=1, ge=1, le=10)

    @model_validator(mode="after")
    def validate_payload(self) -> "JobCreate":
        if self.type == "text" and not self.text:
            raise ValueError("text is required for text jobs")
        if self.type == "image" and not self.image_base64:
            raise ValueError("image_base64 is required for image jobs")
        return self


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


@router.post("/jobs", response_model=JobOut, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> PrintJob:
    if payload.type == "image" and payload.image_base64:
        try:
            prepare_image_for_80mm_203dpi(payload.image_base64)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = PrintJob(
        printer_id=payload.printer_id,
        type=payload.type,
        text=payload.text or "",
        image_base64=payload.image_base64,
        copies=payload.copies,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)) -> list[PrintJob]:
    return (
        db.query(PrintJob)
        .order_by(desc(PrintJob.created_at), desc(PrintJob.id))
        .limit(50)
        .all()
    )
