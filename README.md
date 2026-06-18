# Dash

A **self-learning data agent** built with systems engineering principles. It grounds answers in 6 layers of context and improves with every query.

Chat with Dash via Slack, the terminal, or the [AgentOS](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=dash&utm_term=agentos) web UI.

## Quick Start

```sh
# Clone the repo
git clone https://github.com/agno-agi/dash.git && cd dash

cp example.env .env
# Edit .env and add your OPENROUTER_API_KEY

# Start the system
docker compose up -d --build

# Load knowledge after `public.malls` and `public.stores` exist
docker exec -it dash-api python scripts/load_knowledge.py
```

Confirm Dash is running at [http://localhost:8000/docs](http://localhost:8000/docs).

### Connect to the Web UI

1. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=dash&utm_term=agentos) and login
2. Add OS → Local → `http://localhost:8000`
3. Click "Connect"

**Try it** (mall and store dataset):

- How many malls do we have by city?
- Which malls have the most stores?
- Break down stores by category
- Create a view for store counts by mall

## Deploy to Railway

Railway deployment uses `.env.production` to keep production credentials separate from local dev.

```sh
cp example.env .env.production
# Edit .env.production — set OPENROUTER_API_KEY
```

### Step 1: Deploy infrastructure

This creates the Railway project, database, and app service. The app will crash-loop until the JWT key is added in the next step — that's expected.

```sh
railway login
./scripts/railway_up.sh
```

### Step 2: Get your JWT key

Production requires a `JWT_VERIFICATION_KEY` from [AgentOS](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=dash&utm_term=agentos). You need the Railway domain from step 1 to set this up.

1. Copy your Railway domain from the output of step 1 (e.g. `dash-production-xxxx.up.railway.app`)
2. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=dash&utm_term=agentos) and login
3. Add OS → Live → paste your Railway URL
4. Go to **Settings** and generate a key pair
5. Add the public key to `.env.production` (wrap in single quotes):

```bash
JWT_VERIFICATION_KEY='-----BEGIN PUBLIC KEY-----
MIIBIjANBgkq...
-----END PUBLIC KEY-----'
```

### Step 3: Push environment and redeploy

```sh
./scripts/railway_env.sh
./scripts/railway_redeploy.sh
```

`railway_env.sh` reads `.env.production` and sets each variable on the Railway service. Safe to run repeatedly. Handles multiline values (PEM keys) correctly.

### Production operations

Database scripts must run inside Railway's network (the internal hostname `pgvector.railway.internal` isn't reachable from your local machine). Use SSH to connect to the running container:

```sh
railway ssh --service dash
# Inside the container, after loading source tables:
python scripts/load_knowledge.py
```

Other operations run locally:

```sh
railway logs --service dash
railway open
```

## Why Dash Exists

Ask a question in English, get a correct, meaningful answer. That's the goal. But raw LLMs writing SQL hit a wall fast: schemas lack meaning, types are misleading, tribal knowledge is missing, there's no way to learn from mistakes, and results lack interpretation.

The root cause is missing context and missing memory. Dash solves this with **six layers of grounded context**, a **self-learning loop** that improves with every query, and a focus on delivering insights you can act on.

## Architecture: Five Layers, One System

Agentic software is just software with the business logic replaced by agents. Everything else is systems engineering. Dash is built across five layers that reinforce each other.

```
Agent Engineering     →  dash/team.py + dash/agents/
Data Engineering      →  knowledge/ + Agno Learning Machine + PostgreSQL
Security Engineering  →  AgentOS auth + RBAC + read-only SQL enforcement
Interface Engineering →  app/main.py (FastAPI) + Slack + AgentOS
Infrastructure        →  Dockerfile + compose.yaml + scripts/
```

### 1. Agent Engineering

The agent team and execution flow. Model, instructions, tools, knowledge, and the self-learning loop.

```
AgentOS (app/main.py)  [scheduler=True, tracing=True]
 ├── FastAPI / Uvicorn
 ├── Slack Interface (optional)
 └── Dash Team (dash/team.py, coordinate mode)
     ├─ Analyst (dash/agents/analyst.py)         reads public + dash
     │  ├─ SQLTools (read-only)  → public schema (company data)
     │  ├─ introspect_schema     → both schemas
     │  ├─ save_validated_query  → knowledge base
     │  └─ ReasoningTools
     ├─ Engineer (dash/agents/engineer.py)       reads public, writes dash
     │  ├─ SQLTools (full)       → dash schema (agent-managed)
     │  ├─ introspect_schema     → both schemas
     │  ├─ update_knowledge      → knowledge base (schema changes)
     │  └─ ReasoningTools
     │
     Leader tools: SlackTools (optional)
     Knowledge:    dash_knowledge (table schemas, queries, business rules, dash views)
     Learnings:    dash_learnings (error patterns, type gotchas, fixes)
```

### 2. Data Engineering

Context is data. Memory is data. Knowledge is data. All managed with data engineering principles: well-designed schemas, structured querying, databases for fast read/writes.

**Six layers of grounded context:**

| Layer | Purpose | Source |
|------|--------|--------|
| **Table Usage** | Schema, columns, relationships | `knowledge/tables/*.json` |
| **Human Annotations** | Metrics, definitions, business rules | `knowledge/business/*.json` |
| **Query Patterns** | SQL that is known to work | `knowledge/queries/*.sql` |
| **Institutional Knowledge** | Docs, wikis, external references | MCP (optional) |
| **Learnings** | Error patterns and discovered fixes | Agno `Learning Machine` |
| **Runtime Context** | Live schema changes | `introspect_schema` tool |

**The self-learning loop:**

```
User Question
     ↓
Retrieve Knowledge + Learnings
     ↓
Reason about intent
     ↓
Generate grounded SQL
     ↓
Execute and interpret
     ↓
 ┌────┴────┐
 ↓         ↓
Success    Error
 ↓         ↓
 ↓         Diagnose → Fix → Save Learning
 ↓                           (never repeated)
 ↓
Return insight
 ↓
Optionally save as Knowledge
```

Two complementary systems:

| System | Stores | How It Evolves |
|------|--------|----------------|
| **Knowledge** | Validated queries and business context | Curated by you + Dash |
| **Learnings** | Error patterns and fixes | Managed by `Learning Machine` automatically |

**Dual schema enforcement:** A structural boundary between company data and agent-managed data.

| Schema | Owner | Access |
|--------|-------|--------|
| `public` | Company (loaded externally) | Read-only — never modified by agents |
| `dash` | Engineer agent | Views, summary tables, computed data |

The Engineer builds reusable data assets (`dash.mall_store_counts`, `dash.city_store_density`, `dash.category_distribution`) and records them to knowledge. The Analyst discovers and prefers these views over raw table queries.

### 3. Security Engineering

Auth uses RBAC with JWT verification in production. Every query is scoped to `user_id`. Read-only access is a tool configuration, not a prompt instruction. The Analyst agent's SQL tools are scoped to read-only at the system level.

See [Security](#security) for setup details.

### 4. Interface Engineering

One agent definition, multiple surfaces. Dash is reachable via REST API (FastAPI), Slack threads, and the AgentOS web UI. Each surface has its own identity system: a Slack user ID maps to sessions via thread timestamps, the API uses JWT-backed auth.

### 5. Infrastructure Engineering

Dockerfile, Docker Compose, one-command deployment. Scheduled tasks for proactive behavior. The infrastructure layer is boring on purpose. 95% of running an agent is identical to running any other service.

## Slack

Dash can receive Slack DMs, @mentions, and thread replies, and can also post to channels proactively.

Quick setup:
1. Run Dash and give it a public URL (ngrok locally, or your Railway domain).
2. Follow [docs/SLACK_CONNECT.md](docs/SLACK_CONNECT.md) to create and install the Slack app from the manifest.
3. Set `SLACK_TOKEN` and `SLACK_SIGNING_SECRET`, then restart Dash.
4. In Slack, confirm Event Subscriptions is verified and send a DM or `@mention` to test it.

Each Slack thread maps to one Dash session. For the manifest, ngrok commands, Railway deployment, permissions, and troubleshooting, see [docs/SLACK_CONNECT.md](docs/SLACK_CONNECT.md).

## Data Model (Malls and Stores)

Dash expects mall and store source data in the read-only `public` schema:

| Table | Description |
|-------|-------------|
| `malls` | Mall-level reference data: name, district, city, province, address, opening date, developer group, positioning, rating, trade area, and area |
| `stores` | Store-level tenant data: SKU, brand names, category names, mall relationship, and floor |

Key relationship:

```sql
public.stores.mall_id = public.malls.id
```

Known imported dataset shape:

- `public.malls`: 30,494 mall records
- `public.stores`: 404,799 store records
- Every imported store has `mall_id` populated and linked to `malls.id`

## Adding Knowledge

Dash works best when it understands how your organization talks about data.

```
knowledge/
├── tables/      # Table meaning and caveats
├── queries/     # Proven SQL patterns
└── business/    # Metrics and language
```

### Table Metadata

```json
{
  "table_name": "malls",
  "table_description": "Mall-level reference data loaded into public.malls",
  "use_cases": ["Mall coverage analysis", "City rollups", "Store count summaries"],
  "data_quality_notes": [
    "id is unique and is the join target for stores.mall_id",
    "open_date can be NULL when the source does not provide an opening date",
    "derived views and tables belong in the dash schema"
  ]
}
```

### Query Patterns

```sql
-- <query top_malls_by_store_count>
-- <description>Top malls by imported store count</description>
-- <query>
SELECT
    m.id AS mall_id,
    m.name AS mall_name,
    m.city,
    m.province,
    COUNT(*) AS store_count
FROM public.stores s
JOIN public.malls m ON m.id = s.mall_id
GROUP BY m.id, m.name, m.city, m.province
ORDER BY store_count DESC
LIMIT 20;
-- </query>
```

### Business Rules

```json
{
  "metrics": [
    {
      "name": "Store count by mall",
      "definition": "Count stores grouped by their linked mall"
    }
  ],
  "common_gotchas": [
    {
      "issue": "Join key direction",
      "solution": "Join stores to malls with stores.mall_id = malls.id, not stores.id = malls.id"
    }
  ]
}
```

### Load Knowledge

```sh
python scripts/load_knowledge.py            # Upsert changes
python scripts/load_knowledge.py --recreate  # Fresh start
```

## Evaluations

Five eval categories using Agno's eval framework:

| Category | Eval Type | What It Tests |
|----------|-----------|---------------|
| accuracy | AccuracyEval (1-10) | Correct data and meaningful insights |
| routing | ReliabilityEval | Team routes to correct agent/tools |
| security | AgentAsJudgeEval (binary) | No credential or secret leaks |
| governance | AgentAsJudgeEval (binary) | Refuses destructive SQL operations |
| boundaries | AgentAsJudgeEval (binary) | Schema access boundaries respected |

```sh
python -m evals                      # Run all evals
python -m evals --category accuracy  # Run specific category
python -m evals --verbose            # Show response details
```

## Local Development

```sh
./scripts/venv_setup.sh && source .venv/bin/activate
docker compose up -d dash-db
# Load or copy `public.malls` and `public.stores` before this step
python scripts/load_knowledge.py
python -m dash            # CLI mode
python -m app.main        # AgentOS mode (web UI at os.agno.com)
```

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `OPENROUTER_API_KEY` | Yes | — | OpenRouter API key |
| `OPENROUTER_MODEL_ID` | No | `openai/gpt-5.4` | OpenRouter chat/responses model |
| `OPENROUTER_FALLBACK_MODEL_IDS` | No | `""` | Comma-separated fallback model IDs for OpenRouter model routing |
| `OPENROUTER_EMBEDDING_MODEL_ID` | No | `openai/text-embedding-3-small` | OpenRouter embedding model |
| `OPENROUTER_EMBEDDING_DIMENSIONS` | No | `1536` | Embedding vector dimensions |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | OpenRouter OpenAI-compatible API base URL |
| `OPENROUTER_HTTP_REFERER` | No | `""` | Optional OpenRouter attribution URL |
| `OPENROUTER_APP_TITLE` | No | `""` | Optional OpenRouter attribution app title |
| `OPENROUTER_PROVIDER_JSON` | No | `""` | Raw OpenRouter `provider` routing object as JSON |
| `OPENROUTER_PROVIDER_BY_MODEL_JSON` | No | `""` | JSON map of model ID to provider routing overrides |
| `OPENROUTER_PROVIDER_SORT` | No | `""` | Provider sort: `price`, `throughput`, `latency`, or JSON object with `by`/`partition` |
| `OPENROUTER_PROVIDER_ONLY` | No | `""` | Comma-separated provider slugs to allow |
| `OPENROUTER_PROVIDER_ORDER` | No | `""` | Comma-separated provider slugs to try first, in order |
| `OPENROUTER_PROVIDER_IGNORE` | No | `""` | Comma-separated provider slugs to skip |
| `OPENROUTER_PROVIDER_ALLOW_FALLBACKS` | No | `""` | Whether OpenRouter may use backup providers |
| `OPENROUTER_PROVIDER_REQUIRE_PARAMETERS` | No | `""` | Require providers that support every request parameter |
| `OPENROUTER_PROVIDER_DATA_COLLECTION` | No | `""` | `allow` or `deny` providers that may store data |
| `OPENROUTER_PROVIDER_ZDR` | No | `""` | Restrict to Zero Data Retention endpoints |
| `OPENROUTER_PROVIDER_ENFORCE_DISTILLABLE_TEXT` | No | `""` | Restrict to endpoints that allow text distillation |
| `OPENROUTER_PROVIDER_QUANTIZATIONS` | No | `""` | Comma-separated quantization levels, such as `fp16,bf16` |
| `OPENROUTER_PROVIDER_PREFERRED_MIN_THROUGHPUT` | No | `""` | Number or percentile JSON object, such as `{"p90":50}` |
| `OPENROUTER_PROVIDER_PREFERRED_MAX_LATENCY` | No | `""` | Number or percentile JSON object, such as `{"p90":3}` |
| `OPENROUTER_PROVIDER_MAX_PRICE` | No | `""` | JSON price cap, such as `{"prompt":1,"completion":2}` |
| `SLACK_TOKEN` | No | `""` | Slack bot token (interface + tools) |
| `SLACK_SIGNING_SECRET` | No | `""` | Slack signing secret (interface only) |
| `DB_HOST` | No | `localhost` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DB_USER` | No | `ai` | PostgreSQL user |
| `DB_PASS` | No | `ai` | PostgreSQL password |
| `DB_DATABASE` | No | `ai` | PostgreSQL database |
| `PORT` | No | `8000` | API port |
| `RUNTIME_ENV` | No | `prd` | `dev` enables hot reload |
| `AGENTOS_URL` | No | `http://127.0.0.1:8000` | Scheduler callback URL (production) |
| `JWT_VERIFICATION_KEY` | Production | — | RBAC public key from [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=dash&utm_term=agentos) |

### OpenRouter Provider Routing

Dash sends OpenRouter-specific request fields through the OpenAI-compatible SDK `extra_body`, so they apply to the leader, specialists, eval judges, and the self-improvement loop.

Common examples:

```sh
# Prefer the lowest-latency provider for the configured model.
OPENROUTER_PROVIDER_SORT=latency

# Use only a provider group.
OPENROUTER_PROVIDER_ONLY=openai,azure

# Pin provider order and disable fallback outside that order.
OPENROUTER_PROVIDER_ORDER=openai,azure
OPENROUTER_PROVIDER_ALLOW_FALLBACKS=false

# Prefer providers meeting p90 performance thresholds.
OPENROUTER_PROVIDER_SORT=price
OPENROUTER_PROVIDER_PREFERRED_MIN_THROUGHPUT='{"p90":50}'
OPENROUTER_PROVIDER_PREFERRED_MAX_LATENCY='{"p90":3}'
```

For model-specific groups, set `OPENROUTER_PROVIDER_BY_MODEL_JSON`. Exact model IDs override the global provider config; `default` or `*` can provide a fallback entry.

```sh
OPENROUTER_PROVIDER_BY_MODEL_JSON='{
  "openai/gpt-5.4": {"only": ["openai"], "sort": "latency"},
  "anthropic/claude-sonnet-4.5": {"only": ["anthropic"], "allow_fallbacks": false},
  "default": {"sort": "throughput"}
}'
```

## Security

Production deployments require authentication via [Agno AgentOS](https://docs.agno.com/agent-os/security/overview?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=dash&utm_term=security). Dash enables [RBAC authorization](https://docs.agno.com/agent-os/security/rbac?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=dash&utm_term=rbac) when `RUNTIME_ENV=prd` (the default). Without a valid `JWT_VERIFICATION_KEY`, production endpoints will reject all requests.

Local development (`RUNTIME_ENV=dev`, set by Docker Compose) runs without auth so you can iterate freely.

### Auth Setup

See [Deploy to Railway](#deploy-to-railway) for the full setup flow, including how to get your `JWT_VERIFICATION_KEY` from AgentOS. The Agno control plane handles JWT issuance, session management, traces, metrics, and the web UI. See the [AgentOS Security docs](https://docs.agno.com/agent-os/security/overview?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=dash&utm_term=security) for details.

### Schema-Level Enforcement

Beyond API-level auth, Dash enforces data access at the database level:

- **Analyst** connects with `default_transaction_read_only=on` — PostgreSQL rejects any write attempt
- **Engineer** writes are scoped to the `dash` schema — a SQLAlchemy event listener blocks any DDL/DML targeting `public`
- **Leader** has no direct database access

These are infrastructure guardrails, not prompt instructions. They hold regardless of what the model generates.

## Learn More

- [OpenAI's In-House Data Agent](https://openai.com/index/inside-our-in-house-data-agent/) — the inspiration
- [Self-Improving SQL Agent](https://www.ashpreetbedi.com/articles/sql-agent) — deep dive on an earlier architecture
- [Agno Docs](https://docs.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=dash&utm_term=docs)

<p align="center">Built on <a href="https://github.com/agno-agi/agno">Agno</a> · the runtime for agentic software</p>
