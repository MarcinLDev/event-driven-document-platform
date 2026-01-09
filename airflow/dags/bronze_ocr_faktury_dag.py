"""
DAG: bronze_ocr_faktury

Cel:
- Pobiera listę PDF-ów z S3 (RAW / bronze)
- Dla każdego PDF uruchamia OCR
- zapisuje wynik OCR jako TXT do S3 (bornze / ocr)

Używa: 
- TaskFlow API (@task)
- Dynamic Task Mapping (.expand)
- Poola Airflow do limitu OCR (CPU-heavy)
"""

from datetime import datetime, timedelta
from typing import List

from airflow import DAG
from airflow.decorators import task
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

# Twoje pipeline'y (czysty Python, bez Airflow)
from pipelines.bronze.ocr_faktury.process import process_single_pdf
from pipelines.bronze.ocr_faktury.s3_utils import list_pdf_keys


# =========================
# KONFIGURACJA
# =========================

BUCKET = "bucket_example"

PREFIX_RAW = "example/path"
PREFIX_OCR = "example/path"


# =========================
# DAG
# =========================

with DAG(
    dag_id="bronze_ocr_faktury",
    start_date=datetime(2025, 12, 27),
    schedule_interval=None,   # uruchamiany ręcznie
    catchup=False,
    max_active_runs=1,
    max_active_tasks=2,
    default_args={
        "retries":2,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["bronze", "ocr", "s3"],
) as dag:

    # -------------------------------------------------
    # TASK 1: lista PDF-ów z S3
    # -------------------------------------------------
    @task
    def list_pdfs() -> List[str]:
        """
        Zwraca listę kluczy PDF z S3.
        Airflow pobiera credentials z aws_default.
        """
        s3 = S3Hook(aws_conn_id="aws_default").get_conn()
        return list_pdf_keys(s3, BUCKET, PREFIX_RAW)

    # -------------------------------------------------
    # TASK 2: OCR jednej faktury
    # -------------------------------------------------
    @task(pool="ocr_pool", retries=2, retry_delay=timedelta(minutes=2))
    def process_pdf(pdf_key: str):
        """
        Przetwarza JEDEN PDF:
        - pobiera z S3
        - robi OCR
        - zapisuje TXT do S3
        """
        s3 = S3Hook(aws_conn_id="aws_default").get_conn()

        return process_single_pdf(
            s3_client=s3,
            bucket=BUCKET,
            prefix_ocr=PREFIX_OCR,
            pdf_key=pdf_key,
        )

    # -------------------------------------------------
    # DYNAMIC TASK MAPPING (fan-out)
    # -------------------------------------------------
    process_pdf.expand(
        pdf_key=list_pdfs()
    )
