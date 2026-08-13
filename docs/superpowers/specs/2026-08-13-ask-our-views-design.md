# "Ask Our Views" — RAG over the ATU newsletter archive

## Problem

The frameworks site answers "what mental model applies to X" but not "what have Pranay and RSJ actually argued about X." Over five years and 1000+ newsletter sections (across ~390+ editions of *Anticipating the Unintended*), the two authors have written substantive, sometimes divergent, views on a huge range of public policy questions. A public-policy enthusiast asking "how do I think about rent control?" currently has no way to surface that accumulated view — they'd have to search Substack manually and read entire editions to find the relevant section.

## Goal

A public-facing feature on the frameworks site where a visitor asks a question in plain language and gets back the relevant passages from the newsletter archive — grouped by author, so that Pranay's and RSJ's views are shown separately (including where they disagree), each traceable to the original post.

## Non-goals

- Not a chatbot / conversational interface — single question, single structured answer.
- Not a general-purpose summarizer of "what does the internet think about X" — scoped strictly to the ATU corpus.
- Not attempting to resolve or average disagreements between the two authors — showing the disagreement is a feature, not a bug to fix.
- Not including guest-authored sections (Ameya Naik, Khyati Pathak, Bibhudatta Pani, etc.) — this tool answers "what do Pranay and RSJ think," not "what has anyone on the newsletter said."
- Not reproducing paywalled content concerns — moot, since all ATU posts are public.

## Grounding strategy: extractive-first (Option B)

The system does not generate free-form synthesized opinions. For each matched author group, it:

1. Retrieves the most relevant original excerpts verbatim.
2. Optionally adds one short, tightly-grounded connector line per group (LLM-generated, but constrained to paraphrase only what's in the retrieved excerpts — never adding outside claims).
3. Always shows the actual excerpt text and a link to the source post, so a reader can verify any connector line against the source in one glance.

This trades "impressive flowing prose" for trustworthiness: the tool should never sound more confident about "our view" than the underlying five years of writing actually is, and should never blend Pranay's and RSJ's positions into a single voice.

## Architecture

```
Quarto site (static, GitHub Pages)          Python API (Render, free tier)         Free LLM API
┌──────────────────────┐                    ┌──────────────────────────┐          ┌─────────────────┐
│ ask.qmd + ask.js       │ ── POST /ask ───▶ │ FastAPI                   │ ──────▶  │ Groq / NVIDIA    │
│ (same pattern as       │ ◀── JSON ──────── │  - loads chunks.json +    │ ◀──────  │ NIM (free tier)  │
│  existing finder.js)   │                    │    vectors.npy at startup │          └─────────────────┘
└──────────────────────┘                    │  - cosine similarity      │
                                              │  - per-author grouping    │
                                              │  - rate limiting + cache  │
                                              └──────────────────────────┘
                                                        ▲
                                                        │ reads (checked into repo)
                                              ┌──────────────────────────┐
                                              │ chunks.json + vectors.npy │
                                              │ built offline by a        │
                                              │ separate indexing script  │
                                              └──────────────────────────┘
```

The static Quarto site is unaffected except for one new page. The RAG logic lives entirely in a new, separately deployed Python service.

## Data pipeline (offline, rerun periodically)

1. **Sync** — reuse existing `scripts/sync-substack-db.py` (already works; keeps `~/.claude/data/substack-atu.db` current).
2. **Section-split + attribute** — new script `scripts/build-ask-index.py`:
   - Splits each post's `body_text` into sections using ATU's recurring structural markers and the trailing em-dash signatures (`—RSJ`, `—Pranay Kotasthane`, `—Raghu Sanjaylal Jaitley`).
   - Attribution rule (best-effort, no manual review queue):
     - Signature matches RSJ / Raghu Sanjaylal Jaitley → `author: "RSJ"`.
     - Signature matches Pranay Kotasthane → `author: "Pranay"`.
     - No signature / blank → `author: "Joint"` (both wrote it).
     - Any other named signature (Ameya Naik, Khyati Pathak, Bibhudatta Pani, etc.) → chunk is **dropped** from the corpus.
   - Output per chunk: `{id, author, post_title, post_url, date, section_text}`.
3. **Embed** — each chunk embedded with a free local model (`sentence-transformers/all-MiniLM-L6-v2`, CPU, no API cost, run once per rebuild).
4. **Artifacts** — `chunks.json` (text + metadata) and `vectors.npy` (embedding matrix), checked into the backend repo, rebuilt on the same cadence as the existing Substack sync (manually triggered for now; can be scheduled later).

## Retrieval + API

- `POST /ask {question: str}`.
- Embed the question with the same model used for indexing.
- Cosine similarity against `vectors.npy`; take top ~8-10 chunks above a minimum similarity threshold.
- Group surviving chunks by `author` (Pranay / RSJ / Joint).
- If no chunks clear the threshold: return an explicit "we haven't written directly about this" response — never force the LLM to answer from nothing.
- For each non-empty author group: one LLM call to write a short connector line, tightly grounded in that group's excerpts, explicitly allowed to say "this view shifted over time" if the excerpts show a change rather than smoothing it over.
- Response: `{groups: [{author, connector_text, excerpts: [{text, post_title, url, date}]}]}`.
- **Rate limiting**: per-IP cap (e.g. N requests/hour) to protect the free LLM tier from abuse.
- **Caching**: identical/near-duplicate questions served from a short-lived cache (e.g. 24h) to reduce repeat LLM calls.

## Frontend (`ask.qmd` + `scripts/ask.js`)

- New Quarto page, visually consistent with the existing "Find a Framework" widget (same `.finder-box`/input/button pattern, same design language now in `styles.scss`).
- Submits to the backend via `fetch()`, no page reload.
- Renders results as author-labeled cards: connector line, then excerpt quotes, each with a "Read the full piece →" link to the original Substack post.
- Explicit states: loading, no-results ("we haven't written directly about this"), and backend-unavailable/timeout ("this is taking longer than usual — try again shortly") — never an infinite spinner or a silently wrong answer.

## Cost and reliability posture

- Target: near-zero recurring cost using free-tier LLM APIs (Groq or NVIDIA NIM) and a free-tier host (Render) for the backend.
- Explicitly "best-effort": free tiers can rate-limit or change terms; if traffic grows enough to matter, the fallback is a modest paid budget (a few to a few tens of dollars/month), not an architecture change.
- Cold-start delay on a sleeping free-tier backend is an accepted trade-off.

## Open items for the implementation plan

- Exact ATU section-header patterns to split on (needs inspection of a representative sample of posts across years, since formatting has likely drifted over 5 years).
- Choice between Groq and NVIDIA NIM as the primary free LLM provider (pick one, code the fallback path generically).
- Minimum similarity threshold for "no relevant content" (needs empirical tuning against sample questions).
- Render vs. an alternative free host, if Render's free-tier terms turn out to be unsuitable.
