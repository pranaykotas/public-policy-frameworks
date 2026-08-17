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


def search_diverse(
    query_vector: np.ndarray,
    vectors: np.ndarray,
    chunks: list[dict],
    per_author: int = 5,
    min_similarity: float = 0.25,
) -> list[tuple[int, float]]:
    """Return top matches ensuring each author gets up to per_author results."""
    if vectors.shape[0] == 0:
        return []
    sims = vectors @ query_vector
    order = np.argsort(-sims)
    author_counts: dict[str, int] = {}
    results = []
    for i in order:
        if sims[i] < min_similarity:
            break
        author = chunks[int(i)].get("author", "?")
        if author_counts.get(author, 0) >= per_author:
            continue
        author_counts[author] = author_counts.get(author, 0) + 1
        results.append((int(i), float(sims[i])))
    return results
