#!/usr/bin/env python3
"""Fetch Substack post content and cache as markdown text."""

import re
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CACHE_DIR = BASE_DIR / ".cache" / "posts"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def extract_substack_url(text: str) -> str | None:
    m = re.search(
        r"Originally explored in \[.*?\]\((https://publicpolicy\.substack\.com/[^)]+)\)",
        text,
    )
    if m:
        return m.group(1)
    m = re.search(r"\[Read the original essay on Substack.*?\]\((https://publicpolicy\.substack\.com/[^)]+)\)", text)
    if m:
        return m.group(1)
    m = re.search(r"\]\((https://publicpolicy\.substack\.com/[^)]+)\)", text)
    if m:
        return m.group(1)
    return None


def fetch_post(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_article(html: str) -> str:
    """Extract readable article text from Substack HTML."""
    # Try to find the main post content
    # Substack uses various class names over time
    patterns = [
        r'<div[^>]*class="[^"]*available-content[^"]*"[^>]*>(.*?)</div>\s*</div>\s*<div[^>]*class="[^"]*post-footer',
        r'<div[^>]*class="[^"]*post-content[^"]*"[^>]*>(.*?)</div>\s*(?:<div[^>]*class="[^"]*post-footer|<div[^>]*class="[^"]*subscribe-widget)',
        r'<div[^>]*class="[^"]*body[^"]*"[^>]*>(.*?)</div>\s*<div[^>]*class="[^"]*footer',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1)
    # Fallback: look for the largest text block
    return ""


def html_to_text(html: str) -> str:
    """Very basic HTML to text conversion."""
    # Remove scripts and styles
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Convert common block elements to newlines
    html = re.sub(r"</(p|div|h[1-6]|li|blockquote)>\s*", "\n\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<br\s*/?>\s*", "\n", html, flags=re.IGNORECASE)
    # Remove remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # Decode entities
    html = html.replace("&nbsp;", " ")
    html = html.replace("&quot;", '"')
    html = html.replace("&amp;", "&")
    html = html.replace("&lt;", "<")
    html = html.replace("&gt;", ">")
    html = html.replace("&#8217;", "'")
    html = html.replace("&#8220;", '"')
    html = html.replace("&#8221;", '"')
    html = html.replace("&#8230;", "...")
    html = html.replace("&#8212;", "—")
    html = html.replace("&#8211;", "–")
    # Clean up whitespace
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def main():
    qmd_files = sorted(BASE_DIR.rglob("*.qmd"))
    qmd_files = [f for f in qmd_files if f.name != "index.qmd" and f.name != "about.qmd"]

    for qmd_path in qmd_files:
        text = qmd_path.read_text(encoding="utf-8")
        title_match = re.search(r'^title:\s*"(.+)"', text, re.MULTILINE)
        title = title_match.group(1) if title_match else qmd_path.stem

        url = extract_substack_url(text)
        if not url:
            print(f"No URL: {title}")
            continue

        slug = re.sub(r"[^a-z0-9]", "-", title.lower()).strip("-")[:50]
        cache_path = CACHE_DIR / f"{slug}.txt"

        if cache_path.exists():
            print(f"Cached: {title}")
            continue

        print(f"Fetching: {title} ...")
        try:
            html = fetch_post(url)
            article_html = extract_article(html)
            if not article_html:
                # Fallback: try to get body content
                body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
                if body_match:
                    article_html = body_match.group(1)
            plain = html_to_text(article_html)
            cache_path.write_text(plain, encoding="utf-8")
            print(f"  -> {len(plain)} chars")
        except Exception as e:
            print(f"  FAILED: {e}")

        time.sleep(0.7)

    print("\nDone.")


if __name__ == "__main__":
    main()
