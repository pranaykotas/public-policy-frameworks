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
