from airflow import DAG
from airflow.decorators import task
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime

from pipelines.silver.reference_ppe.pipeline import build_reference_ppe

BUCKET = "example_bucket"

EXCEL_KEY = "example/path"
MISSING_KEY = "example/path"
OUTPUT_KEY = "example/path"

with DAG(
    dag_id="silver_reference_ppe",
    start_date=datetime(2026, 1, 1),
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=["silver", "reference", "ppe"]
) as dag:

    @task
    def run_pipeline():
        s3 = S3Hook(aws_conn_id="aws_default").get_conn()
        return build_reference_ppe(
            s3=s3,
            bucket=BUCKET,
            excel_key=EXCEL_KEY,
            missing_key=MISSING_KEY,
            output_key=OUTPUT_KEY
        )

    run_pipeline()
