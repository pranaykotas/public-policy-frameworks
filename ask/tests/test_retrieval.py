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
    assert 1 not in indices


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
