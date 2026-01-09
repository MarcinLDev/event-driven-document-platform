from airflow import DAG
from airflow.decorators import task

from kafka import KafkaProducer
import json
import os

from datetime import datetime, timedelta


from pipelines.bronze.ocr_single_invoice.pipeline import run_ocr_pipeline

with DAG(
    dag_id="bronze_ocr_single_invoice",
    start_date = datetime(2026, 1, 1),
    schedule_interval = None,
    catchup=False,
    max_active_runs=10,
    tags=["bronze","ocr", "event-driven-invoice"],
) as dag:
    

    @task
    def read_conf(**context):
        return context["dag_run"].conf

    @task(pool="ocr_pool", retries=2, retry_delay=timedelta(minutes=2))
    def ocr_invoice(event: dict):
        return run_ocr_pipeline(
            bucket=event['bucket'],
            pdf_key=event['s3_key'],
        )
    
    @task
    def emit_invoice_ocr_done(event: dict ,ocr_result: dict):
        if ocr_result.get("status") == "SKIPPED":
            print("OCR skipped - not emitting invoice_ocr_done")
            return {"status": "SKIPPED"}

        producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        event_done = {
            "event": "invoice_ocr_done",
            "bucket": event["bucket"],
            "s3_key": event["s3_key"],
            "ocr_key": ocr_result.get("ocr_key"),
            "pdf_name": event["s3_key"].split("/")[-1],
            "status": ocr_result.get("status", "OK"),
        }
        producer.send("invoice_event", event_done)
        producer.flush()
        producer.close()

        return event_done

    event = read_conf()
    ocr_result = ocr_invoice(event)
    emit_invoice_ocr_done(event, ocr_result)
    


