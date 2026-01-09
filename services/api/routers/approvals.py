from fastapi import APIRouter, HTTPException
import boto3
import os
from datetime import datetime

from app.schemas.approve import ApproveInvoicesRequest
from app.kafka_producer import get_producer



router = APIRouter(
    prefix="/approvals",
    tags=["approvals"]
)

BUCKET = os.getenv("S3_BUCKET", "example-bucket")
PARSED_PREFIX = "example/path"

s3 = boto3.client("s3")

APPROVAL_TOPIC = "invoice_approval_event"

def normalize_filename(filename: str) -> str:
    return (
        filename
        .lower()
        .replace(".pdf", "")
        .replace("—", "-")
        .replace(" ", "_")
    )


def find_parsed_key_for_filename(filename: str) -> str | None:
    normalized = normalize_filename(filename)

    resp = s3.list_objects_v2(
        Bucket=BUCKET,
        Prefix=PARSED_PREFIX
    )

    for obj in resp.get("Contents", []):
        if normalized in obj["Key"]:
            return obj["Key"]

    return None


@router.post("/invoices")
def approve_invoices(payload: ApproveInvoicesRequest):
    if not payload.invoices:
        raise HTTPException(
            status_code=400,
            detail="No invoices provided"
        )

    approved = []
    missing = []

    for inv in payload.invoices:
        parsed_key = find_parsed_key_for_filename(inv.filename)

        if not parsed_key:
            missing.append(inv.filename)
        else:
            approved.append({
                "filename": inv.filename,
                "parsed_key": parsed_key
            })

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Some invoices are not parsed yet",
                "files": missing
            }
        )

    #  KAFKA EVENTY 
    producer = get_producer()

    events = []
    for inv in approved:
        event = {
            "event": "invoice_approved",
            "bucket": BUCKET,
            "parsed_key": inv["parsed_key"],
            "filename": inv["filename"],
            "approved_by": payload.approved_by,
            "approved_at": datetime.utcnow().isoformat()
        }

        producer.send(APPROVAL_TOPIC, event)
        events.append(event)

    producer.flush()

    return {
        "status": "ok",
        "approved_count": len(events),
        "approved_by": payload.approved_by,
        "events_sent": len(events),
        "invoices": approved
    }