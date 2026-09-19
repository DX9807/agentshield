"""Mock Admin API."""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Mock Admin API", version="1.0.0")

# Mock admin operations
ADMIN_ACTIONS = []


class AdminAction(BaseModel):
    action: str
    target: str
    params: Optional[dict] = None


@app.post("/admin/users")
async def create_admin_user(action: AdminAction):
    """Create an admin user (high privilege)."""
    ADMIN_ACTIONS.append({
        "id": len(ADMIN_ACTIONS) + 1,
        "action": "create_user",
        "target": action.target,
        "params": action.params,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "status": "success",
        "message": f"Admin user {action.target} created",
        "action_id": len(ADMIN_ACTIONS)
    }


@app.post("/admin/system")
async def system_admin(action: AdminAction):
    """System administration (highest privilege)."""
    ADMIN_ACTIONS.append({
        "id": len(ADMIN_ACTIONS) + 1,
        "action": action.action,
        "target": action.target,
        "params": action.params,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "status": "success",
        "message": f"System action {action.action} executed",
        "action_id": len(ADMIN_ACTIONS)
    }


@app.get("/admin/audit")
async def admin_audit():
    """Get admin audit log."""
    return {"items": ADMIN_ACTIONS, "total": len(ADMIN_ACTIONS)}


@app.get("/")
async def root():
    return {"service": "Admin API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    from datetime import datetime
    uvicorn.run(app, host="0.0.0.0", port=8004)