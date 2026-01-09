from pydantic import BaseModel
from typing import List


class InvoiceToApprove(BaseModel):
    filename: str


class ApproveInvoicesRequest(BaseModel):
    invoices: List[InvoiceToApprove]
    approved_by: str