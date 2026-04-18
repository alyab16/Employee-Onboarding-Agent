"""
Golden dataset for the onboarding agent.

Each case describes:
  - id:                a short stable identifier
  - employee_id:       which seeded employee to act as (emp001 / emp002 / emp003)
  - input:             the user message
  - expected_specialist: which specialist the supervisor should route to first
  - expected_tools:    tools that MUST appear in the trajectory (in any order)
  - forbidden_tools:   tools that must NOT appear
  - expected_contains: case-insensitive substrings required in the final response
  - quality_rubric:    free-form description for the LLM-as-judge evaluator
  - approve_all:       auto-approve every HITL interrupt (default True)

Tune sparingly — a good eval set stays small, legible, and representative.
"""

from dataclasses import dataclass, field


@dataclass
class EvalCase:
    id: str
    employee_id: str
    input: str
    expected_specialist: str
    expected_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    expected_contains: list[str] = field(default_factory=list)
    quality_rubric: str = ""
    approve_all: bool = True


DATASET: list[EvalCase] = [
    # ---- HR Profile ---------------------------------------------------------
    EvalCase(
        id="hr_update_slack_phone",
        employee_id="emp001",
        input="Please update my Slack profile phone number to 415-555-0100.",
        expected_specialist="hr_profile",
        expected_tools=["update_slack_profile"],
        forbidden_tools=["complete_training_module", "submit_it_ticket"],
        expected_contains=["slack", "updated"],
        quality_rubric="Confirms the Slack phone update and states the new value.",
    ),
    EvalCase(
        id="hr_update_hr_location",
        employee_id="emp002",
        input="Set my HR location to 'New York, NY' and phone to 212-555-0200.",
        expected_specialist="hr_profile",
        expected_tools=["update_hr_profile"],
        forbidden_tools=["update_slack_profile", "update_salesforce_profile"],
        expected_contains=["updated"],
        quality_rubric="Confirms the HR Platform update mentioning the new location and phone.",
    ),
    EvalCase(
        id="hr_update_salesforce_title",
        employee_id="emp002",
        input="Update my Salesforce title to 'Senior Account Executive'.",
        expected_specialist="hr_profile",
        expected_tools=["update_salesforce_profile"],
        forbidden_tools=["update_hr_profile"],
        expected_contains=["salesforce", "senior account"],
        quality_rubric="Confirms Salesforce title change.",
    ),
    EvalCase(
        id="hr_lookup_profile",
        employee_id="emp001",
        input="Can you remind me what's on my HR profile?",
        expected_specialist="hr_profile",
        expected_tools=["get_employee_profile"],
        forbidden_tools=["update_hr_profile", "update_slack_profile"],
        expected_contains=["alice"],
        quality_rubric="Reads back profile fields without mutating anything.",
    ),

    # ---- Training -----------------------------------------------------------
    EvalCase(
        id="training_status",
        employee_id="emp001",
        input="Where am I with my onboarding training?",
        expected_specialist="training",
        expected_tools=["get_training_status"],
        forbidden_tools=["complete_training_module"],
        expected_contains=["t1"],
        quality_rubric="Lists training modules and their completion state.",
    ),
    EvalCase(
        id="training_complete_t1",
        employee_id="emp001",
        input="I just finished the Company Policies module. Please mark T1 complete.",
        expected_specialist="training",
        expected_tools=["complete_training_module"],
        forbidden_tools=["update_hr_profile", "submit_it_ticket"],
        expected_contains=["t1"],
        quality_rubric="Marks T1 complete and reports progress.",
    ),
    EvalCase(
        id="training_catalog",
        employee_id="emp003",
        input="What training modules do I have to complete?",
        expected_specialist="training",
        expected_tools=["get_training_catalog"],
        forbidden_tools=["complete_training_module"],
        expected_contains=["t1", "t2", "t3", "t4"],
        quality_rubric="Enumerates all four required training modules.",
    ),

    # ---- IT / Access --------------------------------------------------------
    EvalCase(
        id="it_access_recommendations",
        employee_id="emp001",
        input="Which systems do I need access to for my role?",
        expected_specialist="it_access",
        expected_tools=["get_access_recommendations"],
        forbidden_tools=["submit_it_ticket", "request_manager_approval"],
        expected_contains=["github"],
        quality_rubric="Lists recommended systems for an L3 Software Engineer.",
    ),
    EvalCase(
        id="it_check_approval",
        employee_id="emp002",
        input="Has my access request been approved yet?",
        expected_specialist="it_access",
        expected_tools=["check_approval_status"],
        forbidden_tools=["submit_it_ticket"],
        expected_contains=[],
        quality_rubric="Reports the current approval status honestly.",
    ),

    # ---- Knowledge ----------------------------------------------------------
    EvalCase(
        id="knowledge_pto_policy",
        employee_id="emp001",
        input="How many PTO days do I get as an L3?",
        expected_specialist="knowledge",
        expected_tools=["search_company_knowledge"],
        forbidden_tools=["update_hr_profile", "complete_training_module"],
        expected_contains=["pto"],
        quality_rubric="Cites the HR policy doc and answers with a specific PTO allotment for L3.",
    ),
    EvalCase(
        id="knowledge_401k",
        employee_id="emp002",
        input="What's Acme's 401(k) matching policy?",
        expected_specialist="knowledge",
        expected_tools=["search_company_knowledge"],
        forbidden_tools=["update_salesforce_profile"],
        expected_contains=["401"],
        quality_rubric="Answers using the benefits guide; cites the source doc.",
    ),
    EvalCase(
        id="knowledge_code_review",
        employee_id="emp001",
        input="What's our code review process?",
        expected_specialist="knowledge",
        expected_tools=["search_company_knowledge"],
        forbidden_tools=["complete_training_module"],
        expected_contains=["review"],
        quality_rubric="Uses the engineering guide to describe code review, cites the source.",
    ),
    EvalCase(
        id="knowledge_mfa_policy",
        employee_id="emp001",
        input="Do I have to use MFA on my work laptop?",
        expected_specialist="knowledge",
        expected_tools=["search_company_knowledge"],
        expected_contains=["mfa"],
        quality_rubric="Cites the IT security policy and confirms MFA requirement.",
    ),

    # ---- Routing edge cases -------------------------------------------------
    EvalCase(
        id="route_identity",
        employee_id="emp001",
        input="Hi — can you remind me what team I'm on?",
        expected_specialist="hr_profile",
        expected_tools=["get_employee_profile"],
        expected_contains=["engineering"],
        quality_rubric="Identifies the employee's department / team without write actions.",
    ),
    EvalCase(
        id="route_refuses_out_of_domain",
        employee_id="emp001",
        input="Can you order me a laptop from Apple?",
        expected_specialist="it_access",
        forbidden_tools=["submit_it_ticket"],
        expected_contains=[],
        quality_rubric="Politely declines or redirects; does not fabricate an IT ticket for unsupported work.",
    ),
]


def by_id(case_id: str) -> EvalCase:
    for c in DATASET:
        if c.id == case_id:
            return c
    raise KeyError(case_id)
