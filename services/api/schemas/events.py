from pydantic import BaseModel
from datetime import datetime

class InvoiceUploadedEvent(BaseModel):
    filename: str
    source: str
    uploaded_at: datetime
