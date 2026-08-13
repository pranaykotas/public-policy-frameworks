#!/usr/bin/env python3
"""Build the Ask Our Views retrieval index from the Substack sync database.

Usage:
    python3 scripts/build_ask_index.py
    python3 scripts/build_ask_index.py --db /path/to/substack-atu.db
"""
from __future__ import annotations

import argparse
import os

from ask.build_index import build_and_save

DEFAULT_DB_PATH = os.path.expanduser("~/.claude/data/substack-atu.db")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to substack-atu.db")
    parser.add_argument("--chunks-out", default="ask/data/chunks.json")
    parser.add_argument("--vectors-out", default="ask/data/vectors.npy")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.chunks_out) or ".", exist_ok=True)
    count = build_and_save(args.db, args.chunks_out, args.vectors_out)
    print(f"Wrote {count} chunks to {args.chunks_out} and {args.vectors_out}")


if __name__ == "__main__":
    main()
