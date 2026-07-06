#!/usr/bin/env python3
"""
Sync all posts from publicpolicy.substack.com into a local SQLite FTS5 database.
Supports incremental updates — only fetches posts not already in DB.

Usage:
    python3 scripts/sync-substack-db.py          # incremental sync
    python3 scripts/sync-substack-db.py --full    # re-fetch everything

Database: ~/.claude/data/substack-atu.db
"""

import json
import os
import re
import sqlite3
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

try:
    import requests
except ImportError:
    print("Need requests: pip install requests")
    sys.exit(1)

DB_PATH = Path(os.path.expanduser("~/.claude/data/substack-atu.db"))
API_URL = "https://publicpolicy.substack.com/api/v1/posts"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
}
PAGE_SIZE = 50


# --- HTML to plain text using stdlib ---

class HTMLToText(HTMLParser):
    BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
                  "li", "blockquote", "tr", "br", "hr"}

    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
        elif tag in self.BLOCK_TAGS:
            self._parts.append("\n")
        elif tag == "br":
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False
        elif tag in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self):
        text = "".join(self._parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_text(html):
    parser = HTMLToText()
    parser.feed(html or "")
    return parser.get_text()


# --- Database setup ---

def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            subtitle TEXT,
            date TEXT NOT NULL,
            url TEXT NOT NULL,
            author TEXT,
            tags TEXT,
            wordcount INTEGER,
            body_text TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
            title,
            subtitle,
            body_text,
            tags,
            content='posts',
            content_rowid='id',
            tokenize='porter unicode61'
        );

        CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
            INSERT INTO posts_fts(rowid, title, subtitle, body_text, tags)
            VALUES (new.id, new.title, new.subtitle, new.body_text, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
            INSERT INTO posts_fts(posts_fts, rowid, title, subtitle, body_text, tags)
            VALUES ('delete', old.id, old.title, old.subtitle, old.body_text, old.tags);
        END;
    """)


def slug_exists(conn, slug):
    row = conn.execute("SELECT 1 FROM posts WHERE slug = ?", (slug,)).fetchone()
    return row is not None


# --- API fetching ---

def fetch_page(offset):
    resp = requests.get(
        API_URL,
        params={"limit": PAGE_SIZE, "offset": offset},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def extract_post(raw):
    author = ""
    bylines = raw.get("publishedBylines") or []
    if bylines:
        author = bylines[0].get("name", "")

    tags_list = raw.get("postTags") or []
    if isinstance(tags_list, list):
        tag_names = []
        for t in tags_list:
            if isinstance(t, dict):
                tag_names.append(t.get("name", ""))
            elif isinstance(t, str):
                tag_names.append(t)
        tags = ", ".join(tag_names)
    else:
        tags = ""

    body_html = raw.get("body_html") or ""
    body_text = html_to_text(body_html)

    return {
        "slug": raw.get("slug", ""),
        "title": raw.get("title", ""),
        "subtitle": raw.get("subtitle", ""),
        "date": raw.get("post_date", ""),
        "url": raw.get("canonical_url", ""),
        "author": author,
        "tags": tags,
        "wordcount": raw.get("wordcount", 0),
        "body_text": body_text,
    }


# --- Main sync ---

def sync(full=False):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    if full:
        conn.execute("DELETE FROM posts")
        conn.commit()
        print("Full sync — cleared existing data.")

    offset = 0
    new_count = 0
    skip_streak = 0

    while True:
        print(f"Fetching offset={offset}...", end=" ", flush=True)
        try:
            posts = fetch_page(offset)
        except Exception as e:
            print(f"Error: {e}")
            break

        if not posts:
            print("no more posts.")
            break

        page_new = 0
        for raw in posts:
            slug = raw.get("slug", "")
            if not slug:
                continue
            if slug_exists(conn, slug):
                skip_streak += 1
                continue

            skip_streak = 0
            post = extract_post(raw)
            conn.execute(
                """INSERT INTO posts (slug, title, subtitle, date, url, author, tags, wordcount, body_text)
                   VALUES (:slug, :title, :subtitle, :date, :url, :author, :tags, :wordcount, :body_text)""",
                post,
            )
            page_new += 1
            new_count += 1

        conn.commit()
        print(f"{page_new} new, {len(posts) - page_new} existing.")

        # Stop early if entire page was known posts (incremental optimization)
        if not full and skip_streak >= PAGE_SIZE:
            print("All recent posts already synced. Stopping.")
            break

        offset += PAGE_SIZE
        time.sleep(0.3)

    total = conn.execute("SELECT count(*) FROM posts").fetchone()[0]
    conn.close()
    print(f"\nDone. {new_count} new posts synced. Total in DB: {total}")


if __name__ == "__main__":
    full_mode = "--full" in sys.argv
    sync(full=full_mode)
