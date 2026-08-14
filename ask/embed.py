from __future__ import annotations

import os
import time

import numpy as np
import requests

JINA_API_URL = os.environ.get("JINA_API_URL", "https://api.jina.ai/v1/embeddings")
JINA_API_KEY = os.environ.get("JINA_API_KEY", "")
JINA_MODEL = os.environ.get("JINA_MODEL", "jina-embeddings-v3")
EMBED_DIM = int(os.environ.get("JINA_EMBED_DIM", "384"))
BATCH_SIZE = 20
BATCH_DELAY = 5
MAX_RETRIES = 5


def _embed_batch(texts: list[str]) -> np.ndarray:
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                JINA_API_URL,
                headers={
                    "Authorization": f"Bearer {JINA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": JINA_MODEL,
                    "input": texts,
                    "dimensions": EMBED_DIM,
                    "normalized": True,
                },
                timeout=60,
            )
        except (requests.ConnectionError, requests.Timeout) as e:
            last_err = e
            time.sleep(min(10 * (attempt + 1), 60))
            continue
        if resp.status_code == 429:
            time.sleep(min(10 * (attempt + 1), 60))
            continue
        resp.raise_for_status()
        data = resp.json()["data"]
        data.sort(key=lambda d: d["index"])
        return np.array([d["embedding"] for d in data], dtype=np.float32)
    if last_err:
        raise last_err
    resp.raise_for_status()
    return np.zeros((0, EMBED_DIM), dtype=np.float32)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of strings into L2-normalized vectors via Jina API."""
    if not texts:
        return np.zeros((0, EMBED_DIM), dtype=np.float32)
    if len(texts) <= BATCH_SIZE:
        return _embed_batch(texts)
    parts = []
    for i in range(0, len(texts), BATCH_SIZE):
        if i > 0:
            time.sleep(BATCH_DELAY)
        parts.append(_embed_batch(texts[i : i + BATCH_SIZE]))
    return np.vstack(parts)
