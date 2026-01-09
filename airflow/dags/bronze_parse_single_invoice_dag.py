from airflow import DAG
from airflow.decorators import task

from kafka import KafkaProducer
import json
import os

from datetime import datetime

from pipelines.bronze.parse_single_invoice.pipeline import run_invoice_parser


with DAG(
    dag_id="bronze_parse_single_invoice",
    start_date=datetime(2026, 1, 1),
    schedule_interval=None,
    catchup=False,
    max_active_runs=10,
    tags=["bronze", "parse", "event-driven-invoice"],
) as dag:

    @task
    def read_conf(**context) -> dict:
        """
        Oczekiwany conf:
        {
          "bucket": "...",
          "ocr_key": "...",
          "pdf_name": "..."
        }
        """
        return context["dag_run"].conf

    @task
    def parse_invoice(event: dict) -> dict:
        return run_invoice_parser(
            bucket=event["bucket"],
            ocr_key=event["ocr_key"],
            pdf_name=event["pdf_name"],
        )
    
    @task
    def emit_invoice_parse_done(event: dict, parse_result: dict):
        if parse_result.get("status") == "SKIPPED":
            print("PARSED skipped - not emitting invoice_parse_done")
            return {"status": "SKIPPED"}
        
        producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            value_serializer = lambda v: json.dumps(v).encode("utf-8"),
        )

        event_done = {
            "event": "invoice_parsed_done",
            "bucket": event["bucket"],
            "parsed_key": parse_result.get("parsed_key"),
            "pdf_name": event["pdf_name"],
            "status": parse_result.get("status","OK"),
            "emitted_at": datetime.utcnow().isoformat(),
        }

        producer.send("invoice_event", event_done)
        producer.flush()
        producer.close()

        return event_done

    event = read_conf()
    parse_result = parse_invoice(event)
    emit_invoice_parse_done(event, parse_result)
