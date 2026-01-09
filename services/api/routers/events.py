from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/events")

class InvoiceUpliaded(BaseModel):
    file_path: str
    source: str

@router.post("/invoice-uploaded")
def invoice_uploaded(event: InvoiceUploaded):
    print("Event:", event)
    return {"status": "ok"}
