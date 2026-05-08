#!/usr/bin/env python3
"""Parse _stubs.qmd and generate individual .qmd stub files."""

import re
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STUBS_FILE = BASE_DIR / "_stubs.qmd"

CATEGORY_MAP = {
    "Public Policy": "public-policy",
    "Political Thinking": "political-thinking",
    "Public Finance": "public-finance",
    "Foreign Policy, Defence & Geopolitics": "foreign-policy-defence-geopolitics",
    "Society": "society",
    "Universe": "universe",
}


def slugify(title: str) -> str:
    """Create a filesystem-safe slug from a title."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    return s.strip("-")[:60]


def parse_stubs(text: str):
    """Yield (category_dir, title, summary, url) for each stub entry."""
    lines = text.splitlines()
    current_category = None
    in_stub = False
    stub_lines = []

    for line in lines:
        cat_match = re.match(r"^###\s+(.+)$", line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            continue

        if line.strip().startswith("::: {.stub-entry}"):
            in_stub = True
            stub_lines = []
            continue

        if in_stub and line.strip() == ":::":
            in_stub = False
            stub_text = "\n".join(stub_lines)

            # Extract title
            title_match = re.search(r"\[\*\*(.+?)\*\*\]\{\.stub-name\}", stub_text)
            title = title_match.group(1).strip() if title_match else "Untitled"

            # Extract summary
            summary_match = re.search(r"\[(.+?)\]\{\.stub-summary\}", stub_text)
            summary = summary_match.group(1).strip() if summary_match else ""

            # Extract URL
            url_match = re.search(r"\[\[.*?\]\((.+?)\)\]\{\.stub-link\}", stub_text)
            url = url_match.group(1).strip() if url_match else ""

            category_dir = CATEGORY_MAP.get(current_category, current_category.lower().replace(" ", "-").replace(",", ""))

            yield category_dir, title, summary, url
            continue

        if in_stub:
            stub_lines.append(line)


def main():
    text = STUBS_FILE.read_text(encoding="utf-8")
    generated = 0

    for category_dir, title, summary, url in parse_stubs(text):
        target_dir = BASE_DIR / category_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        slug = slugify(title)
        filepath = target_dir / f"{slug}.qmd"

        # Skip if a file with this title already exists (avoid overwriting real cards)
        if filepath.exists():
            print(f"Skipping existing: {filepath}")
            continue

        # Also check if any .qmd in this dir has the same title in frontmatter
        existing_titles = set()
        for existing in target_dir.glob("*.qmd"):
            if existing.name == "index.qmd":
                continue
            m = re.search(r'^title:\s*"(.+)"', existing.read_text(encoding="utf-8"), re.MULTILINE)
            if m:
                existing_titles.add(m.group(1).strip())

        if title in existing_titles:
            print(f"Skipping duplicate title in {category_dir}: {title}")
            continue

        # Map category dir back to display name
        display_category = {v: k for k, v in CATEGORY_MAP.items()}.get(category_dir, category_dir)

        body = f'''---
title: "{title}"
summary: "{summary}"
categories: [{display_category}]
date: 2026-05-03
---

::: {{.card-meta}}
[{display_category}]{{.badge}}
:::

This framework is explored in the *A Framework a Week* series on *Anticipating the Unintended*.

[Read the original essay on Substack &rarr;]({url})
'''
        filepath.write_text(body, encoding="utf-8")
        generated += 1
        print(f"Generated: {filepath}")

    print(f"\nTotal stub files generated: {generated}")


if __name__ == "__main__":
    main()
