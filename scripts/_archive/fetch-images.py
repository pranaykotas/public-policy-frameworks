#!/usr/bin/env python3
"""Fetch hero images from Substack posts and update .qmd frontmatter."""

import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).parent.parent
IMAGES_DIR = BASE_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)

DEFAULTS_DIR = IMAGES_DIR / "defaults"

CATEGORY_COLORS = {
    "Public Policy": "#1a4480",
    "Political Thinking": "#8B2942",
    "Public Finance": "#2E5A38",
    "Foreign Policy, Defence & Geopolitics": "#5B3A7B",
    "Society": "#A0522D",
    "Universe": "#4A6572",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    return s.strip("-")[:60]


def extract_substack_url(text: str) -> str | None:
    """Find the first publicpolicy.substack.com URL in the file text."""
    # Look for attribution block URL first
    m = re.search(
        r"Originally explored in \[.*?\]\((https://publicpolicy\.substack\.com/[^)]+)\)",
        text,
    )
    if m:
        return m.group(1)
    # Then any markdown link to substack
    m = re.search(r"\]\((https://publicpolicy\.substack\.com/[^)]+)\)", text)
    if m:
        return m.group(1)
    return None


def extract_og_image(url: str) -> str | None:
    """Fetch a page and return its og:image URL."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  Failed to fetch {url}: {e}")
        return None

    m = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html,
    )
    if m:
        return m.group(1)
    m = re.search(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        html,
    )
    if m:
        return m.group(1)
    return None


def download_image(url: str, dest: Path) -> bool:
    """Download an image to dest. Return True on success."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"  Failed to download image {url}: {e}")
        return False


def get_category(text: str) -> str:
    """Extract category from frontmatter categories field."""
    m = re.search(r'^categories:\s*\[([^\]]+)\]', text, re.MULTILINE)
    if m:
        return m.group(1).strip().strip('"').strip("'")
    return "Universe"


def update_frontmatter(text: str, image_path: str) -> str:
    """Add or update the image: field in YAML frontmatter."""
    # Check if image already exists
    if re.search(r'^image:\s*\S', text, re.MULTILINE):
        text = re.sub(
            r'^image:\s*\S.*$',
            f'image: "{image_path}"',
            text,
            flags=re.MULTILINE,
        )
    else:
        text = re.sub(
            r'^(date:\s*\S.*)$',
            r'\1\nimage: "' + image_path + '"',
            text,
            flags=re.MULTILINE,
            count=1,
        )
    return text


def main():
    qmd_files = sorted(BASE_DIR.rglob("*.qmd"))
    # Skip index.qmd files
    qmd_files = [f for f in qmd_files if f.name != "index.qmd"]

    # Keep track of downloaded URLs to avoid duplicates
    url_to_path: dict[str, str] = {}
    fallback_used = 0
    fetched = 0
    failed = 0

    for qmd_path in qmd_files:
        text = qmd_path.read_text(encoding="utf-8")
        title_match = re.search(r'^title:\s*"(.+)"', text, re.MULTILINE)
        title = title_match.group(1) if title_match else qmd_path.stem
        slug = slugify(title)

        substack_url = extract_substack_url(text)
        if not substack_url:
            print(f"No Substack URL in {qmd_path.name}; skipping.")
            failed += 1
            continue

        print(f"Processing: {title}")

        # Determine image path
        img_ext = "webp"
        img_filename = f"{slug}.{img_ext}"
        img_path = IMAGES_DIR / img_filename
        rel_path = f"images/{img_filename}"

        # If this Substack URL was already downloaded, reuse it
        if substack_url in url_to_path:
            existing_rel = url_to_path[substack_url]
            text = update_frontmatter(text, existing_rel)
            qmd_path.write_text(text, encoding="utf-8")
            print(f"  Reusing existing image: {existing_rel}")
            continue

        # Try to fetch og:image
        og_url = extract_og_image(substack_url)
        if og_url:
            print(f"  Found og:image: {og_url[:80]}...")
            if download_image(og_url, img_path):
                url_to_path[substack_url] = rel_path
                text = update_frontmatter(text, rel_path)
                qmd_path.write_text(text, encoding="utf-8")
                print(f"  Downloaded -> {rel_path}")
                fetched += 1
                time.sleep(0.7)
                continue

        # Fallback: use category default
        category = get_category(text)
        default_slug = slugify(category)
        default_rel = f"images/defaults/{default_slug}.png"
        text = update_frontmatter(text, default_rel)
        qmd_path.write_text(text, encoding="utf-8")
        print(f"  Fallback -> {default_rel}")
        fallback_used += 1
        time.sleep(0.3)

    print(f"\nDone. Fetched: {fetched}, Fallbacks: {fallback_used}, No URL: {failed}")


if __name__ == "__main__":
    main()
