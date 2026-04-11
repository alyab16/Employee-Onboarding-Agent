# Acme Corp — Employee Onboarding Agent

> An autonomous AI agent that guides new employees through their entire onboarding journey — updating profiles across SaaS platforms, completing training, requesting system access, and answering role-specific questions from a RAG-powered company knowledge base.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-8B5CF6?style=flat)
![FastMCP](https://img.shields.io/badge/FastMCP-2.3-F97316?style=flat)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat&logo=next.js&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-SQLModel-6366F1?style=flat&logo=sqlite&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-EC4899?style=flat)
![LangSmith](https://img.shields.io/badge/LangSmith-Tracing-14B8A6?style=flat)

---

## Overview

The **Employee Onboarding Agent** is a full-stack agentic application built as a production-minded prototype. It demonstrates:

- **Native tool calling** via a LangGraph ReAct agent with per-employee memory
- **MCP-style extensibility** — each SaaS integration is a standalone FastMCP server; adding a new one requires zero changes to the orchestration logic
- **RAG** over 7 internal policy and role-specific documents using ChromaDB
- **Persistent state** — all structured data backed by SQLite via SQLModel
- **Real-time streaming** — SSE delivers agent thoughts, tool calls, and responses token-by-token to the frontend
- **LangSmith tracing** — full visibility into every agent run, tool call, and token

---

## System Architecture

```mermaid
flowchart TB
    classDef ui fill:#0EA5E9,stroke:#0284C7,color:#fff,font-weight:bold
    classDef api fill:#10B981,stroke:#059669,color:#fff,font-weight:bold
    classDef agent fill:#8B5CF6,stroke:#7C3AED,color:#fff,font-weight:bold
    classDef llm fill:#F59E0B,stroke:#D97706,color:#000,font-weight:bold
    classDef mcp fill:#F97316,stroke:#EA580C,color:#fff,font-weight:bold
    classDef db fill:#6366F1,stroke:#4F46E5,color:#fff,font-weight:bold
    classDef rag fill:#EC4899,stroke:#DB2777,color:#fff,font-weight:bold
    classDef trace fill:#14B8A6,stroke:#0D9488,color:#fff,font-weight:bold

    User(["👤 Employee\nBrowser"]):::ui

    subgraph FE ["Frontend — Next.js 16 · React 19 · Tailwind CSS v4"]
        Chat["💬 Chat Interface\nSSE Streaming"]:::ui
        Selector["👥 Employee\nSelector"]:::ui
    end

    subgraph BE ["Backend — FastAPI"]
        API["🔌 REST + SSE\nEndpoints"]:::api
        Orch["🧠 LangGraph\nReAct Agent"]:::agent
        Mem["💾 MemorySaver\nper-employee thread"]:::agent
    end

    LLM["🤖 OpenAI GPT\nor Ollama"]:::llm
    LS["📊 LangSmith\nTracing"]:::trace

    subgraph MCP ["MCP Servers — FastMCP (stdio transport)"]
        direction LR
        HR["🏛️ HR Platform"]:::mcp
        SL["💼 Slack"]:::mcp
        SF["☁️ Salesforce"]:::mcp
        TR["📚 Training"]:::mcp
        IT["🎫 IT Ticketing"]:::mcp
        KB["🔍 Knowledge Base"]:::mcp
    end

    SQLite[("🗄️ SQLite\ndata.db")]:::db
    Chroma[("🔮 ChromaDB\nVector Store")]:::rag
    Docs["📄 7 × Policy\nMarkdown Docs"]:::rag

    User <--> Chat
    Selector --> Chat
    Chat <-->|"HTTP POST + SSE"| API
    API <--> Orch
    Orch <--> Mem
    Orch <-->|"tool calls"| LLM
    Orch -.->|"traces"| LS
    Orch <-->|"MCP stdio"| MCP
    HR & SL & SF & TR & IT --> SQLite
    KB --> Chroma
    Docs -.->|"indexed at startup"| Chroma
```

---

## Agent Loop — ReAct Pattern

```mermaid
flowchart LR
    classDef input fill:#0EA5E9,stroke:#0284C7,color:#fff,font-weight:bold
    classDef think fill:#8B5CF6,stroke:#7C3AED,color:#fff,font-weight:bold
    classDef tool fill:#F97316,stroke:#EA580C,color:#fff,font-weight:bold
    classDef check fill:#F59E0B,stroke:#D97706,color:#000,font-weight:bold
    classDef stream fill:#10B981,stroke:#059669,color:#fff,font-weight:bold

    MSG["📨 User Message\n+ Employee ID"]:::input
    HIST["📜 Conversation\nHistory\nMemorySaver"]:::think
    LLM["🧠 LLM Reasoning\nWhat action next?"]:::think
    TOOL["⚡ Execute MCP Tool\nvia langchain-mcp-adapters"]:::tool
    RES["📋 Tool Result\nback to context"]:::tool
    MORE{"Stop reason\n= tool_use?"}:::check
    STREAM["💬 Stream tokens\nSSE → Frontend"]:::stream
    DONE["✅ done event\nto client"]:::stream

    MSG --> HIST
    HIST --> LLM
    LLM --> TOOL
    TOOL --> RES
    RES --> MORE
    MORE -->|"yes — more tools needed"| LLM
    MORE -->|"no — end_turn"| STREAM
    STREAM --> DONE
```

Each turn the agent autonomously decides which MCP tool to call, executes it, feeds the result back into context, and repeats until it has enough information to respond.

---

## Onboarding Workflow

```mermaid
flowchart TD
    classDef start fill:#0EA5E9,stroke:#0284C7,color:#fff,font-weight:bold
    classDef stage fill:#8B5CF6,stroke:#7C3AED,color:#fff,font-weight:bold
    classDef task fill:#F97316,stroke:#EA580C,color:#fff
    classDef async fill:#F59E0B,stroke:#D97706,color:#000
    classDef done fill:#10B981,stroke:#059669,color:#fff,font-weight:bold
    classDef rag fill:#EC4899,stroke:#DB2777,color:#fff

    START(["🚀 Employee begins\nonboarding"]):::start

    subgraph S1 ["Stage 1 — Profile Updates"]
        direction LR
        P1["Update\nSlack Profile"]:::task
        P2["Update\nHR Platform"]:::task
        P3["Update\nSalesforce"]:::task
    end

    subgraph S2 ["Stage 2 — Training Modules (ordered)"]
        direction LR
        T1["T1 · Company\nPolicies 30min"]:::task
        T2["T2 · Security\nAwareness 45min"]:::task
        T3["T3 · Data\nPrivacy 30min"]:::task
        T4["T4 · Role-Specific\nOnboarding 60min"]:::task
        T1 --> T2 --> T3 --> T4
    end

    subgraph S3 ["Stage 3 — System Access"]
        direction TB
        A1["Get role-based\naccess recommendations"]:::task
        A2["Employee selects\nrequired systems"]:::task
        A3["Submit manager\napproval request"]:::async
        A4["⏳ Await approval\nasync — agent stays helpful"]:::async
        A5["Submit IT\naccess ticket"]:::done
        A1 --> A2 --> A3 --> A4 --> A5
    end

    RAG(["🔍 Knowledge Base\nRAG — available\nthroughout all stages"]):::rag

    START --> S1
    S1 --> S2
    S2 --> S3
    RAG -.->|"answer any\npolicy question"| S1
    RAG -.-> S2
    RAG -.-> S3
```

---

## MCP Server Ecosystem

```mermaid
flowchart LR
    classDef agent fill:#8B5CF6,stroke:#7C3AED,color:#fff,font-weight:bold
    classDef server fill:#F97316,stroke:#EA580C,color:#fff,font-weight:bold
    classDef tool fill:#FED7AA,stroke:#F97316,color:#000
    classDef db fill:#6366F1,stroke:#4F46E5,color:#fff
    classDef rag fill:#EC4899,stroke:#DB2777,color:#fff

    Agent["🧠 LangGraph Agent\nMultiServerMCPClient"]:::agent

    Agent <-->|stdio| HR
    Agent <-->|stdio| SL
    Agent <-->|stdio| SF
    Agent <-->|stdio| TR
    Agent <-->|stdio| IT
    Agent <-->|stdio| KB

    subgraph HR ["🏛️ HR Platform"]
        direction TB
        h1["get_employee_profile"]:::tool
        h2["update_hr_profile"]:::tool
        h3["list_all_employees"]:::tool
        h4["get_peers_by_role_and_level"]:::tool
    end

    subgraph SL ["💼 Slack"]
        direction TB
        s1["get_slack_profile"]:::tool
        s2["update_slack_profile"]:::tool
        s3["add_to_slack_channels"]:::tool
    end

    subgraph SF ["☁️ Salesforce"]
        direction TB
        sf1["get_salesforce_user"]:::tool
        sf2["update_salesforce_profile"]:::tool
        sf3["assign_salesforce_permission_set"]:::tool
    end

    subgraph TR ["📚 Training Platform"]
        direction TB
        t1["get_training_catalog"]:::tool
        t2["get_training_status"]:::tool
        t3["complete_training_module"]:::tool
    end

    subgraph IT ["🎫 IT Ticketing"]
        direction TB
        i1["get_access_recommendations"]:::tool
        i2["request_manager_approval"]:::tool
        i3["check_approval_status"]:::tool
        i4["submit_it_ticket"]:::tool
        i5["get_it_tickets"]:::tool
    end

    subgraph KB ["🔍 Knowledge Base"]
        direction TB
        k1["search_company_knowledge"]:::tool
        k2["list_knowledge_sources"]:::tool
    end

    SQLite[("🗄️ SQLite")]:::db
    Chroma[("🔮 ChromaDB")]:::rag

    HR & SL & SF & TR & IT --> SQLite
    KB --> Chroma
```

---

## Data Architecture

```mermaid
flowchart TB
    classDef table fill:#6366F1,stroke:#4F46E5,color:#fff,font-weight:bold
    classDef col fill:#E0E7FF,stroke:#6366F1,color:#1e1b4b
    classDef chunk fill:#FCE7F3,stroke:#EC4899,color:#831843
    classDef doc fill:#EC4899,stroke:#DB2777,color:#fff,font-weight:bold

    subgraph SQL ["🗄️  SQLite — data.db  (SQLModel)"]
        direction LR
        EMP["employee"]:::table
        ACC["accessrecommendation\nrole · level · systems"]:::table
        TM["trainingmodule\nT1–T4"]:::table
        TC["trainingcompletion"]:::table
        APR["approvalrequest\nstatus · auto_approve_at"]:::table
        INC["itticket"]:::table
        SP["slackprofile"]:::table
        SFU["salesforceuser"]:::table
    end

    subgraph VEC ["🔮  ChromaDB — chroma_db/  (LangChain)"]
        direction LR
        COL["company_knowledge\ncollection"]:::doc
        subgraph Docs ["Source Documents (knowledge_docs/)"]
            D1["hr_policy.md"]:::chunk
            D2["code_of_conduct.md"]:::chunk
            D3["benefits_guide.md"]:::chunk
            D4["it_security_policy.md"]:::chunk
            D5["engineering_guide.md"]:::chunk
            D6["sales_guide.md"]:::chunk
            D7["marketing_guide.md"]:::chunk
        end
        D1 & D2 & D3 & D4 & D5 & D6 & D7 -->|"chunk 600 chars\noverlap 80"| COL
    end
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Next.js 16, React 19, Tailwind CSS v4 | Chat UI, streaming SSE, employee selector |
| **Backend** | FastAPI, Python 3.13, Uvicorn | REST API, SSE endpoint, app lifecycle |
| **Agent Orchestration** | LangGraph (`create_react_agent`) | ReAct loop, per-employee conversation state |
| **LLM** | OpenAI GPT-4o-mini / Ollama | Reasoning, tool selection, response generation |
| **MCP Servers** | FastMCP 2.3 | 6 independent mock SaaS integrations |
| **MCP Client** | langchain-mcp-adapters | Bridges LangGraph ↔ MCP stdio protocol |
| **Structured Data** | SQLModel + SQLite | Employees, training, approvals, tickets |
| **Vector Store** | ChromaDB + langchain-chroma | Semantic search over policy documents |
| **Embeddings** | OpenAI `text-embedding-3-small` / Ollama `nomic-embed-text` | Document indexing and query embedding |
| **Logging** | structlog | Structured JSON file logs + pretty console |
| **Tracing** | LangSmith | Full agent run visibility |

---

## Project Structure

```
EmployeeOnboardingAgent/
├── frontend/                          # Next.js 16 application
│   └── app/
│       ├── components/
│       │   ├── ChatInterface.tsx      # Main chat UI with SSE streaming
│       │   ├── MessageBubble.tsx      # Message + collapsible tool activity cards
│       │   └── EmployeeSelector.tsx   # Login / employee picker
│       ├── hooks/
│       │   └── useChat.ts             # SSE streaming state management
│       ├── types/index.ts             # Shared TypeScript types + server colour map
│       ├── page.tsx                   # Root: selector → chat
│       └── layout.tsx
│
└── backend/                           # FastAPI + LangGraph application
    ├── main.py                        # App entry point, startup sequence
    │
    ├── agent/
    │   ├── orchestrator.py            # LangGraph agent + MCP client lifecycle
    │   └── prompts.py                 # System prompt
    │
    ├── mcp_servers/                   # One FastMCP server per SaaS
    │   ├── data_store.py              # Seed data (canonical source of truth)
    │   ├── hr_server.py               # HR Platform tools
    │   ├── slack_server.py            # Slack tools
    │   ├── salesforce_server.py       # Salesforce tools
    │   ├── training_server.py         # Training Platform tools
    │   ├── it_server.py               # IT Ticketing + manager approval
    │   └── knowledge_server.py        # RAG search over company knowledge
    │
    ├── database/
    │   ├── engine.py                  # SQLModel engine (shared SQLite file)
    │   ├── models.py                  # All table definitions
    │   └── seed.py                    # One-time data seeding
    │
    ├── knowledge/
    │   └── vector_store.py            # ChromaDB build + hash-based rebuild detection
    │
    ├── knowledge_docs/                # Source documents for RAG
    │   ├── hr_policy.md
    │   ├── code_of_conduct.md
    │   ├── benefits_guide.md
    │   ├── it_security_policy.md
    │   ├── engineering_guide.md
    │   ├── sales_guide.md
    │   └── marketing_guide.md
    │
    ├── api/
    │   ├── chat.py                    # POST /api/chat (SSE), GET /api/chat/history
    │   └── admin.py                   # GET /api/admin/employees, /api/admin/mcp-servers
    │
    ├── utils/
    │   └── logger.py                  # structlog — console + rotating file handler
    │
    ├── logs/                          # Auto-created; app.log rotates at 10 MB
    ├── data.db                        # SQLite database (auto-created)
    ├── chroma_db/                     # ChromaDB persistence (auto-created)
    ├── requirements.txt
    └── .env
```

---

## Getting Started

### Prerequisites

- Python 3.13+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- An OpenAI API key **or** [Ollama](https://ollama.com) running locally

### 1 — Backend

```bash
cd backend

# Copy and configure environment
cp .env.example .env
# Edit .env: add OPENAI_API_KEY or configure Ollama settings

# Install dependencies
uv pip install -r requirements.txt

# If using Ollama — pull required models
ollama pull llama3.1:8b        # chat model
ollama pull nomic-embed-text   # embedding model

# Start the server (DB, seed data, and vector store initialise automatically)
uv run uvicorn main:app --reload
```

The first startup will:
1. Create `data.db` and seed all tables
2. Index the 7 knowledge docs into ChromaDB (subsequent startups skip this if docs haven't changed)
3. Spawn 6 FastMCP subprocesses
4. Start the FastAPI server on `http://localhost:8000`

### 2 — Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), select an employee, and start onboarding.

---

## Environment Variables

### Backend (`.env`)

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI key. If unset, Ollama is used |
| `MODEL_ID` | `gpt-4o-mini` | OpenAI model ID |
| `OLLAMA_MODEL` | `llama3.1:8b` | Ollama chat model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |
| `MAX_TOKENS` | `4096` | Max tokens per LLM response |
| `AUTO_APPROVE_SECONDS` | `30` | Seconds before manager approval auto-approves (demo) |
| `LANGCHAIN_TRACING_V2` | — | Set to `true` to enable LangSmith |
| `LANGCHAIN_API_KEY` | — | LangSmith API key |
| `LANGCHAIN_PROJECT` | `employee-onboarding-agent` | LangSmith project name |

### Frontend (`.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Send a message; returns SSE stream of agent events |
| `GET` | `/api/chat/history?employee_id=` | Full conversation history for an employee |
| `GET` | `/api/admin/employees` | List mock employees (used by frontend selector) |
| `GET` | `/api/admin/mcp-servers` | List active MCP servers and their discovered tools |
| `GET` | `/health` | Health check |

### SSE Event Types

```jsonc
{ "type": "text_delta",  "content": "Hi Alice..." }          // streaming token
{ "type": "tool_call",   "tool": "get_employee_profile",
  "server": "hr",        "input": { "employee_id": "emp001" } }
{ "type": "tool_result", "tool": "get_employee_profile",
  "output": "HR Platform — Employee Profile..." }
{ "type": "done" }
{ "type": "error",       "message": "..." }
```

---

## Mock Employees

| ID | Name | Role | Level | Department |
|---|---|---|---|---|
| `emp001` | Alice Johnson | Software Engineer | L3 | Engineering |
| `emp002` | Bob Chen | Account Executive | L2 | Sales |
| `emp003` | Carol Martinez | Marketing Manager | L4 | Marketing |

---

## Adding a New MCP Server

The architecture is designed so new SaaS integrations require **no changes to the agent or orchestration logic**:

1. Create `backend/mcp_servers/your_server.py`:

```python
from fastmcp import FastMCP
mcp = FastMCP("Your Service")

@mcp.tool()
def your_tool(param: str) -> str:
    """Description the LLM uses to decide when to call this tool."""
    return "result"

if __name__ == "__main__":
    mcp.run()
```

2. Register it in `agent/orchestrator.py`:

```python
MCP_SERVERS_CONFIG = {
    ...
    "your_service": {
        "command": "python",
        "args": [str(_SERVERS_DIR / "your_server.py")],
        "transport": "stdio",
    },
}
```

The agent discovers the new tools automatically on next startup — no other changes needed.

---

## Adding Knowledge Documents

Drop any `.md` file into `backend/knowledge_docs/`. The vector store automatically detects the change via content hash on the next startup and re-indexes.

---

## Observability

| Tool | What you see |
|---|---|
| **Console logs** | Pretty-printed structured logs per request |
| **`logs/app.log`** | Rotating JSON logs (10 MB × 5 files) |
| **LangSmith** | Full agent traces — every LLM call, tool call, token count, latency, and conversation thread |

Enable LangSmith by adding to `.env`:
```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your-key
LANGCHAIN_PROJECT=employee-onboarding-agent
```
