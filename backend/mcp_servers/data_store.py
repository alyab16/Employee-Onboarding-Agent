"""
Shared mock data imported by all MCP servers at startup.
In production each server would connect to its real SaaS API instead.
"""

EMPLOYEES: dict[str, dict] = {
    "emp001": {
        "id": "emp001",
        "name": "Alice Johnson",
        "email": "alice.johnson@acme.com",
        "role": "Software Engineer",
        "level": "L3",
        "department": "Engineering",
        "manager": "David Park",
        "manager_email": "david.park@acme.com",
        "start_date": "2026-04-11",
        "title": "Software Engineer III",
        "phone": None,
        "location": None,
    },
    "emp002": {
        "id": "emp002",
        "name": "Bob Chen",
        "email": "bob.chen@acme.com",
        "role": "Account Executive",
        "level": "L2",
        "department": "Sales",
        "manager": "Sarah Wilson",
        "manager_email": "sarah.wilson@acme.com",
        "start_date": "2026-04-11",
        "title": "Account Executive II",
        "phone": None,
        "location": None,
    },
    "emp003": {
        "id": "emp003",
        "name": "Carol Martinez",
        "email": "carol.martinez@acme.com",
        "role": "Marketing Manager",
        "level": "L4",
        "department": "Marketing",
        "manager": "Tom Hughes",
        "manager_email": "tom.hughes@acme.com",
        "start_date": "2026-04-11",
        "title": "Senior Marketing Manager",
        "phone": None,
        "location": None,
    },
}

# System access recommendations keyed by role → level → list of systems
ACCESS_MATRIX: dict[str, dict[str, list[str]]] = {
    "Software Engineer": {
        "L1": ["GitHub", "Jira", "Confluence", "Slack"],
        "L2": ["GitHub", "Jira", "Confluence", "Slack", "AWS (read-only)", "Docker Hub"],
        "L3": ["GitHub", "Jira", "Confluence", "Slack", "AWS", "Docker Hub", "Datadog", "CircleCI"],
        "L4": ["GitHub", "Jira", "Confluence", "Slack", "AWS", "Docker Hub", "Datadog", "CircleCI", "PagerDuty", "Terraform Cloud"],
        "L5": ["GitHub", "Jira", "Confluence", "Slack", "AWS", "Docker Hub", "Datadog", "CircleCI", "PagerDuty", "Terraform Cloud", "Production DB Access", "ArgoCD"],
    },
    "Account Executive": {
        "L1": ["Salesforce CRM", "HubSpot", "Slack", "Outlook 365", "Zoom"],
        "L2": ["Salesforce CRM", "HubSpot", "Slack", "Outlook 365", "Zoom", "Gong", "LinkedIn Sales Navigator"],
        "L3": ["Salesforce CRM", "HubSpot", "Slack", "Outlook 365", "Zoom", "Gong", "LinkedIn Sales Navigator", "Clari", "DocuSign"],
        "L4": ["Salesforce CRM", "HubSpot", "Slack", "Outlook 365", "Zoom", "Gong", "LinkedIn Sales Navigator", "Clari", "DocuSign", "Salesforce CPQ"],
        "L5": ["Salesforce CRM", "HubSpot", "Slack", "Outlook 365", "Zoom", "Gong", "LinkedIn Sales Navigator", "Clari", "DocuSign", "Salesforce CPQ", "Tableau"],
    },
    "Marketing Manager": {
        "L1": ["HubSpot", "Google Analytics", "Slack", "Canva", "Mailchimp"],
        "L2": ["HubSpot", "Google Analytics", "Slack", "Canva", "Mailchimp", "Semrush", "Buffer"],
        "L3": ["HubSpot", "Google Analytics", "Slack", "Canva", "Mailchimp", "Semrush", "Buffer", "Marketo", "Salesforce CRM (read)"],
        "L4": ["HubSpot", "Google Analytics", "Slack", "Canva", "Mailchimp", "Semrush", "Buffer", "Marketo", "Salesforce CRM (read)", "LinkedIn Campaign Manager", "Google Ads"],
        "L5": ["HubSpot", "Google Analytics", "Slack", "Canva", "Mailchimp", "Semrush", "Buffer", "Marketo", "Salesforce CRM (read)", "LinkedIn Campaign Manager", "Google Ads", "Tableau", "Looker"],
    },
}

TRAINING_MODULES: dict[str, dict] = {
    "T1": {
        "id": "T1",
        "name": "Company Policies & Code of Conduct",
        "duration_minutes": 30,
        "description": "Overview of company values, HR guidelines, and code of conduct. Required for all employees.",
    },
    "T2": {
        "id": "T2",
        "name": "Security Awareness Training",
        "duration_minutes": 45,
        "description": "Cybersecurity best practices, phishing awareness, password policies, and secure data handling.",
    },
    "T3": {
        "id": "T3",
        "name": "Data Privacy & Compliance",
        "duration_minutes": 30,
        "description": "GDPR, CCPA, and Acme Corp data privacy policies. Required for all employees.",
    },
    "T4": {
        "id": "T4",
        "name": "Role-Specific Onboarding",
        "duration_minutes": 60,
        "description": "Department-specific tools, workflows, team processes, and key contacts.",
    },
}
