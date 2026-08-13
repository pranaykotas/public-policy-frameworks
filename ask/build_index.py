from __future__ import annotations

import hashlib
import json
import sqlite3

import numpy as np

from ask.attribution import split_sections
from ask.embed import embed_texts


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


def build_and_save(db_path: str, chunks_out_path: str, vectors_out_path: str) -> int:
    """Build chunks from the database, embed them, and write both artifacts to disk."""
    chunks = chunks_from_db(db_path)
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)

    with open(chunks_out_path, "w") as f:
        json.dump(chunks, f)
    np.save(vectors_out_path, vectors)

    return len(chunks)
