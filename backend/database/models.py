"""
SQLModel table definitions.
All MCP servers and the FastAPI app share the same SQLite file (data.db).
"""

from typing import Optional
from sqlmodel import Field, SQLModel


class Employee(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    email: str
    role: str
    level: str
    department: str
    manager: str
    manager_email: str
    start_date: str
    title: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    personal_email: Optional[str] = None


class AccessRecommendation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    role: str
    level: str
    systems: str  # JSON-encoded list[str]


class TrainingModule(SQLModel, table=True):
    id: str = Field(primary_key=True)  # T1 … T4
    name: str
    duration_minutes: int
    description: str


class TrainingCompletion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: str
    module_id: str
    completed_at: str


class ApprovalRequest(SQLModel, table=True):
    request_id: str = Field(primary_key=True)
    employee_id: str
    manager: str
    manager_email: str
    requested_systems: str  # JSON-encoded list[str]
    status: str             # pending | approved | denied
    created_at: str
    auto_approve_at: str
    notes: Optional[str] = None


class ITTicket(SQLModel, table=True):
    ticket_id: str = Field(primary_key=True)
    employee_id: str
    systems: str  # JSON-encoded list[str]
    status: str   # open | in_progress | completed
    created_at: str
    estimated_completion: str


class SlackProfile(SQLModel, table=True):
    employee_id: str = Field(primary_key=True)
    display_name: str
    title: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    status_text: str = "Starting my onboarding journey!"
    status_emoji: str = ":wave:"
    channels: str = '["#general","#random","#announcements"]'  # JSON


class SalesforceUser(SQLModel, table=True):
    employee_id: str = Field(primary_key=True)
    sf_user_id: str
    username: str
    title: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    profile: str = "Standard User"
    permission_sets: str = "[]"  # JSON
