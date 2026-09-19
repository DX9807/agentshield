"""Mock IAM API."""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import uuid

app = FastAPI(title="Mock IAM API", version="1.0.0")

# Mock users
USERS = {}


class UserCreate(BaseModel):
    username: str
    email: str
    role: str
    department: Optional[str] = None


@app.post("/iam/users")
async def create_user(user: UserCreate):
    """Create a new user (IAM operation)."""
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    new_user = {
        "id": user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "department": user.department,
        "created_at": datetime.utcnow().isoformat()
    }
    USERS[user_id] = new_user
    
    return {
        "status": "created",
        "user": new_user
    }


@app.get("/iam/users")
async def list_users():
    """List all users."""
    return {"items": list(USERS.values()), "total": len(USERS)}


@app.get("/iam/users/{user_id}")
async def get_user(user_id: str):
    """Get user by ID."""
    if user_id not in USERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    return USERS[user_id]


@app.delete("/iam/users/{user_id}")
async def delete_user(user_id: str):
    """Delete user."""
    if user_id not in USERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    del USERS[user_id]
    return {"status": "deleted", "user_id": user_id}


@app.put("/iam/users/{user_id}/role")
async def update_user_role(user_id: str, role: str):
    """Update user role."""
    if user_id not in USERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    USERS[user_id]["role"] = role
    return {"status": "updated", "user": USERS[user_id]}


@app.get("/")
async def root():
    return {"service": "IAM API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    from datetime import datetime
    uvicorn.run(app, host="0.0.0.0", port=8006)