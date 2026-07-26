# Design: RAG retrieval in the AI chat (task #7)

**Date:** 2026-07-26
**Status:** Approved
**Branch:** `feat/rag-chat-retrieval`
**Sheet task:** #7 — *"RAG truy vấn: POST /chat/messages — embedding câu hỏi → hybrid search
(cosine + trgm) → top-k → prompt LLM → sinh câu trả lời. Lưu chat_messages + message_citations."*

## 1. Goal

`/chat/messages` today answers only from the user's health profile. This adds **retrieval**:
the question is embedded, matched against approved knowledge in `doc_chunks`, and the best
passages are injected into the prompt — with the sources returned to the UI as citations and
persisted to `message_citations`.

Task #6 (ingest) and #8 (citation UI) are already done, so this closes the gap between them:
`Chat.jsx` already renders a citations list it currently never receives.

## 2. What already exists (verified)

- `doc_chunks(id, document_id, chunk_index, content, token_count, embedding vector(1024), metadata)`.
- Indexes are in place: **HNSW `vector_cosine_ops`** on `embedding`, **GIN `gin_trgm_ops`** on
  `content` (`09_indexes.sql`), and `pg_trgm` is enabled (`01_extensions.sql`).
- `message_citations(message_id, chunk_id, score, rank)`.
- `ollama_client.get_embedding()` → bge-m3, 1024-dim, via `/api/embeddings`.
- `indexer.run_indexing_pipeline(doc_id)` runs as a background task when an Expert approves a
  document (`expert.py`).
- `Chat.jsx` reads each citation as `{title|source|name, url|link, snippet|excerpt}` and reads
  `citations` off both the POST reply **and** each history message.

## 3. Decisions

- **Hybrid ranking — weighted sum in one SQL query:**
  `score = 0.7 · (1 − (embedding <=> :qvec)) + 0.3 · similarity(content, :q)`
  Both terms land in 0..1, so the blend is meaningful; one round-trip; both indexes used.
  (Alternative considered: Reciprocal Rank Fusion — more robust to score-scale mismatch, but
  two queries and harder to explain. Revisit if ranking looks skewed.)
- **top-k = 5**, with a relevance floor so weak matches are dropped rather than padded in.
- **No relevant chunk → answer anyway** from the existing profile grounding, with
  `citations: []`. The assistant must stay useful for everyday questions ("Tối nay ăn gì?")
  that no document will ever cover.
- **Retrieval never breaks chat.** If embedding fails (bge-m3 missing, Ollama down) or the
  knowledge base is empty, log and continue without context.

## 4. Components

### `app/services/retrieval.py` (new)

```python
@dataclass
class Hit:
    chunk_id: int
    content: str
    score: float
    doc_title: str
    source_url: str | None

def search_chunks(db, query: str, k: int = 5) -> list[Hit]
def render_context_block(hits: list[Hit]) -> str   # pure → unit-testable
```

`search_chunks` embeds the query, runs the hybrid SQL joined to `documents` (only
`status='APPROVED'`, `deleted_at IS NULL`), and returns hits above the floor. On `OllamaError`
it logs and returns `[]`.

`render_context_block` formats hits as a numbered Vietnamese block (`[1] <title> — <content>`)
and returns `""` for no hits, so the caller needs no branching.

### `app/routers/chat.py` (edit)

```
POST /chat/messages
  auth → session → save user message                      (unchanged)
  hits = search_chunks(db, message, k=5)                   NEW
  system = build_system_prompt(db, user)                   (unchanged)
           + render_context_block(hits)                    NEW
  reply = ollama_client.chat([...])                        (unchanged)
  save assistant message                                   (unchanged)
  insert message_citations(message_id, chunk_id, score, rank=i+1)   NEW
  return { reply, citations: [...] }                       NEW
```

`GET /chat/messages` additionally loads citations per assistant message
(`message_citations` → `doc_chunks` → `documents`), so sources survive a page refresh.

### `app/schemas.py` (edit)

```python
class CitationOut(BaseModel):        # shape mandated by Chat.jsx
    title: str
    url: str | None = None
    snippet: str | None = None

class ChatReplyOut(BaseModel):
    reply: str
    citations: list[CitationOut] = []

class ChatMessageOut(BaseModel):     # + citations for history
    ...
    citations: list[CitationOut] = []
```

`snippet` is the chunk content truncated (~200 chars) — the UI shows it as a preview.

## 5. Error handling

| Situation | Behavior |
|---|---|
| Embedding fails / Ollama down | Log warning, `search_chunks` → `[]`, answer without context, `citations: []` |
| `doc_chunks` empty or no chunk clears the floor | Same as above — profile-grounded answer |
| Chunk row has `embedding IS NULL` | Excluded by the SQL (indexer tolerates failed embeddings) |
| LLM call fails | Existing 503 path, unchanged; user message stays saved |

## 6. Testing

- **Unit — `render_context_block`:** numbered block with hits; empty string with none.
- **Integration — `search_chunks`:** insert a document + chunk with a known embedding,
  monkeypatch `get_embedding`, assert the chunk is found and ranked. Skips without Postgres.
- **Integration — embedding failure:** `get_embedding` raising → `search_chunks` returns `[]`
  and does not propagate.
- **Router:** monkeypatch `search_chunks` and `ollama_client.chat` → assert the reply carries
  citations, `message_citations` rows are written with rank/score, and `GET /chat/messages`
  returns citations on the assistant message.
- **Manual:** index the seeded documents, ask a question they cover, confirm citations render
  in the UI and survive a refresh.

## 7. Prerequisites

1. `ollama pull bge-m3` (~1.2 GB) — embeddings are 1024-dim and the column is fixed at that size.
2. Ollama running.
3. `doc_chunks` populated — approve the seeded documents so the indexer runs.

## 8. Out of scope

Task #9 (country drug rules in RAG), cross-encoder reranking, streaming responses, and
multi-session chat. Ranking weights are constants in code, not settings.
