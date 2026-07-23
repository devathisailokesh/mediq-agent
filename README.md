# MediQ Agent

Agentic AI system for medical Q&A using PubMed RAG and Groq LLM.

---

## Architecture

```
User Query
    ↓
[FastAPI Backend]  ←  Pydantic validates input/output
    ↓
[Planner Agent]        — chain-of-thought search strategy
    ↓
[Researcher Agent]     — PubMed RAG (fetch + extract findings)
    ↓
[Summarizer Agent]     — self-critique synthesis
    ↓
[SQLite Memory]        — conversation persistence
    ↓
Streaming JSON Response
```

### Multi-Agent Pipeline

| Agent | Role | Technique |
|-------|------|-----------|
| **Planner** | Converts question → PubMed search queries | Chain-of-thought |
| **Researcher** | Fetches papers, extracts findings | RAG |
| **Summarizer** | Writes final cited answer | Self-critique |

---

## Project Structure

```
mediq-agent/
├── src/
│   ├── agents/
│   │   ├── planner.py       # Planner agent
│   │   ├── researcher.py    # Researcher agent (PubMed RAG)
│   │   └── summarizer.py    # Summarizer agent (self-critique)
│   ├── api/
│   │   ├── main.py          # FastAPI app + router registration
│   │   └── router/
│   │       ├── query.py     # POST /query
│   │       ├── history.py   # GET /history/{session_id}
│   │       └── health.py    # GET /health
│   ├── config/
│   │   └── settings.py      # Pydantic BaseSettings
│   ├── memory/
│   │   └── store.py         # SQLite conversation memory
│   ├── models/
│   │   └── schemas/
│   │       ├── pubmed.py    # PubMedPaper schema
│   │       ├── agent.py     # AgentStep, AgentTrace, SearchPlan
│   │       ├── request.py   # QueryRequest
│   │       └── response.py  # QueryResponse, HealthResponse, etc.
│   ├── prompts/
│   │   └── templates.py     # All system prompts and few-shot examples
│   └── tools/
│       └── pubmed.py        # PubMed E-utilities API client
├── logs/
│   └── logger.py            # Centralised logger (file + console)
├── tests/
│   └── scenarios.json       # 5 evaluation scenarios
├── evaluate.py              # Evaluation script
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/mediq-agent
cd mediq-agent
pip install -r requirements.txt
```

### 2. Create `.env` file

Create a file named `.env` in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
TEMPERATURE=0.1
MAX_TOKENS=2048
MAX_RETRIES=3
RETRY_DELAY=2.0
PUBMED_API_KEY=
PUBMED_MAX_RESULTS=5
DB_PATH=memory.db
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

Get a free Groq API key at: https://console.groq.com

### 3. Run the API

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

---

## Usage

### Ask a medical question

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the latest treatments for Type 2 diabetes?"}'
```

### Get conversation history

```bash
curl http://localhost:8000/history/{session_id}
```

### Health check

```bash
curl http://localhost:8000/health
```

---

## Evaluation

Start the API first, then run:

```bash
python evaluate.py
python evaluate.py --scenarios tests/scenarios.json
```

Results are saved to `logs/evaluation_results.json`.

---

## Docker

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: "3.9"
services:
  mediq-agent:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./memory.db:/app/memory.db
```

### Run with Docker

```bash
docker build -t mediq-agent .
docker run -p 8000:8000 --env-file .env mediq-agent
```

---

## API Keys

| Service | Cost | Required |
|---------|------|----------|
| Groq API | Free | Yes — get at console.groq.com |
| PubMed API | Free | No — optional, improves rate limits |

---

## Test Scenarios

| # | Domain | Question |
|---|--------|----------|
| 1 | Endocrinology | Latest treatments for Type 2 diabetes |
| 2 | Geriatrics | Side effects of metformin in elderly |
| 3 | Infectious Disease | mRNA vaccine efficacy vs Omicron |
| 4 | Cardiology | Hypertension management guidelines |
| 5 | Neuroscience | Sleep deprivation and cognitive function |
