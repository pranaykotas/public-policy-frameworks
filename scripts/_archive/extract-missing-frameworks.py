#!/usr/bin/env python3
"""
Pass 3: For missing frameworks, fetch post HTML, extract the framework section,
and save to cache. Does NOT write .qmd cards yet.
"""

import re, json, time, requests
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path("/Users/pranay-karma/Projects/frameworks")
CACHE_DIR = ROOT / ".cache/posts"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def slugify(title):
    return re.sub(r'[^\w]+', '-', title.lower()).strip('-')

def extract_framework_section(html, title):
    """Extract the A Framework a Week section from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # Find the start of the framework section
    start_idx = None
    for i, line in enumerate(lines):
        if re.search(r'A\s+Framework\s+A\s+Week', line, re.IGNORECASE):
            start_idx = i
            break
    
    if start_idx is None:
        return None
    
    # Find the end - next major section
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if re.search(r'^(India Policy Watch|Global Policy Watch|PolicyWTF|HomeWork|Share|Subscribe|Listen on|Recent Episodes|CommentsRestacks)', lines[i], re.IGNORECASE):
            end_idx = i
            break
        # Also stop at heavy separator patterns
        if lines[i] in ['—', '***', '---'] and i > start_idx + 5:
            end_idx = i
            break
    
    section = "\n".join(lines[start_idx:end_idx])
    return section

def main():
    with open(ROOT / ".cache/scrape-results.json") as f:
        data = json.load(f)
    
    existing_slugs = set(data["existing_slugs"])
    missing = data["missing_frameworks"]
    
    # Filter out obvious duplicates and bad titles
    skip_slugs = {
        "online-activism-through-the",
        "this-week-s-framework-is-an-insight-from-the-world-of-public-finance-known-as",
    }
    
    extracted = 0
    for m in missing:
        slug = m["slug"]
        if slug in skip_slugs:
            print(f"SKIP (bad title): {m['title']}")
            continue
        
        # Check if this is actually a duplicate with different slug
        # Quick heuristic: if the title matches an existing framework closely
        title_norm = re.sub(r'[^\w]', '', m['title'].lower())
        is_duplicate = False
        for e in existing_slugs:
            e_norm = re.sub(r'[^\w]', '', e.lower())
            if title_norm in e_norm or e_norm in title_norm:
                if len(title_norm) > 10 and len(e_norm) > 10:
                    print(f"SKIP (likely dupe): {m['title']} -> {e}")
                    is_duplicate = True
                    break
        if is_duplicate:
            continue
        
        url = m["url"]
        print(f"EXTRACTING: {m['title']} from {url}")
        
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            section = extract_framework_section(r.text, m['title'])
            if section and len(section) > 200:
                cache_path = CACHE_DIR / f"{slug}.txt"
                with open(cache_path, "w") as f:
                    f.write(section)
                print(f"  -> Saved {len(section)} chars to {cache_path}")
                extracted += 1
            else:
                print(f"  -> Section too short or not found ({len(section) if section else 0} chars)")
        except Exception as e:
            print(f"  -> ERROR: {e}")
        
        time.sleep(0.5)
    
    print(f"\nExtracted {extracted} framework sections.")

if __name__ == "__main__":
    main()
