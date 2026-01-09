from pydantic import BaseModel
from typing import List


class InvoiceApproveItem(BaseModel):
    filename: str


class ApproveInvoicesRequest(BaseModel):
    invoices: List[InvoiceApproveItem]
    approved_by: str
