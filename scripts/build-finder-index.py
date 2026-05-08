#!/usr/bin/env python3
"""
Builds frameworks.json — a client-side index for the Framework Finder page.
Reads every .qmd file, extracts YAML frontmatter + body text keywords,
and emits a JSON file that the find-framework.qmd page loads via JS.
"""

import os, re, json, yaml
from pathlib import Path

ROOT = Path(__file__).parent.parent
CATEGORIES = ["public-policy", "political-thinking", "public-finance",
              "foreign-policy-defence-geopolitics", "society", "universe"]

def slugify(title):
    return re.sub(r'[^\w]+', '-', title.lower()).strip('-')

def extract_yaml(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if m:
        try:
            return yaml.safe_load(m.group(1))
        except Exception:
            pass
    return {}

def extract_keywords(text, frontmatter):
    """Extract additional keywords from body text for matching."""
    # Remove YAML frontmatter
    body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)
    # Extract section headers
    headers = re.findall(r'^##\s+(.+)$', body, re.MULTILINE)
    # Extract words from first paragraph after pull quote
    lines = body.splitlines()
    content_words = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('>') and not line.startswith(':::') and not line.startswith('`') and not line.startswith('['):
            words = re.findall(r'\b[a-zA-Z]{5,}\b', line)
            content_words.extend([w.lower() for w in words])
            if len(content_words) > 50:
                break
    return list(set([h.lower() for h in headers] + content_words[:30]))

def build_index():
    frameworks = []
    for cat in CATEGORIES:
        cat_dir = ROOT / cat
        for f in cat_dir.glob("*.qmd"):
            if f.name == "index.qmd":
                continue
            text = f.read_text()
            fm = extract_yaml(text)
            if not fm.get("title"):
                continue
            
            slug = f.stem
            tags = fm.get("tags", [])
            use_cases = fm.get("use_cases", [])
            keywords = extract_keywords(text, fm)
            
            # Merge tags into keywords for matching
            flat_keywords = [t.lower() for t in tags]
            for u in use_cases:
                flat_keywords.extend(re.sub(r'[^\w]', ' ', u).lower().split())
            flat_keywords.extend(keywords)
            all_keywords = list(set(flat_keywords))
            
            frameworks.append({
                "slug": slug,
                "title": fm["title"],
                "summary": fm.get("summary", ""),
                "category": cat,
                "tags": tags,
                "use_cases": use_cases,
                "keywords": all_keywords,
                "url": f"{cat}/{slug}.html",
            })
    
    out = ROOT / "frameworks.json"
    with open(out, "w") as f:
        json.dump(frameworks, f, indent=2)
    print(f"Wrote {len(frameworks)} frameworks to {out}")

if __name__ == "__main__":
    build_index()
