"""Mock Payroll API."""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Mock Payroll API", version="1.0.0")

# Mock payroll data
PAYROLL = {
    "employee_001": {
        "id": "employee_001",
        "name": "John Employee",
        "position": "Senior Engineer",
        "salary": 120000,
        "department": "Engineering",
        "bank_account": "1234567890",
        "ssn": "123-45-6789"
    },
    "employee_002": {
        "id": "employee_002",
        "name": "Jane Employee",
        "position": "Product Manager",
        "salary": 150000,
        "department": "Product",
        "bank_account": "0987654321",
        "ssn": "987-65-4321"
    }
}


@app.get("/payroll/employees")
async def list_employees():
    """List all employees."""
    return {"items": list(PAYROLL.values()), "total": len(PAYROLL)}


@app.get("/payroll/employees/{employee_id}")
async def get_employee(employee_id: str):
    """Get employee payroll details."""
    if employee_id not in PAYROLL:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found"
        )
    return PAYROLL[employee_id]


@app.get("/payroll/department/{department}")
async def get_department_payroll(department: str):
    """Get payroll for a department."""
    employees = [e for e in PAYROLL.values() if e["department"] == department]
    total_salary = sum(e["salary"] for e in employees)
    
    return {
        "department": department,
        "employees": employees,
        "count": len(employees),
        "total_salary": total_salary
    }


@app.get("/")
async def root():
    return {"service": "Payroll API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)