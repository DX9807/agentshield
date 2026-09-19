"""Mock Customer API with vulnerabilities."""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
from datetime import datetime

app = FastAPI(title="Mock Customer API", version="1.0.0")

# Mock customer data
CUSTOMERS = {
    "CUST-001": {
        "id": "CUST-001",
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-0100",
        "address": "123 Main St, Anytown, USA",
        "credit_card": "4111-1111-1111-1111",
        "created_at": "2024-01-01T00:00:00Z"
    },
    "CUST-002": {
        "id": "CUST-002",
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
        "phone": "+1-555-0101",
        "address": "456 Oak Ave, Othertown, USA",
        "credit_card": "4222-2222-2222-2222",
        "created_at": "2024-01-02T00:00:00Z"
    },
    "CUST-003": {
        "id": "CUST-003",
        "name": "Bob Johnson",
        "email": "bob.johnson@example.com",
        "phone": "+1-555-0102",
        "address": "789 Pine Rd, Smallville, USA",
        "credit_card": "4333-3333-3333-3333",
        "created_at": "2024-01-03T00:00:00Z"
    },
    "CUST-004": {
        "id": "CUST-004",
        "name": "Alice Williams",
        "email": "alice.williams@example.com",
        "phone": "+1-555-0103",
        "address": "321 Elm St, Bigcity, USA",
        "credit_card": "4444-4444-4444-4444",
        "created_at": "2024-01-04T00:00:00Z"
    },
    "CUST-005": {
        "id": "CUST-005",
        "name": "Carol Davis",
        "email": "carol.davis@example.com",
        "phone": "+1-555-0104",
        "address": "654 Maple Dr, Metropolis, USA",
        "credit_card": "4555-5555-5555-5555",
        "created_at": "2024-01-05T00:00:00Z"
    }
}

# Mock orders
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


class CustomerResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    address: str
    credit_card: Optional[str] = None
    created_at: str


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


@app.get("/customers")
async def list_customers(limit: int = 10, offset: int = 0):
    """List all customers."""
    customers = list(CUSTOMERS.values())[offset:offset + limit]
    return {
        "items": customers,
        "total": len(CUSTOMERS),
        "limit": limit,
        "offset": offset
    }


@app.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Get customer by ID."""
    if customer_id not in CUSTOMERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )
    
    # VULNERABILITY: Returns full customer data including credit card
    return CUSTOMERS[customer_id]


@app.put("/customers/{customer_id}")
async def update_customer(customer_id: str, update: CustomerUpdate):
    """Update customer."""
    if customer_id not in CUSTOMERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )
    
    customer = CUSTOMERS[customer_id].copy()
    update_dict = update.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            customer[key] = value
    
    CUSTOMERS[customer_id] = customer
    return customer


@app.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str):
    """Delete customer."""
    if customer_id not in CUSTOMERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )
    
    del CUSTOMERS[customer_id]
    return {"status": "deleted", "customer_id": customer_id}


@app.get("/")
async def root():
    return {"service": "Customer API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# Run with: uvicorn customer_api:app --port 8001
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)