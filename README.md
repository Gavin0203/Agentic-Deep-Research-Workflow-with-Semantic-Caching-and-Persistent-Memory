# Deep Research Agent: Agentic Deep Research Workflow with Semantic Caching and Persistent Memory

A production-style research assistant built with LangGraph, Redis, and LLM orchestration. This project is designed to answer complex questions by breaking them into sub-questions, checking whether the answer is already available in a semantic cache, researching missing pieces, evaluating research quality, and then synthesizing a final response.

The system is built to be both efficient and explainable: it reduces duplicate work through caching, preserves short-term conversational state through Redis-backed memory, and uses conditional loops so the agent can keep improving a weak answer instead of stopping prematurely.

---

## Start the Docker container for cache and short-term memory

This project uses Redis both for semantic caching and for LangGraph short-term memory persistence. To keep that data durable across restarts, start Redis Stack with a Docker volume:

```bash
docker run -d --name redis -p 6379:6379 redis:<version>
```

Then configure the environment:

```bash
export REDIS_URL=redis://localhost:6379
export OPENAI_API_KEY=your_openai_key_here
export TAVILY_API_KEY=your_tavilly_key_here
```

This gives the project a persistent Redis layer for:

- semantic cache lookups
- agent short-term memory
- workflow checkpointing / state continuity

---

## Project overview

This repository implements an agentic research workflow that handles multi-part questions more intelligently than a single LLM call.

Instead of sending a broad question to an LLM and hoping for a complete answer, the system:

1. decomposes the original question into smaller, cacheable sub-questions
2. checks Redis for semantic matches with a vector-based cache
3. only researches the questions that do not already have valid answers in the Cache
4. evaluates answer quality against a threshold
5. loops back into research when the quality is weak
6. synthesizes a final response from all validated sub-answers

This makes the workflow more cost-aware, more reliable, and better suited for production scenarios such as customer support, internal knowledge retrieval, or research copilots.

---

## Core techniques used

### 1. Research orchestration
The workflow is built as a LangGraph state machine. Each node represents a distinct stage of the intelligent process:

- query decomposition
- cache lookup
- research execution
- quality evaluation
- final synthesis

This keeps reasoning modular and traceable, and it makes the workflow easier to debug and extend.

### 2. Query decomposition
Complex prompts are broken into smaller sub-questions before research begins. This has two benefits:

- it reduces hallucination by focusing each step on a narrower task
- it increases cache reuse because the system can match sub-questions individually rather than only on the full original query

The decomposition logic is designed to keep simple queries as one question and split multi-part queries into 2–4 focused sub-questions.

### 3. Semantic caching
The project uses Redis-based semantic caching with vector similarity matching to avoid repeating the same work.

This is implemented via:

- Redis Stack
- RedisVL semantic cache
- Hugging Face embedding vectorization
- confidence-based cache hit detection

If a sub-question has already been answered before, the agent can reuse the cached answer instead of paying for another LLM research round.

### 4. Review and quality evaluation
Not every researched answer is accepted blindly. After the agent researches a missing sub-question, a second evaluation pass reviews the answer quality.

The evaluation step checks whether the answer is strong enough and gives feedback when it is not. This creates a human-like review loop: the system does not simply trust the first research result.

### 5. Conditional looping
This is one of the most important design patterns in the project.

The workflow uses conditional routing to determine whether it should:

- continue researching
- proceed to synthesis
- stop because the result is adequate

The routing logic explicitly checks whether a sub-question has a low quality score and whether the maximum number of retry iterations has been reached. This results in an adaptive loop where weak answers are improved before the final answer is produced.

In other words, the agent is not a single-pass system; it is a review-driven loop designed to self-correct.

### 6. Short-term memory
The project uses LangGraph checkpointing with Redis-backed memory storage. This means the system can preserve conversational or workflow state across turns in a session.

This is particularly valuable for:

- follow-up questions
- multi-turn research workflows
- contextual support interaction
- recovering a workflow state after an interruption

The memory layer is not just for conversation history; it also helps maintain research continuity.

### 7. Cost-aware decision making
This agent is designed to optimize the expensive parts of AI work:

- cache hits reduce repeated embedding and retrieval work
- only missing sub-questions are researched
- repeated quality checks prevent wasted synthesis on weak outputs
- smaller research model usage is separated from analysis/model orchestration

This helps reduce both latency and LLM spending.

### 8. Stateful workflow architecture
The workflow uses a structured state object that tracks:

- original query
- decomposed sub-questions
- cache hit/miss status
- sub-answers
- research iteration counts
- quality scores
- feedback
- execution path
- metrics

This makes the system highly inspectable and ideal for experimentation and iterative improvement.

---

## Architecture and workflow

The application follows this flow:

```text
User Query
   ↓
Decompose question
   ↓
Check semantic cache
   ├─ Cache hit → reuse answer
   └─ Cache miss → research
           ↓
      Quality review
           ├─ Good enough → synthesize
           └─ Weak answer → research again (conditional loop)
                 ↓
            Final answer
```

The core graph is structured in the project files:

- `app.py` – application launcher and workflow assembly
- `agent/nodes.py` – decomposition, cache checking, research, quality evaluation, synthesis
- `agent/edges.py` – routing logic and research-quality loop handling
- `cache/wrapper.py` – Redis semantic cache abstraction
- `cache/config.py` – environment configuration

---

## Repository structure

```text
Redis-Agent/
├── agent/
│   ├── __init__.py
│   ├── demo.py
│   ├── edges.py
│   ├── knowledge_base_utils.py
│   ├── nodes.py
│   └── tools.py
├── cache/
│   ├── __init__.py
│   ├── config.py
│   ├── cross_encoder.py
│   ├── evals.py
│   ├── faq_data_container.py
│   ├── fuzzy_cache.py
│   ├── llm_evaluator.py
│   ├── model_costs.json
│   ├── vis.py
│   └── wrapper.py
├── data/
│   ├── faq_seed.csv
│   └── test_dataset.csv
├── app.py
├── requirements.txt
├── .env
├── test.py
├── test.ipynb
└── README.md
```

---

## Setup and usage

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# or .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 2. Set environment variables

Create a `.env` file (or set the variables in your shell):

```env
OPENAI_API_KEY=your_openai_key_here
REDIS_URL=redis://localhost:6379
CACHE_NAME=semantic-cache
CACHE_DISTANCE_THRESHOLD=0.3
CACHE_TTL_SECONDS=3600
```

### 3. Start Redis

```bash
docker run -d --name redis -p 6379:6379 redis:<version>
```

### 4. Launch the app

```bash
python app.py
```

This launches the Gradio-based interface for the research workflow.

### 5. Ask a complex question

Use the app to ask multi-part or ambiguous questions. The system will:

- break them into smaller sub-questions
- look for cached answers
- research missing information
- evaluate quality
- cycle if needed
- return a final synthesized answer

---

## Example usage flow

A user might ask:

> "How do I troubleshoot slow database performance, and what should I check for indexing, memory pressure, and replication lag?"

The workflow could break this into sub-questions like:

- how do I identify indexing bottlenecks?
- what are the signs of memory pressure?
- how does replication lag affect application latency?

Each sub-question is checked individually in the cache. Only the missing ones are researched, and the agent keeps iterating until the output is strong enough to synthesize.

---

## Why this project stands out

This is not just a chatbot. It is a research pipeline with real engineering patterns:

- semantic retrieval
- Redis persistence
- LLM orchestration
- iterative quality assurance
- stateful workflow execution
- conditional branching and loop control
- memory-aware system design

---

## Troubleshooting

### Redis connection errors
If Redis is not running, start it with the Docker command above. The app expects Redis at `redis://localhost:6379` by default.

### OpenAI API issues
Make sure your `OPENAI_API_KEY` is set correctly before running the workflow.

### Low-quality answers
The workflow is designed to retry and improve weak answers. If results remain weak, consider increasing the `max_research_iterations` value or refining the search logic and prompts.

---

## Closing note

This project brings together several modern AI patterns into a single research agent:

- decomposition for complexity management
- caching for efficiency
- review for quality
- memory for continuity
- conditional loops for improvement
- synthesis for final delivery

It is a strong example of how to build an agentic system that feels intelligent, efficient, and operationally aware.
