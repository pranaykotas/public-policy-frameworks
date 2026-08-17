from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ask.cache import TTLCache
from ask.embed import embed_texts
from ask.llm import generate_connector
from ask.ratelimit import RateLimiter
from ask.retrieval import group_by_author, load_index, search_diverse

CHUNKS_PATH = os.environ.get("ASK_CHUNKS_PATH", "ask/data/chunks.json")
VECTORS_PATH = os.environ.get("ASK_VECTORS_PATH", "ask/data/vectors.npy")
MAX_REQUESTS_PER_HOUR = int(os.environ.get("ASK_RATE_LIMIT", "30"))
CACHE_TTL_SECONDS = int(os.environ.get("ASK_CACHE_TTL", "86400"))
MIN_SIMILARITY = float(os.environ.get("ASK_MIN_SIMILARITY", "0.20"))
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

    try:
        index = get_index()
        query_vector = embed_texts([question])[0]
    except Exception:
        return {"error": "embed_failed", "message": "Something went wrong — please try again in a moment."}
    matches = search_diverse(query_vector, index["vectors"], index["chunks"], per_author=TOP_K, min_similarity=MIN_SIMILARITY)

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
