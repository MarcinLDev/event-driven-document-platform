from fastapi import APIRouter, UploadFile, File, HTTPException
from datetime import datetime
import os
import boto3

from app.kafka_producer import get_producer

router = APIRouter(prefix="/invoices", tags=["Invoices"])

BUCKET = os.getenv("S3_BUCKET")
PREFIX_RAW = "01_bronze/raw_invoice/"

if not BUCKET:
    raise RuntimeError("S3_BUCKET canno't find the BUCKET, pleas check config file or AWS platform")

s3 = boto3.client("s3")

@router.post("/upload")

async def upload_invoice(file: UploadFile = File(...)):

    #walidacja
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # czytanie pliku
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")
    
    #S3 key
    s3_key = f"{PREFIX_RAW}{file.filename}"
    
    #upload do s3
    
    try:
        s3.put_object(
            Bucket=BUCKET,
            Key=s3_key,
            Body=contents,
            ContentType="application/pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"S3 upload file: {str(e)}")
    
    # event Kafka
    event = {
        "event": "invoice_uploaded",
        "invoice_name": file.filename,
        "s3_key": s3_key,
        "bucket": BUCKET,
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    
    producer = get_producer()
    producer.send("invoice_event", event)
    producer.flush()

    #response

    return{
        "status": "uploaded",
        "filename": file.filename,
        "s3_key": s3_key,
        "bucket": BUCKET,

    }

@router.get("")
def list_invoices():
    response = s3.list_objects_v2(
        Bucket=BUCKET,
        Prefix=PREFIX_RAW
    )

    items=[]
    for obj in response.get("Contents", []):
        items.append({
            "filename": obj["Key"].split("/")[-1],
            "s3_key": obj["Key"],
            "size": obj["Size"],
            "last_modified": obj["LastModified"].isoformat(),
        })

    return {"items": items}
    
