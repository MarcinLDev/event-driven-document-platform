from fastapi import APIRouter, HTTPException, UploadFile, File
import boto3
import os
import json

router = APIRouter(prefix="/invoices", tags=["invoices"])

# === KONFIGURACJA ===
BUCKET = os.getenv("S3_BUCKET", "example/bucket")

RAW_PREFIX = "example/path"
OCR_PREFIX = "example/path"
PARSED_PREFIX = "example/path"

s3 = boto3.client("s3")



@router.post("/upload")
def upload_invoice(file: UploadFile = File(...)):
    """
    Uploaduje PDF do S3 (raw_faktury)
    oraz inicjuje dalsze przetwarzanie (Kafka / Airflow).
    """
    try:
        key = RAW_PREFIX + file.filename

        s3.upload_fileobj(
            file.file,
            BUCKET,
            key,
            ExtraArgs={"ContentType": "application/pdf"}
        )

        return {
            "status": "uploaded",
            "filename": file.filename,
            "s3_key": key
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/parsed/{filename}")
def get_parsed_invoice(filename: str):
    """
    Zwraca sparsowaną fakturę JSON
    (jeśli jeszcze nie gotowa: 404)
    """
    normalized = (
        filename
        .lower()
        .replace(".pdf", "")
        .replace("—", "-")
        .replace(" ", "_")
    )

    try:
        resp = s3.list_objects_v2(
            Bucket=BUCKET,
            Prefix=PARSED_PREFIX
        )

        for obj in resp.get("Contents", []):
            if normalized in obj["Key"]:
                body = s3.get_object(
                    Bucket=BUCKET,
                    Key=obj["Key"]
                )["Body"].read().decode("utf-8").strip()

                return json.loads(body)

        raise HTTPException(status_code=404, detail="Parsed invoice not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/status/{filename}")
def get_invoice_status(filename: str):
    """
    Sprawdza czy faktura jest już przetworzona.
    """
    normalized = (
        filename
        .lower()
        .replace(".pdf", "")
        .replace("—", "-")
        .replace(" ", "_")
    )

    try:
        resp = s3.list_objects_v2(
            Bucket=BUCKET,
            Prefix=PARSED_PREFIX
        )

        for obj in resp.get("Contents", []):
            if normalized in obj["Key"]:
                return {
                    "filename": filename,
                    "status": "ready"
                }

        return {
            "filename": filename,
            "status": "processing"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{filename}")
def delete_invoice(filename: str):
    """
    Usuwa WSZYSTKIE artefakty faktury:
    - raw PDF
    - OCR
    - parsed JSON
    """
    deleted = []

    normalized = (
        filename
        .lower()
        .replace(".pdf", "")
        .replace("—", "-")
        .replace(" ", "_")
    )

    try:
        # --- RAW PDF ---
        raw_key = RAW_PREFIX + filename
        try:
            s3.head_object(Bucket=BUCKET, Key=raw_key)
            s3.delete_object(Bucket=BUCKET, Key=raw_key)
            deleted.append("raw_pdf")
        except:
            pass

        # --- OCR FILES ---
        ocr_resp = s3.list_objects_v2(
            Bucket=BUCKET,
            Prefix=OCR_PREFIX
        )

        for obj in ocr_resp.get("Contents", []):
            if normalized in obj["Key"]:
                s3.delete_object(Bucket=BUCKET, Key=obj["Key"])
                deleted.append("ocr")

        # --- PARSED JSON ---
        parsed_resp = s3.list_objects_v2(
            Bucket=BUCKET,
            Prefix=PARSED_PREFIX
        )

        for obj in parsed_resp.get("Contents", []):
            if normalized in obj["Key"]:
                s3.delete_object(Bucket=BUCKET, Key=obj["Key"])
                deleted.append("parsed")

        return {
            "status": "ok",
            "filename": filename,
            "deleted": list(set(deleted))
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
