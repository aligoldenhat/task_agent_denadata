# Task Agent Denadata

built with LangGraph + LangChain + FastAPI.

---

## Quick Start

```bash
cp .env.example .env
# fill in OPENAI_API_KEY, TASK_CSV, USERS_CSV in .env

docker compose up --build
```

Docker Compose overrides DB_PATH, LOG_PATH, TASK_CSV, and USERS_CSV automatically to container paths — you only need to set OPENAI_API_KEY in .env.

---

## Prerequisites

- Docker + Docker Compose
- An OpenAI API key

For local development without Docker:

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)

---

## Local Development (without Docker)

```bash
uv sync
uv run uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## API

### `POST /chat`

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "چند تسک باز داریم؟"}'
```

**Request:**

```json
{
  "conversation_id": "optional-uuid-for-multi-turn",
  "message": "چند تسک باز داریم؟"
}
```

**Response:**

```json
{
  "conversation_id": "3f8a2b1c-...",
  "answer": "در حال حاضر ۵ تسک باز وجود دارد."
}
```

Omit `conversation_id` to start a new session. Pass it back on subsequent requests to continue the conversation — the agent remembers context within a session.

### `GET /health`

```bash
curl http://localhost:8001/health
# {"status": "ok"}
```

---

## Running Tests

```bash
uv sync --group dev
uv run pytest -v
```

---

## Architecture

```
POST /chat
    │
    ▼
FastAPI (routers.py)
    │  conversation_id → thread_id
    ▼
LangGraph (agent.py)
    │
    ├── llm_node      calls OpenAI, decides whether to use tools
    │       │
    │       ├── tool_calls? → tool_node → back to llm_node
    │       │
    │       └── no tool_calls? → final answer
    │
    └── AsyncSqliteSaver   persists full message history per thread_id
    │
    ▼
14 LangChain Tools (tools.py)
    │   count, filter, search, create, update
    ▼
pandas DataFrames
    │   tasks.csv ⟕ users.csv (joined on assignee_id)
    └── runtime_mutations.json (create/update operations)
```

---

## Technical Decisions

### LangGraph over a simple ReAct loop

LangGraph gives a graph which is suitable for simple ReAct loop. there is a router that check if the LLM call a tool or not.

### AsyncSqliteSaver for memory

LangGraph's built-in checkpointer stores the full message history keyed by `thread_id` (your `conversation_id`). SQLite is used over in-memory storage so sessions survive restarts.

### Pandas tools

The data is static CSV — pandas is simpler, faster to iterate on. Each tool function computes its answer directly from the DataFrame, making hallucination structurally impossible (the LLM never sees raw data).

### Runtime mutations without a database

`update_task` and `create_task` write to a JSON sidecar file (`runtime_mutations.json`).

### LLM choice

Configured via `OPENAI_MODEL` env var. Defaults to `gpt-5.4-mini`.

### Out-of-scope handling

The system prompt instructs the agent to decline questions outside the tasks/personnel domain and ask clarifying questions when the request is ambiguous.

### Error handling

LLM errors (`APITimeoutError`, `RateLimitError`, `APIConnectionError`) are caught in the router and mapped to appropriate HTTP status codes (504, 429, 502).

---

## Project Structure

```
.
├── compose.yaml
├── docker/
│   └── chat.Dockerfile
├── data/
│   ├── tasks.csv
│   └── users.csv
├── src/
│   ├── main.py           # FastAPI app + lifespan
│   ├── config.py         # pydantic-settings
│   ├── log.py            # logging config
│   ├── api/
│   │   └── routers.py    # POST /chat
│   ├── graph/
│   │   ├── agent.py      # LangGraph graph + AsyncSqliteSaver
│   │   ├── nodes.py      # llm_node, tool_node
│   │   ├── state.py      # AgentState
│   │   └── utils/
│   │       ├── data_store.py   # CSV loader + mutations
│   │       └── tools.py        # 14 LangChain tools
│   └── schema/
│       └── main_schema.py
└── tests/
    ├── test_chat.py    # integration tests
    └── test_tools.py   # unit tests
```
