"""Mock Order API."""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

app = FastAPI(title="Mock Order API", version="1.0.0")

# Mock orders (extends from customer_api)
ORDERS = {
    "ORD-001": {
        "id": "ORD-001",
        "customer_id": "CUST-001",
        "total": 150.00,
        "status": "delivered",
        "items": ["Item-001", "Item-002"],
        "created_at": "2024-01-01T00:00:00Z"
    },
    "ORD-002": {
        "id": "ORD-002",
        "customer_id": "CUST-001",
        "total": 75.50,
        "status": "pending",
        "items": ["Item-003"],
        "created_at": "2024-01-02T00:00:00Z"
    },
    "ORD-003": {
        "id": "ORD-003",
        "customer_id": "CUST-002",
        "total": 230.00,
        "status": "delivered",
        "items": ["Item-004", "Item-005", "Item-006"],
        "created_at": "2024-01-03T00:00:00Z"
    }
}


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    total: float
    status: str
    items: list
    created_at: str


@app.get("/orders")
async def list_orders():
    """List all orders."""
    return {"items": list(ORDERS.values()), "total": len(ORDERS)}


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order by ID."""
    if order_id not in ORDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    return ORDERS[order_id]


@app.get("/customers/{customer_id}/orders")
async def get_customer_orders(customer_id: str):
    """Get orders for a customer."""
    customer_orders = [o for o in ORDERS.values() if o["customer_id"] == customer_id]
    return {"items": customer_orders, "total": len(customer_orders)}


@app.get("/")
async def root():
    return {"service": "Order API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)