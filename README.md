# MediQ Agent

Agentic AI system for medical Q&A using PubMed RAG and Groq LLM.

Live demo: [mediq-agent.streamlit.app](https://mediq-agent.streamlit.app)

---

## Architecture

Three-agent pipeline:

```
Question
  ↓
[1] PLANNER     → Generates PubMed search queries (chain-of-thought)
  ↓
[2] RESEARCHER  → Fetches papers + extracts findings (RAG)
  ↓
[3] SUMMARIZER  → Synthesizes cited answer (self-critique)
  ↓
Answer + Citations
```

| Agent | Input | Output | Technique |
|---|---|---|---|
| Planner | Question | Search queries | Chain-of-thought reasoning |
| Researcher | Queries | Key findings | PubMed RAG |
| Summarizer | Findings | Final answer | Self-critique verification |

---

## Project Structure

```
mediq-agent/
├── src/
│   ├── agents/              # Planner, Researcher, Summarizer
│   ├── tools/               # PubMed API client
│   ├── prompts/             # System prompts + few-shot examples
│   ├── schemas/             # Input/output validation
│   ├── config/              # Settings (.env)
│   ├── memory/              # SQLite conversation store
│   ├── utils/               # Retry logic
│   ├── api/                 # Optional FastAPI layer
│   └── agent.py             # CLI entry point
├── ui/                      # Streamlit UI
├── tests/
│   └── scenarios.json       # 5 evaluation scenarios
├── evaluate.py              # Evaluation script
├── AGENT_RUN_REPORT.md      # Assessment documentation
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/devathisailokesh/mediq-agent
cd mediq-agent
pip install -r requirements.txt
```

### 2. Create `.env` file

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free Groq API key at: https://console.groq.com

---

## Running the App

### Streamlit UI (primary — no FastAPI needed)

```bash
streamlit run ui/app.py
```

Opens at: http://localhost:8501

---

### CLI (optional)

```bash
python src/agent.py --query "What are the latest treatments for Type 2 diabetes?"
python src/agent.py --query "Side effects of metformin in elderly?" --max-papers 3
python src/agent.py --query "Hypertension guidelines" --output results.json
```

---

## Evaluation

```bash
python evaluate.py
```

Scores on 5 test scenarios. Results saved to `logs/evaluation_results.json`.

---

---

---

## Deployment

Deployed on Streamlit Community Cloud. To deploy your own:
1. Push to GitHub (`.env` is gitignored)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Set main file: `ui/app.py`
4. Add secret: `GROQ_API_KEY = "your_key"`

---

## Prompt Engineering Techniques

| Technique | Where |
|---|---|
| Chain-of-thought | Planner system prompt — step-by-step query generation |
| Few-shot examples | All 3 agent prompts |
| Self-critique | Summarizer — verification checklist before finalizing |
| RAG | Researcher — PubMed abstracts injected into LLM context |
| Structured output | Planner JSON → Pydantic `SearchPlan` validation |

---

## Full Trace & Detailed Results

See **AGENT_RUN_REPORT.md** for:
- Complete agent execution traces
- Evaluation results (5 test scenarios)
- Design decisions & rationale
- Advanced techniques documentation
