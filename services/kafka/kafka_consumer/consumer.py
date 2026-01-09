from kafka import KafkaConsumer
import json
import os
import requests

print("Kafka consumer started, waiting for events...")

consumer = KafkaConsumer(
    "invoice_event",
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
    group_id="airflow-trigger",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda v: v.decode("utf-8"),
)

for msg in consumer:
    raw_value = msg.value
    print("Raw message:", raw_value)

    try:
        event = json.loads(raw_value)
    except json.JSONDecodeError:
        print(" Skipping non-JSON message")
        continue

    print("Received event:", event)

    if event.get("event") == "invoice_uploaded":
        response = requests.post(
            f"{os.environ['AIRFLOW_API']}/api/v1/dags/bronze_ocr_single_invoice/dagRuns",
            auth=(os.environ["AIRFLOW_USER"], os.environ["AIRFLOW_PASSWORD"]),
            json={
                "conf": {
                    "bucket": event["bucket"],
                    "s3_key": event["s3_key"],
                }
            },
        )

        print("Triggered Airflow:", response.status_code, response.text)


    elif event.get("event") =="invoice_ocr_done":
        response = requests.post(
            f"{os.environ['AIRFLOW_API']}/api/v1/dags/bronze_parse_single_invoice/dagRuns",
            auth=(os.environ["AIRFLOW_USER"], os.environ["AIRFLOW_PASSWORD"]),
            json={
                "conf": {
                    "bucket": event["bucket"],
                    "ocr_key": event["ocr_key"],
                    "pdf_name": event["pdf_name"],
                }
            },
        )
        print("Triggered bronze parse DAG:", response.status_code, response.text)
    
    else:
        print("Unknow event type", event.get("event"))