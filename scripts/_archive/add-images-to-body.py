#!/usr/bin/env python3
"""Add framework images to the body of every .qmd file, right after the card-meta block."""

import re, yaml
from pathlib import Path

ROOT = Path("/Users/pranay-karma/Projects/frameworks")

for f in ROOT.rglob("*.qmd"):
    name = f.name
    if name == "index.qmd" or name == "about.qmd" or name == "find-framework.qmd":
        continue
    if "_site" in str(f) or ".quarto" in str(f):
        continue

    text = f.read_text()
    # Skip if image already in body
    if re.search(r'^!\[', text, re.MULTILINE):
        continue

    # Extract YAML
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        continue
    try:
        fm = yaml.safe_load(m.group(1))
    except Exception:
        continue

    img = fm.get("image", "")
    title = fm.get("title", "")
    if not img or not title:
        continue

    # Build image markdown
    image_md = f'![{title}]({img}){{fig-alt="{title}"}}'

    # Insert after card-meta block and before the pull quote
    # Pattern: card-meta block ending, then blank line, then > quote
    pattern = r'(::: \{\.card-meta\}\n.*?\n:::)\n\n(>)'
    replacement = r'\1\n\n' + image_md + r'\n\n\2'

    new_text = re.sub(pattern, replacement, text, flags=re.DOTALL)
    if new_text != text:
        f.write_text(new_text)
        print(f"ADDED: {f.relative_to(ROOT)}")
    else:
        # Try alternate pattern: card-meta block without blank line before quote
        pattern2 = r'(::: \{\.card-meta\}\n.*?\n:::)\n(>)'
        replacement2 = r'\1\n\n' + image_md + r'\n\n\2'
        new_text2 = re.sub(pattern2, replacement2, text, flags=re.DOTALL)
        if new_text2 != text:
            f.write_text(new_text2)
            print(f"ADDED (alt): {f.relative_to(ROOT)}")
        else:
            print(f"SKIP: {f.relative_to(ROOT)}")
