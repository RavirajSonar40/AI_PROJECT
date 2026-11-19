# Demo Guide — AI Knowledge & Action Platform

Everything you need to present the project without improvising.
Total duration: 8–12 minutes.

---

## 1. The 30-second pitch

> "This is a knowledge and action platform. You upload your documents, the system turns them
> into vectors, and you can ask questions in plain language. The agent searches your documents,
> cites its sources, calls tools, and **asks for human approval** before doing anything dangerous.
> Everything runs locally: Angular, FastAPI, LangGraph, PostgreSQL with pgvector, and Redis."

---

## 2. Architecture at a glance

```
┌──────────────────────────────────────────────────────────────┐
│  Angular 20  ·  http://localhost:4200                        │
│  Chat + document panel + system status                       │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP / JSON
┌───────────────────────────▼──────────────────────────────────┐
│  FastAPI  ·  http://localhost:8000  ·  /docs (Swagger)       │
│  /documents/upload   /documents/{id}/chunks                  │
│  /documents/{id}/embeddings   /documents/search              │
│  /rag/ask            /agent/ask   /agent/resume              │
└──────────┬───────────────────────────────┬───────────────────┘
           │                               │
┌──────────▼──────────────┐   ┌────────────▼──────────────────┐
│ PostgreSQL 17 + pgvector│   │ Redis 7                       │
│ documents               │   │ embedding cache (3600 s)      │
│ document_chunks         │   │ rate limiting                 │
│ embedding VECTOR(384)   │   └───────────────────────────────┘
│ checkpoints (LangGraph) │
└─────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────┐
│  LLM (Groq · openai/gpt-oss-120b)                            │
│  embeddings: paraphrase-multilingual-MiniLM-L12-v2 (384 d)   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Five-minute pre-demo checklist

```powershell
# 1. Services are up
docker compose ps

# 2. API is healthy
Invoke-RestMethod http://localhost:8000/health/ready

# 3. Frontend
start http://localhost:4200

# 4. Corpus is loaded (should be 18 documents)
(Invoke-RestMethod http://localhost:8000/documents).Count
```

If the corpus is missing: `powershell -File demo/seed-demo.ps1`
If you want a clean slate: `powershell -File demo/reset-demo.ps1`, then the seed.

---

## 4. The demo script (6 steps)

### Step 1 — The system is alive
**Say:** "First we check that the whole infrastructure is responding."
**Do:** open `http://localhost:8000/health/ready`
**You see:**

```json
{"status":"ready","database":"connected","cache":"connected"}
```

> That `ready` means the API is talking to PostgreSQL and Redis — not just that the process is running.

---

### Step 2 — The knowledge is indexed
**Say:** "These 18 documents are the knowledge base: HR, security, support,
billing, product and technical documentation."
**Do:** open `http://localhost:4200` and point at the **Documents** panel.
**You see:** the list of 18 files with their size.

> Each document was split into fragments of 1000 characters with 200 overlap,
> and every fragment was turned into a 384-number vector.

**If you want the technical detail:**

```powershell
Invoke-RestMethod http://localhost:8000/documents/1/chunks | ConvertTo-Json -Depth 4
```

---

### Step 3 — Semantic search (no LLM) ⭐ the "aha" moment
**Say:** "I'll search without calling any language model. Just math."
**Do:**

```powershell
$b = @{ query = "how many vacation days do I have"; limit = 3 } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/documents/search -Method Post -ContentType application/json -Body $b
```

**You see:** 3 fragments ranked by similarity, the best around 0.65–0.70.

> "I didn't look up the word 'vacation' in a text index: I turned the question into a vector
> and searched for the closest vectors. That's why it understands synonyms and typos."

---

### Step 4 — RAG: an answer with sources
**Say:** "Now we do call the model, but we give it the retrieved context."
**Do:** in the chat, type:

> **How many vacation days do I get and how do I request them?**

**You see:** 25 working days (permanent contract), 2.5/month (fixed-term), PeopleHub request
15 calendar days ahead, approval within 5 working days, plus the cited sources.

> "Look at `sources`: the answer doesn't come from the model's memory, it comes from *your*
> documents. Change the document and the answer changes, with no retraining."

---

### Step 5 — The agent chooses tools
**Say:** "The agent doesn't always answer the same way: it picks which tool to use."
**Do:** in the chat, type:

> **What version and environment does this platform run?**

**You see:** `route: system`, `tool_used: get_system_info`, answer "version 0.1.0, environment development".

Then type:

> **According to my documents, what does the health insurance cover and how big is the training budget?**

**You see:** `tool_used: search_knowledge`, `route: knowledge`, an answer with 100%/60% cover,
1,200 € training budget and the 12-month commitment for certifications over 500 €.

> "Nobody told it to call that tool: the model read the question, chose the function
> and passed its arguments as JSON. That's tool calling."

---

### Step 6 — Human approval ⭐ the closer
**Say:** "And if the action is destructive? Here it never runs on its own."
**Do:** in the chat, type:

> **Clear the embedding cache now.**

**You see:** the chat waits for approval (or asks for confirmation).
If the model asks in plain text, reply **"yes, go ahead, call clear_embedding_cache"**.

**You then see:** status `interrupted`, with `action: clear_embedding_cache`.

> "The graph **paused mid-execution** and its state is stored in PostgreSQL.
> I could restart the server and the conversation would still be waiting here.
> No destructive action happens without a person."

To resume through the API:

```powershell
# Approve
$b = @{ thread_id = "demo-approval"; approved = $true; note = "ok" } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/agent/resume -Method Post -ContentType application/json -Body $b
```

> With `approved = false` the agent replies "cancelled by the user" and nothing is deleted.
> That proves control, not just functionality.

---

### Step 7 (optional) — Prove it doesn't make things up
**Say:** "A bad RAG hallucinates. This one admits when it doesn't know."
**Do:** ask **What is the capital of Mongolia?**

**You see:** "I don't have enough information in the available documents to answer that question."
and an empty `sources` list.

> "It preferred not to answer rather than invent. That behaviour is called abstention
> and it matters as much as being correct."

---

## 5. Question bank (verified answers)

| Question | Expected answer | Document |
|---|---|---|
| How many vacation days do I get? | 25 working days (permanent); 2.5/month (fixed-term); +1 day/year from year 5, max 5 | 01 |
| How many days can I work remotely? | 3 remote / 2 office; core hours 10:00–16:00; 40 €/month | 02 |
| How long is the probation period? | 6 months for technical roles, 2 months for others; 15-day notice | 03 |
| What does the health insurance cover? | 100% employee, 60% spouse and children; 2,400 centres; basic dental | 04 |
| How often do I change my password? | No 90-day rotation; minimum 16 characters; MFA mandatory | 05 |
| How fast must a breach be reported? | 72 hours to the authority; SEV1 immediate 24/7 response | 06 |
| What is the SLA for a P1? | 15-minute first response, 4-hour resolution, 24x7 for Enterprise | 07 |
| How long does a refund take? | 30 days to return; 5–10 working days to refund; Basic pays 4.95 € | 08 |
| How much is the Premium plan? | 89 €/month, 10 users, 500 GB; extra user 7 € | 09 |
| How much are Nova Run Elite shoes? | 139 €; 52 units in stock | 10 |
| How are embeddings stored? | VECTOR(384) in pgvector, 1000/200 chunks | 11 |
| What is RAG? | Retrieval plus generation; reduces hallucinations and enables citations | 12 |
| What is an embedding? | A vector representing meaning; compared with cosine similarity | 13 |
| What happens before a dangerous action? | `interrupt` plus human approval; state persisted | 14 |
| How is quality evaluated? | Recall, precision, faithfulness, abstention; 30+ questions | 15 |
| What is a hallucination? | A plausible but invented answer; RAG reduces it | 16 |
| What if /health/ready fails? | Check DB credentials, then Redis connectivity | 17 |
| Do you ship internationally? | Spain, Portugal, France and Italy; 5–8 days | 18 |
| **Cross-document:** SLA vs refund policy? | Compares support response times with the 30-day return window | 07 + 08 |
| **Trap:** Capital of Mongolia? | "I don't have enough information…" | — |

---

## 6. Browser demo (what the audience sees)

1. **System status panel** → API `ready`, PostgreSQL `connected`, Redis `connected`.
2. **Documents panel** → the 18 files.
3. **Chat** → type the vacation question. "YOU" appears, then the answer.
4. **New thread button** → starts a clean conversation (memory is per `thread_id`).
5. **Refresh button** in System status → re-queries `/health/ready`.

> Tip: after each answer the chat shows the `thread_id`.
> That identifier is the conversation's persistent memory in PostgreSQL.

---

## 7. If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `429 Too Many Requests` | 10 queries/minute limit | wait 60 s |
| `503` on `/rag/ask` | LLM provider down or out of credits | check `docker compose logs api` |
| Answers without sources | question outside the corpus | expected: it demonstrates abstention |
| `Document embeddings could not be generated` | Hugging Face cache not writable | `HOME` and `HF_HOME` must point to `data/hf-cache` |
| Frontend shows no data | opened on `127.0.0.1` | open `http://localhost:4200` (CORS) |
| First search is very slow | embedding model download | only happens once |

Live logs:

```powershell
docker compose logs -f api
```

---

## 8. Reset and reload

```powershell
# Wipes documents, chunks, vectors, cache and checkpoints
powershell -NoProfile -ExecutionPolicy Bypass -File demo/reset-demo.ps1

# Re-uploads, chunks and embeds the 18 documents
powershell -NoProfile -ExecutionPolicy Bypass -File demo/seed-demo.ps1

# Automated tour of the 6 steps, with pauses if you add -Pause
powershell -NoProfile -ExecutionPolicy Bypass -File demo/demo-questions.ps1 -Pause
```

---

## 9. Sentences that explain each concept well

- **Chunking** — "We split the document because the model has a limited window.
  Overlap prevents cutting an idea in half."
- **Embedding** — "It's the fingerprint of meaning. Two texts that say the same thing
  have similar vectors even with no words in common."
- **pgvector** — "PostgreSQL with a column type for vectors. Nearest-neighbour search
  becomes an `ORDER BY distance LIMIT k`."
- **RAG** — "Search first, answer second. That way the model doesn't rely on what it memorised."
- **Tool calling** — "The model doesn't execute code: it proposes a call with a name and arguments,
  and the orchestrator decides whether to run it."
- **Human in the loop** — "The graph stops and saves its state. The sensitive action
  waits for a person to say yes or no."
- **Checkpoint** — "The conversation doesn't live in server memory: it lives in PostgreSQL.
  That's why it survives a restart."
- **Abstention** — "If similarity is below the threshold, the system says it doesn't know.
  We prefer 'I don't know' to an invented answer."

---

## 10. Technical facts for audience questions

| Item | Value |
|---|---|
| LLM | `openai/gpt-oss-120b` (Groq) |
| Embedding model | `paraphrase-multilingual-MiniLM-L12-v2` |
| Dimensions | 384 |
| Chunk size / overlap | 1000 / 200 characters |
| Current corpus | 18 documents · 43 chunks |
| Query cache | Redis, 3600 s TTL |
| Rate limit | 10 requests/minute per client |
| Agent recursion limit | 12 steps |
| Max file size | 10 MB (.pdf, .txt, .md) |
| Ports | API 8000 · UI 4200 · PostgreSQL 5434 · Redis 6379 |
