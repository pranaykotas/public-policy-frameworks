#!/usr/bin/env python3
"""
Three-pass scrape of the Anticipating the Unintended newsletter archive.
Pass 1: Find posts containing "A Framework a Week" heading.
Pass 2: Extract framework titles, deduplicate against existing cards.
Pass 3: Extract framework sections and write cards.
"""

import re, os, json, time, yaml, requests
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path("/Users/pranay-karma/Projects/frameworks")
CACHE_DIR = ROOT / ".cache/posts"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
SITEMAP_URL = "https://publicpolicy.substack.com/sitemap.xml"

def get_all_post_urls():
    r = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
    urls = re.findall(r'<loc>(https://publicpolicy\.substack\.com/p/[^<]+)</loc>', r.text)
    exclude = {"/book", "/coming-soon", "/frameworks", "/policywtfsa-hall-of-shame", "/policywtfsa-hall-of-shame-063",
               "/public-policy-review-1", "/public-policy-review-2", "/public-policy-review-3", "/public-policy-review-4",
               "/special-edition-frameworks-to-understand", "/unlearn-to-learn-public-policy"}
    filtered = []
    for u in urls:
        slug = u.split("/p/")[-1]
        if not any(slug.startswith(e.lstrip("/")) for e in exclude):
            filtered.append(u)
    return sorted(set(filtered))

def has_framework_section(url):
    """Pass 1: Check if post contains 'A Framework a Week' heading."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator="\n")
        if re.search(r'A\s+Framework\s+A\s+Week', text, re.IGNORECASE):
            return True, r.text
        return False, None
    except Exception as e:
        print(f"ERROR fetching {url}: {e}")
        return False, None

def extract_framework_title(html):
    """Extract the framework title from the HTML."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # Pattern 1: "A Framework a Week: Title" on same line
    for line in lines:
        m = re.search(r'A\s+Framework\s+A\s+Week[:\s]+(.+)', line, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            if title and len(title) > 5 and len(title) < 200:
                return title
    
    # Pattern 2: "A Framework a Week" followed by title on next line
    for i, line in enumerate(lines):
        if re.search(r'^A\s+Framework\s+A\s+Week$', line, re.IGNORECASE):
            for j in range(i+1, min(i+5, len(lines))):
                candidate = lines[j]
                if candidate in ["Tools for thinking public policy", "Tools for thinking about public policy", 
                                 "— Pranay Kotasthane", "— RSJ", "Subscribe", "Share", "Listen"]:
                    continue
                if len(candidate) > 5 and len(candidate) < 200:
                    return candidate
    
    return None

def slugify(title):
    return re.sub(r'[^\w]+', '-', title.lower()).strip('-')

def get_existing_slugs():
    slugs = set()
    for cat in ["public-policy", "political-thinking", "public-finance",
                "foreign-policy-defence-geopolitics", "society", "universe"]:
        for f in (ROOT / cat).glob("*.qmd"):
            if f.name == "index.qmd":
                continue
            slugs.add(f.stem)
    return slugs

def main():
    print("=== Pass 1: Fetching all post URLs ===")
    urls = get_all_post_urls()
    print(f"Found {len(urls)} post URLs")
    
    framework_posts = []
    for idx, url in enumerate(urls):
        has_fw, html = has_framework_section(url)
        if has_fw:
            title = extract_framework_title(html)
            if title:
                framework_posts.append({"url": url, "title": title, "slug": slugify(title)})
                print(f"[{idx+1}/{len(urls)}] FRAMEWORK: {title}")
            else:
                print(f"[{idx+1}/{len(urls)}] FRAMEWORK (no title): {url}")
        else:
            print(f"[{idx+1}/{len(urls)}] —")
        time.sleep(0.5)
    
    print(f"\n=== Pass 2: Deduplicating ===")
    existing = get_existing_slugs()
    print(f"Existing frameworks: {len(existing)}")
    
    missing = []
    seen_slugs = set()
    for post in framework_posts:
        if post["slug"] in seen_slugs:
            print(f"DUPE:    {post['title']} ({post['slug']})")
            continue
        seen_slugs.add(post["slug"])
        if post["slug"] not in existing:
            missing.append(post)
            print(f"MISSING: {post['title']} ({post['slug']})")
        else:
            print(f"EXISTS:  {post['title']} ({post['slug']})")
    
    results = {
        "all_posts": len(urls),
        "framework_posts": len(framework_posts),
        "missing_frameworks": missing,
        "existing_slugs": list(existing),
    }
    out_path = ROOT / ".cache/scrape-results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n=== Summary ===")
    print(f"Total posts checked: {len(urls)}")
    print(f"Posts with frameworks: {len(framework_posts)}")
    print(f"Missing frameworks: {len(missing)}")
    print(f"Results saved to {out_path}")

if __name__ == "__main__":
    main()
