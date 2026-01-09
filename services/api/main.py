from fastapi import FastAPI, UploadFile, File
from datetime import datetime
import os

from app.routers import health, upload, invoices
from app.routers import approvals


print("ENV =", os.getenv("ENV"))
print("BUCKET =", os.getenv("S3_BUCKET"))

app = FastAPI(title="Platform-FastAPI")



# health / root
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "fastapi",
        "timestamp": datetime.utcnow().isoformat()
    }

app.include_router(health.router)
app.include_router(upload.router)
app.include_router(invoices.router)
app.include_router(approvals.router)