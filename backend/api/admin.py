"""
Admin API endpoints — for demo/testing purposes.

GET  /api/admin/employees   → list mock employees (for frontend dropdown)
GET  /api/admin/mcp-servers → list registered MCP servers and their tools
"""

from fastapi import APIRouter, Request
from mcp_servers.data_store import EMPLOYEES

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/employees")
async def list_employees():
    """Return the list of mock employees for the frontend login selector."""
    return {
        "employees": [
            {
                "id": emp["id"],
                "name": emp["name"],
                "role": emp["role"],
                "level": emp["level"],
                "department": emp["department"],
                "email": emp["email"],
            }
            for emp in EMPLOYEES.values()
        ]
    }


@router.get("/mcp-servers")
async def list_mcp_servers(request: Request):
    """
    Return the MCP servers connected to the agent and their available tools.
    Demonstrates runtime tool discovery — the agent never hardcodes tools.
    """
    orchestrator = request.app.state.orchestrator
    tools = orchestrator._mcp_client.get_tools()

    servers: dict[str, list[str]] = {}
    for tool in tools:
        # langchain-mcp-adapters attaches server name as tool metadata
        server = getattr(tool, "metadata", {}).get("server", "unknown")
        servers.setdefault(server, []).append(tool.name)

    return {
        "mcp_servers": [
            {"server": srv, "tools": tool_names}
            for srv, tool_names in servers.items()
        ],
        "total_tools": len(tools),
    }
