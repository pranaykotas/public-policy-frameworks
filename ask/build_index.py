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
