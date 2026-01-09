# Event-Driven Document Processing Platform

This repository presents a **modular, event-driven data platform** for document ingestion,
invoice processing, and analytics-ready data delivery.

The system is designed as a **production-style architecture**, while intentionally excluding
proprietary business logic and real customer data.

---

## Architecture Overview

**Core principles:**
- Event-driven processing (Kafka)
- Layered data architecture (Bronze / Silver / Gold)
- Idempotent data pipelines
- Explicit separation of responsibilities
- Scalable orchestration with Airflow

```md
[ FastAPI ]
|
v
[ Kafka Topics ]
|
v
[ Airflow DAGs ]
|
v
[ S3 Data Lake ]
```

## Event Flow

1. **Document upload**
   - FastAPI receives invoice files
   - Metadata event is emitted to Kafka

2. **Bronze layer**
   - OCR & parsing pipelines process raw documents
   - Parsed JSONL stored in S3 (Bronze)

3. **Silver layer**
   - Idempotent upsert of invoice records
   - Reference data (PPE registry) normalized
   - Data stored as Parquet

4. **Gold layer**
   - Analytical views generated (CSV)
   - Data optimized for dashboards & reporting

5. **Approval flow**
   - UI approval triggers Kafka event
   - Downstream DAGs update analytical outputs

---

## Repository Structure

```text
airflow/dags/
  bronze_*
  silver_*
  gold_*

services/
  api/               # FastAPI service
  kafka/             # Kafka consumers

architecture/
  event-flow.md

```
## Technologies Used

Python
Apache Airflow
Apache Kafka
FastAPI
AWS S3 (Data Lake)
Pandas / PyArrow
Docker / Docker Compose

