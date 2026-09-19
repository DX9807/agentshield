"""Mock Refund API."""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

app = FastAPI(title="Mock Refund API", version="1.0.0")

# Mock refunds
REFUNDS = {}


class RefundRequest(BaseModel):
    order_id: str = Field(..., description="Order ID to refund")
    customer_id: str = Field(..., description="Customer ID")
    amount: float = Field(..., gt=0, description="Refund amount")
    reason: str = Field(..., description="Reason for refund")
    notes: Optional[str] = None


class RefundResponse(BaseModel):
    id: str
    order_id: str
    customer_id: str
    amount: float
    reason: str
    status: str
    created_at: str
    processed_at: Optional[str] = None


@app.post("/refunds")
async def create_refund(request: RefundRequest):
    """Create a refund."""
    refund_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
    
    refund = {
        "id": refund_id,
        "order_id": request.order_id,
        "customer_id": request.customer_id,
        "amount": request.amount,
        "reason": request.reason,
        "notes": request.notes,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "processed_at": None
    }
    
    REFUNDS[refund_id] = refund
    return refund


@app.get("/refunds")
async def list_refunds():
    """List all refunds."""
    return {"items": list(REFUNDS.values()), "total": len(REFUNDS)}


@app.get("/refunds/{refund_id}")
async def get_refund(refund_id: str):
    """Get refund by ID."""
    if refund_id not in REFUNDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Refund {refund_id} not found"
        )
    return REFUNDS[refund_id]


@app.post("/refunds/{refund_id}/process")
async def process_refund(refund_id: str):
    """Process a refund."""
    if refund_id not in REFUNDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Refund {refund_id} not found"
        )
    
    refund = REFUNDS[refund_id]
    refund["status"] = "processed"
    refund["processed_at"] = datetime.utcnow().isoformat()
    REFUNDS[refund_id] = refund
    
    return refund


@app.get("/")
async def root():
    return {"service": "Refund API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)