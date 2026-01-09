from airflow import DAG
from airflow.decorators import task
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime, timedelta

from kafka import KafkaProducer
import json
import os

from pipelines.silver.silver_upsert_invoices.pipeline import upsert_invoice_from_jsonl

with DAG(
    dag_id ="silver_upsert_invoices",
    start_date=datetime(2026, 1, 5),
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=["silver", "upsert", "event-driven-invoice"]
) as dag:
    
    @task
    def read_conf(**context) -> dict:
        return context["dag_run"].conf
    
    @task(retries=2, retry_delay=timedelta(minutes=2)) 
    def run_upsert(data_conf: dict) ->dict:

        s3_client = S3Hook(aws_conn_id="aws_default").get_conn()

        return upsert_invoice_from_jsonl(
            s3_client=s3_client,
            bucket=data_conf["bucket"],
            parsed_key=data_conf["parsed_key"],
        )
    
    @task
    def emit_silver_invoices_updated(event: dict, upsert_result: dict):
        if upsert_result.get("status") =="SKIPPED":
            print("UPSERT - skipped - not emitting silver_invoices_updated")
            return {"status": "SKIPPED"}
        
        producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            value_serializer = lambda v: json.dumps(v).encode("utf-8"),
        )

        event_done = {
            "event": "silver_invoices_updated",
            "bucket": event["bucket"],
            "silver_key": upsert_result.get("silver_key"),
            "status": upsert_result.get("status", "OK"),
            "emitted_at": datetime.utcnow().isoformat(),
        }

        producer.send("invoice_event", event_done)
        producer.flush()
        producer.close()

        return event_done
    
    data_conf = read_conf()
    upsert_result = run_upsert(data_conf)
    emit_silver_invoices_updated(data_conf, upsert_result)