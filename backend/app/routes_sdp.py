from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.epos_xml import build_text_epos_xml, wrap_sdp_print_request
from app.models import PrintJob

router = APIRouter(prefix="/sdp")

XML_MEDIA_TYPE = "text/xml; charset=utf-8"


def empty_xml_response() -> Response:
    return Response(content=b"", media_type=XML_MEDIA_TYPE, status_code=200)


@router.post("/print")
def printer_poll(
    ConnectionType: str = Form(...),
    ID: str = Form(...),
    ResponseFile: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> Response:
    if ConnectionType == "GetRequest":
        job = (
            db.query(PrintJob)
            .filter(PrintJob.printer_id == ID, PrintJob.status == "pending")
            .order_by(PrintJob.created_at, PrintJob.id)
            .first()
        )
        if not job:
            return empty_xml_response()

        job.status = "sent_to_printer"
        db.commit()

        epos_xml = build_text_epos_xml(job.text, job.copies)
        return Response(
            content=wrap_sdp_print_request(epos_xml),
            media_type=XML_MEDIA_TYPE,
            status_code=200,
        )

    if ConnectionType == "SetResponse":
        job = (
            db.query(PrintJob)
            .filter(PrintJob.printer_id == ID, PrintJob.status == "sent_to_printer")
            .order_by(desc(PrintJob.updated_at), desc(PrintJob.id))
            .first()
        )
        if job:
            response_text = ResponseFile or ""
            job.printer_response = response_text
            job.status = "error" if _looks_like_error(response_text) else "printed"
            db.commit()
        return empty_xml_response()

    return empty_xml_response()


def _looks_like_error(response_xml: str) -> bool:
    lowered = response_xml.lower()
    return any(token in lowered for token in ("error", "false", "failed", "failure"))
