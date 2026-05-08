#!/usr/bin/env python3
"""
Validate every framework qmd before build.
Checks:
  1. front-matter has `image:` pointing to a real file in images/
  2. front-matter image filename matches the image embedded in ## What it says
  3. ## What it says section contains an image embed (![...)

Run: python scripts/check-frameworks.py
Exits non-zero on first category of failure.
"""

import os, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CATEGORIES = ["public-policy", "political-thinking", "public-finance",
              "foreign-policy-defence-geopolitics", "society", "universe"]

def extract_frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}
    import yaml
    try:
        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}

def extract_what_it_says_body(text):
    m = re.search(r'^## What it says\s*\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ''

errors = []
warnings = []

for cat in CATEGORIES:
    cat_dir = ROOT / cat
    for qmd in sorted(cat_dir.glob('*.qmd')):
        if qmd.name == 'index.qmd':
            continue
        text = qmd.read_text()
        fm = extract_frontmatter(text)

        # 1. front-matter must have image:
        img_fm = fm.get('image', '')
        if not img_fm:
            errors.append(f'{qmd.relative_to(ROOT)}: missing `image:` in front-matter')
            continue

        # 2. image file must exist (path relative to the qmd file)
        img_path = (qmd.parent / img_fm).resolve()
        if not img_path.exists():
            errors.append(f'{qmd.relative_to(ROOT)}: front-matter image not found: {img_fm}')

        is_default = 'defaults/' in img_fm

        # 3. What it says must contain an image embed (skip for category-default pages)
        body = extract_what_it_says_body(text)
        body_images = re.findall(r'!\[.*?\]\(.*?images/(.*?)\)', body)
        if not body_images and not is_default:
            errors.append(f'{qmd.relative_to(ROOT)}: no image embed in ## What it says')
            continue

        # 4. front-matter image should match body image (skip for default pages)
        if body_images and not is_default:
            fm_base = Path(img_fm).name
            if fm_base not in body_images:
                warnings.append(
                    f'{qmd.relative_to(ROOT)}: front-matter image ({fm_base}) '
                    f'≠ body image ({body_images[0]})'
                )

if warnings:
    print('WARNINGS:')
    for w in warnings:
        print(f'  ⚠  {w}')

if errors:
    print('ERRORS:')
    for e in errors:
        print(f'  ✗  {e}')
    sys.exit(1)

print(f'✓ All framework pages passed ({sum(1 for c in CATEGORIES for _ in (ROOT/c).glob("*.qmd")) - len(CATEGORIES)} checked)')
