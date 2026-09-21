"""Mock Admin API."""

from datetime import UTC, datetime

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock Admin API", version="1.0.0")

# Mock admin operations
ADMIN_ACTIONS = []


class AdminAction(BaseModel):
    action: str
    target: str
    params: dict | None = None


@app.post("/admin/users")
async def create_admin_user(action: AdminAction):
    """Create an admin user (high privilege)."""
    ADMIN_ACTIONS.append(
        {
            "id": len(ADMIN_ACTIONS) + 1,
            "action": "create_user",
            "target": action.target,
            "params": action.params,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )

    return {
        "status": "success",
        "message": f"Admin user {action.target} created",
        "action_id": len(ADMIN_ACTIONS),
    }


@app.post("/admin/system")
async def system_admin(action: AdminAction):
    """System administration (highest privilege)."""
    ADMIN_ACTIONS.append(
        {
            "id": len(ADMIN_ACTIONS) + 1,
            "action": action.action,
            "target": action.target,
            "params": action.params,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )

    return {
        "status": "success",
        "message": f"System action {action.action} executed",
        "action_id": len(ADMIN_ACTIONS),
    }


@app.get("/admin/audit")
async def admin_audit():
    """Get admin audit log."""
    return {"items": ADMIN_ACTIONS, "total": len(ADMIN_ACTIONS)}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "Admin API"}


@app.get("/")
async def root():
    return {"service": "Admin API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
