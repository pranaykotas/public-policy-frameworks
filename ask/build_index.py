from __future__ import annotations

import hashlib
import json
import sqlite3

import numpy as np

from ask.attribution import split_sections
from ask.embed import embed_texts

MAX_CHUNK_WORDS = 400
OVERLAP_WORDS = 50


def _sub_chunk(text: str) -> list[str]:
    """Split text into overlapping sub-chunks by word count.

    Short texts are returned as-is. Longer texts are split at paragraph
    boundaries where possible, with word-level fallback.
    """
    words = text.split()
    if len(words) <= MAX_CHUNK_WORDS:
        return [text]

    paragraphs = text.split("\n\n")
    sub_chunks: list[str] = []
    current_words: list[str] = []

    for para in paragraphs:
        para_words = para.split()
        if current_words and len(current_words) + len(para_words) > MAX_CHUNK_WORDS:
            sub_chunks.append(" ".join(current_words))
            overlap = current_words[-OVERLAP_WORDS:] if len(current_words) > OVERLAP_WORDS else []
            current_words = overlap + para_words
        else:
            current_words.extend(para_words)

    if current_words:
        sub_chunks.append(" ".join(current_words))

    return sub_chunks if sub_chunks else [text]


def chunks_from_db(db_path: str) -> list[dict]:
    """Read all posts from the Substack sync database and split into
    author-attributed, sub-chunked pieces."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT title, date, url, body_text FROM posts").fetchall()
    finally:
        conn.close()

    chunks: list[dict] = []
    for title, date, url, body_text in rows:
        for i, section in enumerate(split_sections(body_text)):
            header_prefix = f"{section['header']}: {section['title']}"
            sub_texts = _sub_chunk(section["text"])

            for j, sub_text in enumerate(sub_texts):
                chunk_id = hashlib.sha1(
                    f"{url}|{section['header']}|{i}|{j}".encode("utf-8")
                ).hexdigest()[:12]
                embed_text = f"{header_prefix}\n\n{sub_text}"
                chunks.append(
                    {
                        "id": chunk_id,
                        "author": section["author"],
                        "post_title": title,
                        "post_url": url,
                        "date": date,
                        "header": section["header"],
                        "section_title": section["title"],
                        "text": sub_text,
                        "embed_text": embed_text,
                    }
                )
    return chunks


def build_and_save(db_path: str, chunks_out_path: str, vectors_out_path: str) -> int:
    """Build chunks from the database, embed them, and write both artifacts to disk."""
    chunks = chunks_from_db(db_path)
    texts = [c["embed_text"] for c in chunks]
    vectors = embed_texts(texts)

    with open(chunks_out_path, "w") as f:
        json.dump(chunks, f)
    np.save(vectors_out_path, vectors)

    return len(chunks)
