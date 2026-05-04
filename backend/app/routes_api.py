from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PrintJob
from app.security import require_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


class JobCreate(BaseModel):
    printer_id: str = Field(min_length=1, max_length=128)
    type: Literal["text"] = "text"
    text: str = Field(min_length=1)
    copies: int = Field(default=1, ge=1, le=10)


class JobOut(BaseModel):
    id: int
    printer_id: str
    type: str
    text: str
    copies: int
    status: str
    printer_response: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.post("/jobs", response_model=JobOut, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> PrintJob:
    job = PrintJob(
        printer_id=payload.printer_id,
        type=payload.type,
        text=payload.text,
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
