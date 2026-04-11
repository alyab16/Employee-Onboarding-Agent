"""
Admin API endpoints — for demo/testing purposes.

GET  /api/admin/employees   → list employees from SQLite (for frontend dropdown)
GET  /api/admin/mcp-servers → list registered MCP servers and their tools
POST /api/admin/reset-db    → wipe all data and re-seed from mock data
"""

from fastapi import APIRouter, Request
from sqlmodel import select

from database.engine import get_session
from database.models import Employee
from database.seed import reset_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/employees")
async def list_employees():
    """Return the list of employees from SQLite for the frontend login selector."""
    with get_session() as session:
        employees = session.exec(select(Employee)).all()
        return {
            "employees": [
                {
                    "id": emp.id,
                    "name": emp.name,
                    "role": emp.role,
                    "level": emp.level,
                    "department": emp.department,
                    "email": emp.email,
                }
                for emp in employees
            ]
        }


@router.get("/mcp-servers")
async def list_mcp_servers(request: Request):
    """
    Return the MCP servers connected to the agent and their available tools.
    Demonstrates runtime tool discovery — the agent never hardcodes tools.
    """
    orchestrator = request.app.state.orchestrator
    tools = orchestrator._tools

    servers: dict[str, list[str]] = {}
    for tool in tools:
        server = getattr(tool, "metadata", {}).get("server", "unknown")
        servers.setdefault(server, []).append(tool.name)

    return {
        "mcp_servers": [
            {"server": srv, "tools": tool_names}
            for srv, tool_names in servers.items()
        ],
        "total_tools": len(tools),
    }


@router.post("/reset-db")
async def reset_database():
    """
    Wipe all data (completions, approvals, tickets, profiles) and re-seed
    from mock data. Useful for demo resets.
    """
    reset_db()
    return {"status": "ok", "message": "Database reset and re-seeded successfully."}
