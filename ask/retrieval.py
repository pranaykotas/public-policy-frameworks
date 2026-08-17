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
    top_k: int = 10,
    min_floor: int = 2,
    max_per_author: int = 6,
    min_similarity: float = 0.25,
) -> list[tuple[int, float]]:
    """Return the top_k matches by relevance, but if an author with at least
    one match above min_similarity would otherwise be shut out of the top_k
    entirely, backfill up to min_floor of their best matches. Caps any single
    author at max_per_author so one prolific/relevant author can't fill the
    whole result set."""
    if vectors.shape[0] == 0:
        return []
    sims = vectors @ query_vector
    order = np.argsort(-sims)
    order = [i for i in order if sims[i] >= min_similarity]

    author_counts: dict[str, int] = {}
    results: list[tuple[int, float]] = []
    for i in order:
        if len(results) >= top_k:
            break
        author = chunks[int(i)].get("author", "?")
        if author_counts.get(author, 0) >= max_per_author:
            continue
        author_counts[author] = author_counts.get(author, 0) + 1
        results.append((int(i), float(sims[i])))

    # Backfill: guarantee any author with relevant matches gets at least
    # min_floor results, even if they were crowded out of the initial top_k.
    for i in order:
        author = chunks[int(i)].get("author", "?")
        if author_counts.get(author, 0) >= min_floor:
            continue
        if any(idx == int(i) for idx, _ in results):
            continue
        author_counts[author] = author_counts.get(author, 0) + 1
        results.append((int(i), float(sims[i])))

    results.sort(key=lambda x: -x[1])
    return results
