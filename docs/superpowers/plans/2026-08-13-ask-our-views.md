# Ask Our Views Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public "Ask Our Views" feature on the frameworks site — a visitor asks a policy question and gets back real excerpts from the *Anticipating the Unintended* newsletter archive, grouped by author (Pranay / RSJ / Joint), with links to the source posts.

**Architecture:** An offline indexing script splits each newsletter post into per-section chunks (using the ATU section headers and trailing author signatures), embeds each chunk with a free local model, and writes the result to `ask/data/chunks.json` + `ask/data/vectors.npy`. A small FastAPI service (`ask/app.py`) loads that index at startup, and on each `/ask` request does retrieval + author-grouping + a tightly-grounded connector line via a free-tier LLM API. A new static Quarto page (`ask.qmd`) with a vanilla-JS widget calls that API, following the same pattern as the existing `finder.js` widget.

**Tech Stack:** Python 3.11+, FastAPI, `sentence-transformers` (`all-MiniLM-L6-v2`) for embeddings, `numpy` for similarity search, `requests` for calling an OpenAI-compatible free-tier LLM API (Groq by default, swappable via env vars), `pytest` for tests, Render (free tier) for backend hosting. Frontend: vanilla JS matching `scripts/finder.js` conventions, existing `styles.scss` design tokens.

## Global Constraints

- Corpus scope: only sections signed by Pranay Kotasthane, RSJ/Raghu Sanjaylal Jaitley, or unsigned (Joint) sections. Any section signed by another named person (Ameya Naik, Khyati Pathak, Bibhudutta Pani, etc.) is dropped — spec's non-goal is "what do Pranay and RSJ think," not general newsletter content.
- Grounding strategy is extractive-first (spec Option B): the LLM only ever writes a short connector line strictly grounded in retrieved excerpts — never free-form synthesis. Raw excerpts are always shown alongside any connector line.
- No relevant chunks above the similarity threshold → explicit "we haven't written directly about this" response, never a forced answer.
- Cost posture: free-tier LLM API + free-tier host, best-effort reliability, accepted cold-start delays — per spec's "Cost and reliability posture" section.
- Author attribution aliases (best-effort, no manual review queue): `Pranay Kotasthane`, `Pranay Kotashane` (typo variant) → `Pranay`; `RSJ`, `Raghu Sanjaylal Jaitley` → `RSJ`; both present or neither present in an unsigned section → `Joint`; any other name → drop.
- All ATU posts are public — no paywall handling needed.

---

## Decisions locked in during planning (spec's open items resolved)

- **Section headers to split on** (confirmed by frequency analysis of the actual corpus — 151/114/108/76 occurrences respectively across 5 years): `India Policy Watch`, `Global Policy Watch`, `Matsyanyaaya`, `PolicyWTF`/`PolicyWTFs`. Promotional headers (`Course Advertisement`, `Programming Note`, `Advertisement`) are not split targets and are implicitly excluded since only the four content headers are matched.
- **LLM provider**: Groq (OpenAI-compatible `chat/completions` endpoint, `llama-3.3-70b-versatile`), configured via env vars (`LLM_API_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`) so switching to NVIDIA NIM later is a config change, not a code change (both expose OpenAI-compatible APIs).
- **Similarity threshold**: starting value `0.25` (cosine similarity on normalized MiniLM embeddings), exposed as env var `ASK_MIN_SIMILARITY` for later tuning against real questions in Task 11.
- **Host**: Render free tier, deployed from this same repo (`ask/` subdirectory), no `rootDir` override — build/start commands reference the `ask` package from the repo root so internal imports (`from ask.embed import ...`) work identically in local dev, tests, and deployment.

---

### Task 1: Section splitting and author attribution

**Files:**
- Create: `pytest.ini`
- Create: `ask/__init__.py`
- Create: `ask/attribution.py`
- Test: `ask/tests/__init__.py`
- Test: `ask/tests/test_attribution.py`

**Interfaces:**
- Produces: `ask.attribution.split_sections(body_text: str) -> list[dict]`, where each dict has keys `header: str`, `title: str`, `author: str` (one of `"Pranay"`, `"RSJ"`, `"Joint"`), `text: str`.
- Produces: `ask.attribution.classify_signature(sig_text: str) -> str | None` (returns `None` for unrecognized/guest signatures).

- [ ] **Step 1: Create pytest config and package skeleton**

Create `pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = ask/tests
```

Create `ask/__init__.py` (empty file) and `ask/tests/__init__.py` (empty file).

- [ ] **Step 2: Write the failing tests**

Create `ask/tests/test_attribution.py`:

```python
from ask.attribution import split_sections, classify_signature


SAMPLE_BODY = """Some intro text nobody signed, not a real section.

India Policy Watch: Regulating Medical Devices

This is the body of the first section. It needs to be long enough to
clear the minimum length filter, so here is some more filler text
about medical device regulation and unintended consequences that a
policy newsletter section would plausibly contain.

—RSJ

Global Policy Watch: A Second Section

This is the body of the second section, also padded out to be long
enough to survive the minimum length filter used by split_sections,
discussing a completely different global policy topic in some detail.

—Pranay Kotasthane

Matsyanyaaya: A Joint Section

This section has no trailing signature line at all, so it should be
attributed to both authors jointly rather than to either one alone,
and it also needs to be padded to clear the length filter.

PolicyWTF: A Guest Section

This section was written by someone outside the two hosts, so even
though it's long enough to pass the length filter, it should be
dropped entirely because the signature doesn't match either alias set.

—Guest Post by Ameya Naik
"""


def test_classify_signature_pranay():
    assert classify_signature("Pranay Kotasthane") == "Pranay"


def test_classify_signature_pranay_typo():
    assert classify_signature("Pranay Kotashane") == "Pranay"


def test_classify_signature_rsj_short():
    assert classify_signature("RSJ") == "RSJ"


def test_classify_signature_rsj_full_name():
    assert classify_signature("Raghu Sanjaylal Jaitley") == "RSJ"


def test_classify_signature_joint_both_present():
    assert classify_signature("RSJ and Pranay Kotasthane") == "Joint"


def test_classify_signature_guest_returns_none():
    assert classify_signature("Guest Post by Ameya Naik") is None


def test_split_sections_extracts_four_headers_drops_guest():
    sections = split_sections(SAMPLE_BODY)
    headers = [s["header"] for s in sections]
    assert headers == ["India Policy Watch", "Global Policy Watch", "Matsyanyaaya"]


def test_split_sections_assigns_correct_authors():
    sections = split_sections(SAMPLE_BODY)
    by_header = {s["header"]: s for s in sections}
    assert by_header["India Policy Watch"]["author"] == "RSJ"
    assert by_header["Global Policy Watch"]["author"] == "Pranay"
    assert by_header["Matsyanyaaya"]["author"] == "Joint"


def test_split_sections_captures_title_and_text():
    sections = split_sections(SAMPLE_BODY)
    first = sections[0]
    assert first["title"] == "Regulating Medical Devices"
    assert "medical device regulation" in first["text"]
    assert first["text"].strip().endswith("—RSJ")


def test_split_sections_drops_short_sections():
    short_body = "Global Policy Watch: Too Short\n\nJust a line.\n\n—RSJ\n"
    assert split_sections(short_body) == []


def test_split_sections_no_headers_returns_empty():
    assert split_sections("Just a plain newsletter intro with no section headers at all.") == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest ask/tests/test_attribution.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ask.attribution'`

- [ ] **Step 4: Implement `ask/attribution.py`**

```python
from __future__ import annotations

import re

SECTION_HEADER_PATTERN = re.compile(
    r"(India Policy Watch|Global Policy Watch|Matsyanyaaya|PolicyWTFs?):\s*([^\n]*)"
)

SIGNATURE_PATTERN = re.compile(r"^[—-]\s*([A-Z][A-Za-z .]{2,60})\s*$", re.MULTILINE)

MIN_SECTION_LENGTH = 100

PRANAY_ALIASES = ("pranay kotasthane", "pranay kotashane")
RSJ_ALIASES = ("rsj", "raghu sanjaylal jaitley")


def classify_signature(sig_text: str) -> str | None:
    """Classify a signature line into 'Pranay', 'RSJ', 'Joint', or None (drop)."""
    s = sig_text.lower()
    has_pranay = any(alias in s for alias in PRANAY_ALIASES)
    has_rsj = any(alias in s for alias in RSJ_ALIASES)
    if has_pranay and has_rsj:
        return "Joint"
    if has_pranay:
        return "Pranay"
    if has_rsj:
        return "RSJ"
    return None


def split_sections(body_text: str) -> list[dict]:
    """Split a post body into ATU sections, tagging each with its author.

    Only the four recurring ATU section headers are treated as split points
    (India Policy Watch, Global Policy Watch, Matsyanyaaya, PolicyWTF/s).
    Sections signed by someone other than Pranay or RSJ are dropped, as are
    sections under the minimum length (mostly empty/junk sections).
    """
    matches = list(SECTION_HEADER_PATTERN.finditer(body_text))
    sections = []
    for i, m in enumerate(matches):
        header_name = m.group(1)
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body_text)
        section_text = body_text[start:end].strip()

        if len(section_text) < MIN_SECTION_LENGTH:
            continue

        sig_matches = SIGNATURE_PATTERN.findall(section_text)
        author = classify_signature(sig_matches[-1]) if sig_matches else "Joint"
        if author is None:
            continue

        sections.append(
            {
                "header": header_name,
                "title": title,
                "author": author,
                "text": section_text,
            }
        )
    return sections
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest ask/tests/test_attribution.py -v`
Expected: PASS (10 tests)

- [ ] **Step 6: Commit**

```bash
git add pytest.ini ask/__init__.py ask/tests/__init__.py ask/attribution.py ask/tests/test_attribution.py
git commit -m "feat(ask): add section-splitting and author attribution"
```

---

### Task 2: Build chunks from the Substack database

**Files:**
- Create: `ask/build_index.py`
- Test: `ask/tests/test_build_index.py`

**Interfaces:**
- Consumes: `ask.attribution.split_sections(body_text: str) -> list[dict]` (Task 1).
- Produces: `ask.build_index.chunks_from_db(db_path: str) -> list[dict]`, each dict with keys `id`, `author`, `post_title`, `post_url`, `date`, `header`, `section_title`, `text`.

- [ ] **Step 1: Write the failing test**

Create `ask/tests/test_build_index.py`:

```python
import sqlite3

import pytest

from ask.build_index import chunks_from_db


@pytest.fixture
def sample_db(tmp_path):
    db_path = tmp_path / "sample.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            url TEXT NOT NULL,
            body_text TEXT NOT NULL
        )
        """
    )
    body_one = (
        "India Policy Watch: Rent Control Revisited\n\n"
        "Rent control tends to reduce housing supply over the long run, and "
        "this section spends several sentences padding out the argument so "
        "that it clears the minimum section length filter used upstream.\n\n"
        "—Pranay Kotasthane\n"
    )
    body_two = (
        "PolicyWTF: A Guest Rant\n\n"
        "This section is written by someone outside the two hosts and should "
        "be dropped even though it is long enough to pass the length filter "
        "on its own, because the signature does not match either alias set.\n\n"
        "—Guest Post by Khyati Pathak\n"
    )
    conn.execute(
        "INSERT INTO posts (title, date, url, body_text) VALUES (?, ?, ?, ?)",
        ("Edition One", "2024-01-01", "https://example.com/one", body_one),
    )
    conn.execute(
        "INSERT INTO posts (title, date, url, body_text) VALUES (?, ?, ?, ?)",
        ("Edition Two", "2024-01-08", "https://example.com/two", body_two),
    )
    conn.commit()
    conn.close()
    return str(db_path)


def test_chunks_from_db_extracts_signed_section(sample_db):
    chunks = chunks_from_db(sample_db)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["author"] == "Pranay"
    assert chunk["post_title"] == "Edition One"
    assert chunk["post_url"] == "https://example.com/one"
    assert chunk["date"] == "2024-01-01"
    assert chunk["header"] == "India Policy Watch"
    assert chunk["section_title"] == "Rent Control Revisited"
    assert "Rent control" in chunk["text"]


def test_chunks_from_db_has_stable_unique_ids(sample_db):
    chunks_a = chunks_from_db(sample_db)
    chunks_b = chunks_from_db(sample_db)
    assert chunks_a[0]["id"] == chunks_b[0]["id"]
    assert len(chunks_a[0]["id"]) > 0


def test_chunks_from_db_drops_guest_sections(sample_db):
    chunks = chunks_from_db(sample_db)
    headers = [c["header"] for c in chunks]
    assert "PolicyWTF" not in headers
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest ask/tests/test_build_index.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ask.build_index'`

- [ ] **Step 3: Implement `ask/build_index.py`**

```python
from __future__ import annotations

import hashlib
import sqlite3

from ask.attribution import split_sections


def chunks_from_db(db_path: str) -> list[dict]:
    """Read all posts from the Substack sync database and split into
    author-attributed chunks, dropping guest-authored sections."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT title, date, url, body_text FROM posts").fetchall()
    finally:
        conn.close()

    chunks: list[dict] = []
    for title, date, url, body_text in rows:
        for i, section in enumerate(split_sections(body_text)):
            chunk_id = hashlib.sha1(
                f"{url}|{section['header']}|{i}".encode("utf-8")
            ).hexdigest()[:12]
            chunks.append(
                {
                    "id": chunk_id,
                    "author": section["author"],
                    "post_title": title,
                    "post_url": url,
                    "date": date,
                    "header": section["header"],
                    "section_title": section["title"],
                    "text": section["text"],
                }
            )
    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest ask/tests/test_build_index.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add ask/build_index.py ask/tests/test_build_index.py
git commit -m "feat(ask): build author-attributed chunks from the Substack database"
```

---

### Task 3: Embeddings and the index-building CLI

**Files:**
- Create: `ask/embed.py`
- Modify: `ask/build_index.py`
- Create: `scripts/build_ask_index.py`
- Test: `ask/tests/test_embed.py`
- Test: `ask/tests/test_build_index.py` (add one test)

**Interfaces:**
- Consumes: `ask.build_index.chunks_from_db(db_path: str) -> list[dict]` (Task 2).
- Produces: `ask.embed.embed_texts(texts: list[str]) -> np.ndarray` (shape `(len(texts), 384)`, L2-normalized rows).
- Produces: `ask.build_index.build_and_save(db_path: str, chunks_out_path: str, vectors_out_path: str) -> int` (returns chunk count).

- [ ] **Step 1: Write the failing embedding test**

Create `ask/tests/test_embed.py`:

```python
import numpy as np

from ask.embed import embed_texts


def test_embed_texts_returns_correct_shape():
    vectors = embed_texts(["rent control policy", "semiconductor export controls"])
    assert vectors.shape == (2, 384)


def test_embed_texts_identical_strings_are_near_identical():
    vectors = embed_texts(["rent control reduces housing supply", "rent control reduces housing supply"])
    similarity = float(np.dot(vectors[0], vectors[1]))
    assert similarity > 0.99


def test_embed_texts_unrelated_strings_are_less_similar_than_identical():
    vectors = embed_texts(["rent control reduces housing supply", "GPU export controls to China"])
    same_topic = embed_texts(["rent control reduces housing supply", "rent caps distort the rental market"])
    unrelated_similarity = float(np.dot(vectors[0], vectors[1]))
    same_topic_similarity = float(np.dot(same_topic[0], same_topic[1]))
    assert same_topic_similarity > unrelated_similarity
```

Note: this test downloads the `all-MiniLM-L6-v2` model weights (~80MB) on first run — needs internet access once; cached locally afterwards (`~/.cache/torch/sentence_transformers`).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest ask/tests/test_embed.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ask.embed'`

- [ ] **Step 3: Implement `ask/embed.py`**

```python
from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of strings into L2-normalized vectors, one row per text."""
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    model = get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vectors, dtype=np.float32)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest ask/tests/test_embed.py -v`
Expected: PASS (3 tests) — first run will pause to download model weights.

- [ ] **Step 5: Write the failing test for `build_and_save`**

Add to `ask/tests/test_build_index.py`:

```python
import json

import numpy as np

from ask.build_index import build_and_save


def test_build_and_save_writes_chunks_and_vectors(sample_db, tmp_path, monkeypatch):
    def fake_embed_texts(texts):
        return np.ones((len(texts), 4), dtype=np.float32)

    monkeypatch.setattr("ask.build_index.embed_texts", fake_embed_texts)

    chunks_out = tmp_path / "chunks.json"
    vectors_out = tmp_path / "vectors.npy"
    count = build_and_save(sample_db, str(chunks_out), str(vectors_out))

    assert count == 1
    saved_chunks = json.loads(chunks_out.read_text())
    assert len(saved_chunks) == 1
    saved_vectors = np.load(vectors_out)
    assert saved_vectors.shape == (1, 4)
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest ask/tests/test_build_index.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_and_save'`

- [ ] **Step 7: Add `build_and_save` to `ask/build_index.py`**

Add these lines to the top of `ask/build_index.py` (alongside the existing imports):

```python
import json

import numpy as np

from ask.embed import embed_texts
```

Add this function at the end of `ask/build_index.py`:

```python
def build_and_save(db_path: str, chunks_out_path: str, vectors_out_path: str) -> int:
    """Build chunks from the database, embed them, and write both artifacts to disk."""
    chunks = chunks_from_db(db_path)
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)

    with open(chunks_out_path, "w") as f:
        json.dump(chunks, f)
    np.save(vectors_out_path, vectors)

    return len(chunks)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest ask/tests/test_build_index.py ask/tests/test_embed.py -v`
Expected: PASS (7 tests total)

- [ ] **Step 9: Create the CLI wrapper**

Create `scripts/build_ask_index.py`:

```python
#!/usr/bin/env python3
"""Build the Ask Our Views retrieval index from the Substack sync database.

Usage:
    python3 scripts/build_ask_index.py
    python3 scripts/build_ask_index.py --db /path/to/substack-atu.db
"""
from __future__ import annotations

import argparse
import os

from ask.build_index import build_and_save

DEFAULT_DB_PATH = os.path.expanduser("~/.claude/data/substack-atu.db")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to substack-atu.db")
    parser.add_argument("--chunks-out", default="ask/data/chunks.json")
    parser.add_argument("--vectors-out", default="ask/data/vectors.npy")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.chunks_out) or ".", exist_ok=True)
    count = build_and_save(args.db, args.chunks_out, args.vectors_out)
    print(f"Wrote {count} chunks to {args.chunks_out} and {args.vectors_out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 10: Commit**

```bash
git add ask/embed.py ask/build_index.py ask/tests/test_embed.py ask/tests/test_build_index.py scripts/build_ask_index.py
git commit -m "feat(ask): add embeddings and the index-building CLI"
```

---

### Task 4: Retrieval — similarity search and author grouping

**Files:**
- Create: `ask/retrieval.py`
- Test: `ask/tests/test_retrieval.py`

**Interfaces:**
- Produces: `ask.retrieval.load_index(chunks_path: str, vectors_path: str) -> tuple[list[dict], np.ndarray]`.
- Produces: `ask.retrieval.search(query_vector: np.ndarray, vectors: np.ndarray, top_k: int, min_similarity: float) -> list[tuple[int, float]]` (list of `(chunk_index, similarity_score)`, best first).
- Produces: `ask.retrieval.group_by_author(chunks: list[dict], matches: list[tuple[int, float]]) -> dict[str, list[dict]]` (each chunk dict gets a `"score"` key added).

- [ ] **Step 1: Write the failing tests**

Create `ask/tests/test_retrieval.py`:

```python
import json

import numpy as np

from ask.retrieval import group_by_author, load_index, search


def test_search_returns_best_matches_above_threshold():
    query = np.array([1.0, 0.0], dtype=np.float32)
    vectors = np.array(
        [
            [1.0, 0.0],   # perfect match
            [0.0, 1.0],   # orthogonal, similarity 0
            [0.9, 0.1],   # close match
        ],
        dtype=np.float32,
    )
    results = search(query, vectors, top_k=10, min_similarity=0.5)
    indices = [i for i, _score in results]
    assert indices[0] == 0
    assert 1 not in indices  # below threshold, excluded


def test_search_respects_top_k():
    query = np.array([1.0, 0.0], dtype=np.float32)
    vectors = np.array([[1.0, 0.0], [0.95, 0.05], [0.9, 0.1]], dtype=np.float32)
    results = search(query, vectors, top_k=2, min_similarity=0.0)
    assert len(results) == 2


def test_group_by_author_buckets_correctly():
    chunks = [
        {"id": "a", "author": "Pranay", "text": "one"},
        {"id": "b", "author": "RSJ", "text": "two"},
        {"id": "c", "author": "Pranay", "text": "three"},
    ]
    matches = [(0, 0.9), (1, 0.8), (2, 0.7)]
    groups = group_by_author(chunks, matches)
    assert set(groups.keys()) == {"Pranay", "RSJ"}
    assert len(groups["Pranay"]) == 2
    assert groups["Pranay"][0]["score"] == 0.9


def test_load_index_reads_chunks_and_vectors(tmp_path):
    chunks_path = tmp_path / "chunks.json"
    vectors_path = tmp_path / "vectors.npy"
    chunks_path.write_text(json.dumps([{"id": "a", "author": "Pranay", "text": "x"}]))
    np.save(vectors_path, np.ones((1, 4), dtype=np.float32))

    chunks, vectors = load_index(str(chunks_path), str(vectors_path))
    assert chunks == [{"id": "a", "author": "Pranay", "text": "x"}]
    assert vectors.shape == (1, 4)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ask/tests/test_retrieval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ask.retrieval'`

- [ ] **Step 3: Implement `ask/retrieval.py`**

```python
from __future__ import annotations

import json

import numpy as np


def load_index(chunks_path: str, vectors_path: str) -> tuple[list[dict], np.ndarray]:
    with open(chunks_path) as f:
        chunks = json.load(f)
    vectors = np.load(vectors_path)
    return chunks, vectors


def search(
    query_vector: np.ndarray,
    vectors: np.ndarray,
    top_k: int = 10,
    min_similarity: float = 0.25,
) -> list[tuple[int, float]]:
    """Return (index, similarity) pairs for the top_k most similar vectors
    that clear min_similarity, best match first."""
    if vectors.shape[0] == 0:
        return []
    sims = vectors @ query_vector
    order = np.argsort(-sims)[:top_k]
    return [(int(i), float(sims[i])) for i in order if sims[i] >= min_similarity]


def group_by_author(chunks: list[dict], matches: list[tuple[int, float]]) -> dict[str, list[dict]]:
    """Group matched chunks by author, attaching each chunk's similarity score."""
    groups: dict[str, list[dict]] = {}
    for idx, score in matches:
        chunk = {**chunks[idx], "score": score}
        groups.setdefault(chunk["author"], []).append(chunk)
    return groups
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ask/tests/test_retrieval.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add ask/retrieval.py ask/tests/test_retrieval.py
git commit -m "feat(ask): add similarity search and author grouping"
```

---

### Task 5: LLM connector text generation

**Files:**
- Create: `ask/llm.py`
- Test: `ask/tests/test_llm.py`

**Interfaces:**
- Produces: `ask.llm.generate_connector(author: str, question: str, excerpts: list[str]) -> str | None` (returns `None` on missing API key or any request failure — caller must handle `None` gracefully, never raises).

- [ ] **Step 1: Write the failing tests**

Create `ask/tests/test_llm.py`:

```python
from unittest.mock import Mock

import pytest

from ask import llm


def test_generate_connector_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "")
    result = llm.generate_connector("Pranay", "what about rent control?", ["excerpt one"])
    assert result is None


def test_generate_connector_returns_stripped_content_on_success(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "fake-key")

    fake_response = Mock()
    fake_response.raise_for_status = Mock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": "  Pranay has argued rent control backfires.  "}}]
    }

    def fake_post(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(llm.requests, "post", fake_post)

    result = llm.generate_connector("Pranay", "what about rent control?", ["excerpt one"])
    assert result == "Pranay has argued rent control backfires."


def test_generate_connector_returns_none_on_request_exception(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "fake-key")

    def fake_post(*args, **kwargs):
        raise llm.requests.RequestException("network error")

    monkeypatch.setattr(llm.requests, "post", fake_post)

    result = llm.generate_connector("Pranay", "what about rent control?", ["excerpt one"])
    assert result is None


def test_generate_connector_does_not_call_api_without_key(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("requests.post should not be called without an API key")

    monkeypatch.setattr(llm.requests, "post", fail_if_called)

    llm.generate_connector("RSJ", "what about rent control?", ["excerpt one"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ask/tests/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ask.llm'`

- [ ] **Step 3: Implement `ask/llm.py`**

```python
from __future__ import annotations

import os

import requests

API_BASE_URL = os.environ.get("LLM_API_BASE_URL", "https://api.groq.com/openai/v1")
API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = (
    "You summarise what a specific author has written, using ONLY the excerpts "
    "given below. Write one or two sentences. Do not add claims, examples, or "
    "reasoning that is not directly present in the excerpts. If the excerpts show "
    "the author's view changing over time, say so explicitly rather than picking one."
)


def generate_connector(author: str, question: str, excerpts: list[str]) -> str | None:
    """Write a short connector line grounded in the given excerpts.

    Returns None if no API key is configured or the request fails for any
    reason — callers must treat None as "show excerpts without a connector
    line," never as an error to surface to the user.
    """
    if not API_KEY:
        return None

    excerpt_block = "\n\n".join(f"- {e}" for e in excerpts)
    user_prompt = (
        f"Question: {question}\n\n"
        f"Excerpts written by {author}:\n{excerpt_block}\n\n"
        f"Write the one-to-two sentence connector line now."
    )

    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 120,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError):
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ask/tests/test_llm.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add ask/llm.py ask/tests/test_llm.py
git commit -m "feat(ask): add grounded LLM connector-text generation"
```

---

### Task 6: Rate limiter

**Files:**
- Create: `ask/ratelimit.py`
- Test: `ask/tests/test_ratelimit.py`

**Interfaces:**
- Produces: `ask.ratelimit.RateLimiter(max_requests: int, window_seconds: float, clock: Callable[[], float] = time.monotonic)` with method `.allow(client_id: str) -> bool`.

- [ ] **Step 1: Write the failing tests**

Create `ask/tests/test_ratelimit.py`:

```python
from ask.ratelimit import RateLimiter


def test_allows_requests_under_the_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60, clock=lambda: 0.0)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True


def test_blocks_requests_over_the_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60, clock=lambda: 0.0)
    limiter.allow("client-a")
    limiter.allow("client-a")
    assert limiter.allow("client-a") is False


def test_different_clients_have_independent_limits():
    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=lambda: 0.0)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-b") is True


def test_old_requests_expire_out_of_the_window():
    times = iter([0.0, 0.0, 61.0])
    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=lambda: next(times))
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False
    assert limiter.allow("client-a") is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ask/tests/test_ratelimit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ask.ratelimit'`

- [ ] **Step 3: Implement `ask/ratelimit.py`**

```python
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable


class RateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, client_id: str) -> bool:
        now = self._clock()
        hits = self._hits[client_id]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ask/tests/test_ratelimit.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add ask/ratelimit.py ask/tests/test_ratelimit.py
git commit -m "feat(ask): add per-client rate limiter"
```

---

### Task 7: Response cache

**Files:**
- Create: `ask/cache.py`
- Test: `ask/tests/test_cache.py`

**Interfaces:**
- Produces: `ask.cache.TTLCache(ttl_seconds: float, clock: Callable[[], float] = time.monotonic)` with methods `.get(key: str) -> Any | None` and `.set(key: str, value: Any) -> None`.

- [ ] **Step 1: Write the failing tests**

Create `ask/tests/test_cache.py`:

```python
from ask.cache import TTLCache


def test_get_returns_none_for_missing_key():
    cache = TTLCache(ttl_seconds=60, clock=lambda: 0.0)
    assert cache.get("missing") is None


def test_set_then_get_returns_value_within_ttl():
    cache = TTLCache(ttl_seconds=60, clock=lambda: 0.0)
    cache.set("key", {"answer": 42})
    assert cache.get("key") == {"answer": 42}


def test_get_returns_none_after_ttl_expires():
    times = iter([0.0, 0.0, 61.0])
    cache = TTLCache(ttl_seconds=60, clock=lambda: next(times))
    cache.set("key", "value")
    assert cache.get("key") == "value"
    assert cache.get("key") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ask/tests/test_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ask.cache'`

- [ ] **Step 3: Implement `ask/cache.py`**

```python
from __future__ import annotations

import time
from typing import Any, Callable


class TTLCache:
    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (self._clock() + self.ttl_seconds, value)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ask/tests/test_cache.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add ask/cache.py ask/tests/test_cache.py
git commit -m "feat(ask): add TTL response cache"
```

---

### Task 8: FastAPI app — the `/ask` endpoint

**Files:**
- Create: `ask/app.py`
- Test: `ask/tests/test_app.py`

**Interfaces:**
- Consumes: `ask.embed.embed_texts` (Task 3), `ask.retrieval.load_index/search/group_by_author` (Task 4), `ask.llm.generate_connector` (Task 5), `ask.ratelimit.RateLimiter` (Task 6), `ask.cache.TTLCache` (Task 7).
- Produces: FastAPI app instance `ask.app.app` with `POST /ask` accepting `{"question": str}` and returning `{"groups": [{"author": str, "connector_text": str | None, "excerpts": [{"text": str, "post_title": str, "url": str, "date": str}]}], "message": str | None}` or `{"error": str, "message": str}` on rate limiting / empty input.

- [ ] **Step 1: Write the failing tests**

Create `ask/tests/test_app.py`:

```python
import numpy as np
from fastapi.testclient import TestClient

from ask import app as app_module

FAKE_CHUNKS = [
    {
        "id": "a",
        "author": "Pranay",
        "post_title": "Edition One",
        "post_url": "https://example.com/one",
        "date": "2024-01-01",
        "header": "India Policy Watch",
        "section_title": "Rent Control",
        "text": "Rent control tends to reduce housing supply over time.",
    },
    {
        "id": "b",
        "author": "RSJ",
        "post_title": "Edition Two",
        "post_url": "https://example.com/two",
        "date": "2024-02-01",
        "header": "Global Policy Watch",
        "section_title": "Rent Control Elsewhere",
        "text": "Rent control can help incumbent tenants in the short run.",
    },
]
FAKE_VECTORS = np.array([[1.0, 0.0], [0.9, 0.1]], dtype=np.float32)


def make_client(monkeypatch):
    monkeypatch.setattr(app_module, "get_index", lambda: {"chunks": FAKE_CHUNKS, "vectors": FAKE_VECTORS})
    monkeypatch.setattr(app_module, "embed_texts", lambda texts: np.array([[1.0, 0.0]], dtype=np.float32))
    monkeypatch.setattr(app_module, "generate_connector", lambda author, question, excerpts: f"Connector for {author}")
    app_module.rate_limiter = app_module.RateLimiter(max_requests=100, window_seconds=3600)
    app_module.cache = app_module.TTLCache(ttl_seconds=86400)
    return TestClient(app_module.app)


def test_ask_returns_grouped_excerpts(monkeypatch):
    client = make_client(monkeypatch)
    response = client.post("/ask", json={"question": "how should I think about rent control?"})
    assert response.status_code == 200
    body = response.json()
    authors = {g["author"] for g in body["groups"]}
    assert "Pranay" in authors
    assert "RSJ" in authors
    pranay_group = next(g for g in body["groups"] if g["author"] == "Pranay")
    assert pranay_group["connector_text"] == "Connector for Pranay"
    assert pranay_group["excerpts"][0]["url"] == "https://example.com/one"


def test_ask_returns_no_results_message_below_threshold(monkeypatch):
    client = make_client(monkeypatch)
    monkeypatch.setattr(app_module, "MIN_SIMILARITY", 2.0)  # impossible to clear
    response = client.post("/ask", json={"question": "an obscure topic"})
    assert response.status_code == 200
    body = response.json()
    assert body["groups"] == []
    assert "haven't written" in body["message"]


def test_ask_rejects_empty_question(monkeypatch):
    client = make_client(monkeypatch)
    response = client.post("/ask", json={"question": "   "})
    body = response.json()
    assert body["error"] == "empty_question"


def test_ask_enforces_rate_limit(monkeypatch):
    client = make_client(monkeypatch)
    app_module.rate_limiter = app_module.RateLimiter(max_requests=1, window_seconds=3600)
    first = client.post("/ask", json={"question": "rent control"})
    second = client.post("/ask", json={"question": "rent control again"})
    assert first.status_code == 200
    assert second.json()["error"] == "rate_limited"


def test_ask_uses_cache_for_repeated_question(monkeypatch):
    client = make_client(monkeypatch)
    calls = []
    monkeypatch.setattr(
        app_module,
        "generate_connector",
        lambda author, question, excerpts: calls.append(author) or "x",
    )
    client.post("/ask", json={"question": "rent control"})
    client.post("/ask", json={"question": "rent control"})
    # Two authors matched, so a non-cached second call would double the count.
    assert len(calls) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ask/tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ask.app'`

- [ ] **Step 3: Implement `ask/app.py`**

```python
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ask.cache import TTLCache
from ask.embed import embed_texts
from ask.llm import generate_connector
from ask.ratelimit import RateLimiter
from ask.retrieval import group_by_author, load_index, search

CHUNKS_PATH = os.environ.get("ASK_CHUNKS_PATH", "ask/data/chunks.json")
VECTORS_PATH = os.environ.get("ASK_VECTORS_PATH", "ask/data/vectors.npy")
MAX_REQUESTS_PER_HOUR = int(os.environ.get("ASK_RATE_LIMIT", "30"))
CACHE_TTL_SECONDS = int(os.environ.get("ASK_CACHE_TTL", "86400"))
MIN_SIMILARITY = float(os.environ.get("ASK_MIN_SIMILARITY", "0.25"))
TOP_K = int(os.environ.get("ASK_TOP_K", "10"))
ALLOWED_ORIGINS = os.environ.get(
    "ASK_ALLOWED_ORIGINS",
    "https://frameworks.pranaykotas.com,http://localhost:8734,http://127.0.0.1:8734",
).split(",")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST"],
    allow_headers=["*"],
)

rate_limiter = RateLimiter(max_requests=MAX_REQUESTS_PER_HOUR, window_seconds=3600)
cache = TTLCache(ttl_seconds=CACHE_TTL_SECONDS)

_index_cache: dict | None = None


def get_index() -> dict:
    global _index_cache
    if _index_cache is None:
        chunks, vectors = load_index(CHUNKS_PATH, VECTORS_PATH)
        _index_cache = {"chunks": chunks, "vectors": vectors}
    return _index_cache


class AskRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(payload: AskRequest, request: Request):
    client_id = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(client_id):
        return {"error": "rate_limited", "message": "Too many questions right now — try again in a bit."}

    question = payload.question.strip()
    if not question:
        return {"error": "empty_question", "message": "Ask a question first."}

    cache_key = question.lower()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    index = get_index()
    query_vector = embed_texts([question])[0]
    matches = search(query_vector, index["vectors"], top_k=TOP_K, min_similarity=MIN_SIMILARITY)

    if not matches:
        result = {"groups": [], "message": "We haven't written directly about this yet."}
        cache.set(cache_key, result)
        return result

    grouped = group_by_author(index["chunks"], matches)
    groups = []
    for author, items in grouped.items():
        excerpts = [item["text"] for item in items]
        connector = generate_connector(author, question, excerpts)
        groups.append(
            {
                "author": author,
                "connector_text": connector,
                "excerpts": [
                    {
                        "text": item["text"],
                        "post_title": item["post_title"],
                        "url": item["post_url"],
                        "date": item["date"],
                    }
                    for item in items
                ],
            }
        )

    result = {"groups": groups, "message": None}
    cache.set(cache_key, result)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ask/tests/test_app.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full test suite**

Run: `pytest ask/tests -v`
Expected: PASS (all tests across all modules)

- [ ] **Step 6: Commit**

```bash
git add ask/app.py ask/tests/test_app.py
git commit -m "feat(ask): wire retrieval, grouping, LLM connector, rate limit, and cache into /ask"
```

---

### Task 9: Deployment config and real index build

**Files:**
- Create: `ask/requirements.txt`
- Create: `ask/render.yaml`
- Create: `ask/data/chunks.json` (generated artifact)
- Create: `ask/data/vectors.npy` (generated artifact)

**Interfaces:**
- Consumes: `scripts/build_ask_index.py` (Task 3) run against the real `~/.claude/data/substack-atu.db`.

- [ ] **Step 1: Create `ask/requirements.txt`**

```
fastapi
uvicorn[standard]
sentence-transformers
numpy
requests
pydantic
pytest
httpx
```

- [ ] **Step 2: Install dependencies locally**

Run: `pip install -r ask/requirements.txt`
Expected: installs without errors (this also gives `pytest`'s `TestClient` its `httpx` dependency, needed since Task 8).

- [ ] **Step 3: Build the real index**

Run: `python3 scripts/build_ask_index.py`
Expected output: `Wrote <N> chunks to ask/data/chunks.json and ask/data/vectors.npy`, where N is a few hundred to a couple thousand depending on corpus size. This step takes a few minutes (embedding every chunk on CPU).

- [ ] **Step 4: Spot-check the built index**

Run:

```bash
python3 -c "
import json
chunks = json.load(open('ask/data/chunks.json'))
print('total chunks:', len(chunks))
from collections import Counter
print(Counter(c['author'] for c in chunks))
print(chunks[0])
"
```

Expected: a plausible total count, a Counter showing all three of `Pranay`, `RSJ`, `Joint` with non-trivial counts, and a sensible-looking first chunk (real title, real excerpt text, valid URL).

- [ ] **Step 5: Create `ask/render.yaml`**

```yaml
services:
  - type: web
    name: ask-our-views-api
    env: python
    buildCommand: pip install -r ask/requirements.txt
    startCommand: uvicorn ask.app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: LLM_API_KEY
        sync: false
      - key: LLM_API_BASE_URL
        value: https://api.groq.com/openai/v1
      - key: LLM_MODEL
        value: llama-3.3-70b-versatile
```

- [ ] **Step 6: Run the backend locally and smoke-test it**

Run: `uvicorn ask.app:app --reload` (from repo root)

In a second terminal:

```bash
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "how should I think about rent control?"}' | python3 -m json.tool
```

Expected: a JSON response with a `groups` array. Without `LLM_API_KEY` set, `connector_text` will be `null` for every group and excerpts will still be present — this confirms the graceful-degradation path from Task 5 works end-to-end.

- [ ] **Step 7: Commit**

```bash
git add ask/requirements.txt ask/render.yaml ask/data/chunks.json ask/data/vectors.npy
git commit -m "feat(ask): add deploy config and build the production index"
```

Note: `ask/data/vectors.npy` and `chunks.json` are binary/generated artifacts checked into the repo so Render can serve them without re-running the embedding step on every deploy. Rebuilding later (as new newsletter posts come in) means re-running `scripts/build_ask_index.py` and committing the updated files — same rhythm as the existing `sync-substack-db.py` workflow.

---

### Task 10: Frontend widget

**Files:**
- Create: `ask.qmd`
- Create: `scripts/ask.js`
- Modify: `_quarto.yml`
- Modify: `styles.scss`

**Interfaces:**
- Consumes: the deployed `/ask` endpoint (Task 9) — `scripts/ask.js` calls it via `fetch()`.

- [ ] **Step 1: Add the "Ask" nav entry**

In `_quarto.yml`, modify the `navbar.left` list to add an entry right after the existing "Browse" menu item and before "About":

```yaml
  navbar:
    pinned: true
    left:
      - text: "Browse"
        menu:
          - text: "Public Policy"
            href: public-policy/index.qmd
          - text: "Political Thinking"
            href: political-thinking/index.qmd
          - text: "Public Finance"
            href: public-finance/index.qmd
          - text: "Foreign Policy & Geopolitics"
            href: foreign-policy-defence-geopolitics/index.qmd
          - text: "Society"
            href: society/index.qmd
          - text: "Universe"
            href: universe/index.qmd
      - text: "Ask Our Views"
        href: ask.qmd
      - text: "About"
        href: about.qmd
```

- [ ] **Step 2: Create `ask.qmd`**

```markdown
---
title: "Ask Our Views"
summary: "Ask a policy question and see what Pranay and RSJ have written about it."
page-layout: custom
---

::: {.finder-page}

# Ask Our Views

Ask a public policy question in plain language — e.g. "how should I think about rent control?" or "what's the case for congestion pricing?" — and see the actual excerpts Pranay and RSJ have written on it over five years of *Anticipating the Unintended*, grouped by author. When they've disagreed, you'll see both views.

::: {.finder-input-row}
<input type="text" id="ask-input" class="finder-input" placeholder="e.g. how should I think about rent control?" />
<button id="ask-btn" class="finder-btn">Ask</button>
:::

<div id="ask-results" class="finder-results-area"></div>

:::

<script src="scripts/ask.js"></script>
```

- [ ] **Step 3: Create `scripts/ask.js`**

```javascript
/**
 * Ask Our Views — calls the /ask backend and renders author-grouped excerpts.
 * Loaded by ask.qmd via <script src="scripts/ask.js">.
 * Expects these DOM ids: ask-input, ask-btn, ask-results
 */
(function () {
  const API_BASE = 'https://ask-our-views-api.onrender.com';

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  function renderGroup(group) {
    let html = `<div class="ask-group">`;
    html += `<div class="ask-group-author">${escapeHtml(group.author)}</div>`;
    if (group.connector_text) {
      html += `<p class="ask-connector">${escapeHtml(group.connector_text)}</p>`;
    }
    html += `<div class="ask-excerpt-list">`;
    for (const ex of group.excerpts) {
      html += `
        <a href="${escapeHtml(ex.url)}" class="ask-excerpt" target="_blank" rel="noopener">
          <p class="ask-excerpt-text">${escapeHtml(ex.text)}</p>
          <div class="ask-excerpt-source">${escapeHtml(ex.post_title)} · ${escapeHtml(formatDate(ex.date))}</div>
        </a>`;
    }
    html += `</div></div>`;
    return html;
  }

  function render(data) {
    const container = document.getElementById('ask-results');
    if (!container) return;

    if (data.error) {
      container.innerHTML = `<p class="finder-error">${escapeHtml(data.message)}</p>`;
      return;
    }
    if (!data.groups || data.groups.length === 0) {
      container.innerHTML = `<p class="finder-no-results">${escapeHtml(data.message || "We haven't written directly about this yet.")}</p>`;
      return;
    }
    container.innerHTML = data.groups.map(renderGroup).join('');
  }

  function doAsk() {
    const inputEl = document.getElementById('ask-input');
    const container = document.getElementById('ask-results');
    if (!inputEl || !container) return;

    const question = inputEl.value.trim();
    if (!question) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = '<p class="finder-no-results">Searching five years of newsletter archives…</p>';

    fetch(API_BASE + '/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })
      .then(r => r.json())
      .then(render)
      .catch(() => {
        container.innerHTML = '<p class="finder-error">This is taking longer than usual — try again in a moment.</p>';
      });
  }

  function init() {
    const btn = document.getElementById('ask-btn');
    const input = document.getElementById('ask-input');
    if (!btn || !input) return;
    btn.addEventListener('click', doAsk);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doAsk(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

Note: `API_BASE` must be updated after Task 11's deployment if the actual Render service URL differs from `ask-our-views-api.onrender.com` (Render assigns this URL from the `name` field in `render.yaml`; it's deterministic but worth confirming after first deploy).

- [ ] **Step 4: Add styles for the author-grouped result cards**

In `styles.scss`, add this block after the existing `.finder-result-explain` rule (reuses the same design tokens already defined at the top of the file):

```scss
/* ── Ask Our Views ─────────────────────────────────────── */

.ask-group {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid $ink-20;
}

.ask-group-author {
  font-family: $font-family-monospace;
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: $wine;
  margin-bottom: 0.75rem;
}

.ask-connector {
  font-size: 1.05rem;
  color: $ink;
  margin-bottom: 1rem;
  line-height: 1.5;
}

.ask-excerpt-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.ask-excerpt {
  display: block;
  border: 1px solid $ink-20;
  border-radius: 0;
  padding: 1rem 1.25rem;
  text-decoration: none;
  color: inherit;
  transition: background 0.15s ease;

  &:hover {
    background: $deep;
    text-decoration: none;
    color: inherit;
  }
}

.ask-excerpt-text {
  margin: 0 0 0.5rem 0;
  color: $ink-70;
  font-size: 0.95rem;
  line-height: 1.5;
}

.ask-excerpt-source {
  font-family: $font-family-monospace;
  font-size: 10.5px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: $ink-50;
}
```

- [ ] **Step 5: Render the new page**

Run: `quarto render ask.qmd --to html`
Expected: `Output created: _site/ask.html` with no errors.

- [ ] **Step 6: Commit**

```bash
git add ask.qmd scripts/ask.js _quarto.yml styles.scss
git commit -m "feat(ask): add the Ask Our Views frontend page"
```

---

### Task 11: Deploy and end-to-end verification

**Files:**
- Modify: `scripts/ask.js` (only if the actual Render URL differs from the assumed default)

**Interfaces:**
- Consumes: Render account, Groq API key.

- [ ] **Step 1: Push the branch and create the Render service**

Push all commits from Tasks 1–10 to the repo. In the Render dashboard: New → Web Service → connect this repo → Render should auto-detect `ask/render.yaml`. Set the `LLM_API_KEY` environment variable to a Groq API key (obtained from console.groq.com — free tier).

- [ ] **Step 2: Confirm the deployed service URL**

After the first successful deploy, note the assigned URL in the Render dashboard (expected: `https://ask-our-views-api.onrender.com`, per the `name` in `render.yaml`).

If it differs, update `API_BASE` in `scripts/ask.js` to match, then:

```bash
git add scripts/ask.js
git commit -m "fix(ask): correct deployed backend URL"
```

- [ ] **Step 3: Smoke-test the deployed backend directly**

```bash
curl -s -X POST https://ask-our-views-api.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "how should I think about rent control?"}' | python3 -m json.tool
```

Expected: a 200 response with `groups` populated and (with `LLM_API_KEY` set) non-null `connector_text` fields. First request after idling may take 30-60s (free-tier cold start) — this is expected per the spec's accepted reliability posture.

- [ ] **Step 4: Render the full site and preview locally**

```bash
quarto render
python3 -m http.server 8734 --directory _site
open http://localhost:8734/ask.html
```

Manually test in the browser:
- Ask a question with strong corpus coverage (e.g. "rent control", "semiconductor export controls") — expect populated author groups with excerpts and connector lines.
- Ask a question with no coverage (e.g. "opinions on the 1986 FIFA World Cup") — expect the "we haven't written directly about this yet" message.
- Submit an empty question — expect no error, just a no-op.
- Check the "Ask Our Views" nav link appears and works from other pages.

- [ ] **Step 5: Deploy the static site**

Push to `master` (or the branch that triggers the existing GitHub Pages deploy) so the new `ask.html` page and nav entry go live alongside the already-deployed backend.

- [ ] **Step 6: Tune the similarity threshold if needed**

If Step 4's manual testing showed either too many irrelevant excerpts or too many false "we haven't written about this" responses, adjust `ASK_MIN_SIMILARITY` in Render's environment variables (no code change needed — `ask/app.py` reads it from the environment) and redeploy. Re-run Step 3's curl test after any adjustment to confirm the change took effect.
