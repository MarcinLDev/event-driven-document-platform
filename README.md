# Event-Driven Document Processing Platform

This repository presents a **modular, event-driven data platform** for document ingestion,
invoice processing, and analytics-ready data delivery.

The system is designed as a **production-style architecture**, while intentionally excluding
proprietary business logic and real customer data.

---

## Architecture Overview
**The platform follows a decoupled, event-driven architecture combined with a Medallion Data Lake design (Bronze / Silver / Gold).**

**Core principles:**
- Event-driven processing (Kafka)
- Clear separation of responsibilities
- Layered data architecture (Bronze / Silver / Gold)
- Idempotent and replayable pipelines
- Scalable orchestration with Apache Airflow

```md
[DASH (UI)]
   |
   | 1. Upload PDF
   |    (POST /invoices/upload)
   v
[FASTAPI]
   |
   | 2. Store raw PDF file
   |    S3 → BRONZE layer
   |    01_bronze/raw_faktury/{filename}.pdf
   |
   | 3. Emit event
   v
[KAFKA]
   topic: invoice_uploaded
   payload:
   {
     filename,
     s3_key,
     layer: "bronze"
   }
   |
   v
[AIRFLOW DAG #1 — OCR]
   |
   | 4. Fetch PDF from S3 (bronze/raw)
   | 5. Run OCR (raw text extraction)
   | 6. Store OCR output
   |    S3 → BRONZE layer
   |    01_bronze/ocr_faktury/{filename}.txt
   |
   | 7. Emit event
   v
[KAFKA]
   topic: invoice_ocr_completed
   payload:
   {
     filename,
     ocr_key,
     layer: "bronze"
   }
   |
   v
[AIRFLOW DAG #2 — PARSER]
   |
   | 8. Fetch OCR text from S3 (bronze/ocr)
   | 9. Parse structured data from text
   |    (invoice number, PPE, amounts, period, corrections)
   | 10. Store parsed invoice
   |     S3 → BRONZE layer
   |     01_bronze/parsed_invoices/{filename}.json
   |
   | 11. Emit event
   v
[KAFKA]
   topic: invoice_parsed
   payload:
   {
     filename,
     parsed_key,
     layer: "bronze"
   }
   |
   v
[FASTAPI]
   |
   | 12. Status check (no Kafka subscription)
   |     GET /invoices/status/{filename}
   |     └── checks whether
   |         BRONZE/parsed_invoices/{filename}.json exists
   |
   | 13. Read model
   |     GET /invoices/parsed/{filename}
   |     └── reads JSON directly from S3
   |
   v
[DASH (UI)]
   |
   | 14. Polling every N seconds
   |     → status = processing / ready
   |
   | 15. When ready:
   |     - UI processing lock is removed
   |     - table is populated with parsed data
   |     - gross amount = net amount * 1.23 (UI-side logic)
   |
   v
[END USER]

```

## Detailed Event Flow

1. Document ingestion (UI → API)

- User uploads a PDF invoice via Dash UI
- Dash sends the file to FastAPI
- FastAPI:
  - stores the raw PDF in S3 (Bronze layer)
  - emits a invoice_uploaded event to Kafka

2. Bronze layer — raw & parsed data

- Airflow DAG: bronze_ocr
  - Triggered by Kafka event
  - Performs OCR on raw PDF
  - Stores OCR output in S3 (Bronze)
- Airflow DAG: bronze_parse_invoice
  - Triggered after OCR completion
  - Parses OCR text into structured JSON
  - Stores parsed invoice JSON in S3 (Bronze)
Bronze characteristics:
- Immutable data
- Raw + parsed representations
- One file per processing step
- No business transformations

3. Silver layer — cleaned & normalized data

- Airflow DAG: silver_invoices
  - Reads parsed invoices from Bronze
  - Validates schema and data types
  - Normalizes units, dates, and identifiers
  - Generates deterministic business keys
  - Performs idempotent upserts

Data is stored in S3 (Silver layer) as:
- Parquet files
- Partitioned by time or domain

Silver characteristics:
- One row = one invoice
- Clean, typed, deduplicated data
- Stable schema ready for analytics

4. Gold layer — analytical datasets

- Airflow DAG: gold_invoice_metrics
  - Reads Silver data
  - Builds aggregated, business-oriented datasets:
    - monthly energy costs
    - consumption per PPE
    - correction vs original invoices
  - Stores results in S3 (Gold layer)

Gold characteristics:
- Aggregated and denormalized
- Optimized for BI tools
- No raw or operational data

5. Status & feedback loop (API → UI)
- FastAPI exposes invoice status endpoints
- Dash UI periodically polls processing status
- UI updates automatically when processing is complete
- Processing lock prevents concurrent user actions

---

## Repository Structure

```text
airflow/
  dags/
    bronze_ocr.py
    bronze_parse_invoice.py
    silver_invoices.py
    gold_invoice_metrics.py

services/
  api/               # FastAPI service
  kafka/             # Kafka producers / consumers

dash/
  pages/
    invoices.py      # Upload & monitoring UI

architecture/
  event-flow.md

```
## Technologies Used

- Python
- Apache Airflow
- Apache Kafka
- FastAPI
- Dash
- AWS S3 (Data Lake)
- Pandas / PyArrow
- Docker / Docker Compose


---


