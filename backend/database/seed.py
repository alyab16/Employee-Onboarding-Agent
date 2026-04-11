"""
Seed the SQLite database from the canonical mock data in mcp_servers/data_store.py.
Called once at application startup — skips tables that already have data.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlmodel import select, Session
from database.engine import get_engine
from database.models import (
    Employee, AccessRecommendation, TrainingModule,
    SlackProfile, SalesforceUser,
)
from mcp_servers.data_store import EMPLOYEES, ACCESS_MATRIX, TRAINING_MODULES


def seed_all() -> None:
    engine = get_engine()
    with Session(engine) as session:
        _seed_employees(session)
        _seed_access_matrix(session)
        _seed_training_modules(session)
        _seed_slack_profiles(session)
        _seed_salesforce_users(session)
        session.commit()


def _seed_employees(session: Session) -> None:
    if session.exec(select(Employee)).first():
        return
    for data in EMPLOYEES.values():
        session.add(Employee(**{k: v for k, v in data.items() if v is not None or k in Employee.__fields__}))


def _seed_access_matrix(session: Session) -> None:
    if session.exec(select(AccessRecommendation)).first():
        return
    for role, levels in ACCESS_MATRIX.items():
        for level, systems in levels.items():
            session.add(AccessRecommendation(
                role=role,
                level=level,
                systems=json.dumps(systems),
            ))


def _seed_training_modules(session: Session) -> None:
    if session.exec(select(TrainingModule)).first():
        return
    for data in TRAINING_MODULES.values():
        session.add(TrainingModule(
            id=data["id"],
            name=data["name"],
            duration_minutes=data["duration_minutes"],
            description=data["description"],
        ))


def _seed_slack_profiles(session: Session) -> None:
    if session.exec(select(SlackProfile)).first():
        return
    for emp_id, emp in EMPLOYEES.items():
        session.add(SlackProfile(
            employee_id=emp_id,
            display_name=emp["name"],
            title=emp.get("title"),
            channels=json.dumps(["#general", "#random", "#announcements"]),
        ))


def _seed_salesforce_users(session: Session) -> None:
    if session.exec(select(SalesforceUser)).first():
        return
    for emp_id, emp in EMPLOYEES.items():
        session.add(SalesforceUser(
            employee_id=emp_id,
            sf_user_id=f"005{emp_id.upper()}",
            username=f"{emp['email'].split('@')[0]}@acme.salesforce.com",
            title=emp.get("title"),
            department=emp.get("department"),
        ))
