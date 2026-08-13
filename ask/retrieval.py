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
