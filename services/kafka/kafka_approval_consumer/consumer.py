from kafka import KafkaConsumer
import json
import os
import requests

AIRFLOW_API = os.environ["AIRFLOW_API"]
AIRFLOW_USER = os.environ["AIRFLOW_USER"]
AIRFLOW_PASSWORD = os.environ["AIRFLOW_PASSWORD"]

print("Kafka EVENT consumer started (APPROVAL + SILVER = GOLD)")

consumer = KafkaConsumer(
    "invoice_approval_event",  
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
    group_id="airflow-event-trigger",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

for msg in consumer:
    event = msg.value
    event_type = event.get("event")

    print("EVENT RECEIVED:", event)

    if event_type == "invoice_approved":
        print("Triggering SILVER DAG")

        try:
            r = requests.post(
                f"{AIRFLOW_API}/api/v1/dags/silver_upsert_invoices/dagRuns",
                auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
                json={
                    "conf": {
                        "bucket": event["bucket"],
                        "parsed_key": event["parsed_key"],
                        "filename": event["filename"],
                        "approved_by": event["approved_by"],
                        "approved_at": event["approved_at"],
                    }
                },
                timeout=5,
            )

            print("SILVER triggered:", r.status_code)

        except Exception as e:
            print("ERROR triggering SILVER DAG:", e)

    elif event_type == "silver_invoices_updated":
        if event.get("status") != "OK":
            print("⏭Silver status not OK — skipping GOLD")
            continue

        print("Triggering GOLD DAG")

        try:
            r = requests.post(
                f"{AIRFLOW_API}/api/v1/dags/gold_przywidz_invoice_views/dagRuns",
                auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
                json={
                    "conf": {
                        "bucket": event["bucket"],
                        "silver_key": event["silver_key"],
                        "emitted_at": event["emitted_at"],
                    }
                },
                timeout=5,
            )

            print("GOLD triggered:", r.status_code)

        except Exception as e:
            print("ERROR triggering GOLD DAG:", e)

    else:
        print("Unknown event type — ignored:", event_type)
