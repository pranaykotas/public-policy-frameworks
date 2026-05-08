#!/usr/bin/env python3
"""
Assign category default images to every framework.
Removes all incorrect fetched images and replaces with consistent category-colored PNGs.
"""

import re, yaml, shutil
from pathlib import Path

ROOT = Path("/Users/pranay-karma/Projects/frameworks")
IMAGE_DIR = ROOT / "images"
DEFAULTS_DIR = IMAGE_DIR / "defaults"

CATEGORY_MAP = {
    "Public Policy": "public-policy.png",
    "Political Thinking": "political-thinking.png",
    "Public Finance": "public-finance.png",
    "Foreign Policy, Defence & Geopolitics": "foreign-policy-defence-geopolitics.png",
    "Society": "society.png",
    "Universe": "universe.png",
}

def get_category(f):
    text = f.read_text()
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1))
    except Exception:
        return None
    cats = fm.get("categories", [])
    if cats:
        return str(cats[0])
    return None

def main():
    # Clear out any remaining incorrect images
    for f in IMAGE_DIR.glob("*.png"):
        if f.name != "about.png":
            f.unlink()
    for f in IMAGE_DIR.glob("*.webp"):
        f.unlink()

    assigned = 0
    for cat_dir in ["public-policy", "political-thinking", "public-finance",
                     "foreign-policy-defence-geopolitics", "society", "universe"]:
        for f in (ROOT / cat_dir).glob("*.qmd"):
            if f.name == "index.qmd":
                continue
            
            cat = get_category(f)
            if not cat or cat not in CATEGORY_MAP:
                print(f"SKIP (no category): {f}")
                continue
            
            slug = f.stem
            default_src = DEFAULTS_DIR / CATEGORY_MAP[cat]
            dest = IMAGE_DIR / f"{slug}.png"
            shutil.copy(default_src, dest)
            
            # Update YAML image path
            text = f.read_text()
            new_text = re.sub(
                r'^(image:\s*").*?(\")',
                r'\1../images/' + slug + '.png\2',
                text,
                flags=re.MULTILINE
            )
            
            # Also update any inline image in the body
            new_text = re.sub(
                r'!\[(.*?)\]\(\.\./images/[^)]+\)',
                r'![\1](../images/' + slug + '.png)',
                new_text
            )
            
            if new_text != text:
                f.write_text(new_text)
            
            assigned += 1
            print(f"ASSIGNED: {slug} -> {CATEGORY_MAP[cat]}")
    
    print(f"\nAssigned {assigned} default images.")

if __name__ == "__main__":
    main()
