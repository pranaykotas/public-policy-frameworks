#!/usr/bin/env python3
"""Extract the 'A Framework A Week' section from each cached post."""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CACHE_DIR = BASE_DIR / ".cache" / "posts"
SECTIONS_DIR = BASE_DIR / ".cache" / "sections"
SECTIONS_DIR.mkdir(parents=True, exist_ok=True)


def extract_framework_section(text: str) -> str:
    """Extract just the A Framework A Week section from a newsletter."""
    # Pattern 1: "A Framework A Week: Title" header
    m = re.search(
        r"A\s*Framework\s*[Aa]\s*Week[:\s]*.*?(?:\n|—\s*Pranay)"
        r"(.*?)(?:Leave a comment|Subscribe|HomeWork|India Policy Watch|Global Policy Watch|Matsyanyaaya|PolicyWTF)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        content = m.group(1).strip()
        # Remove the tagline if present
        content = re.sub(r"^Tools for thinking about public policy\s*—\s*Pranay Kotasthane\s*", "", content, flags=re.IGNORECASE)
        return content

    # Pattern 2: Look for "— Pranay Kotasthane" and take content after it
    m = re.search(
        r"—\s*Pranay Kotasthane\s*(.*?)(?:Leave a comment|Subscribe|HomeWork|India Policy Watch|Global Policy Watch|Matsyanyaaya|PolicyWTF)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()

    # Pattern 3: If the text is short and doesn't have other sections, return it all
    if len(text) < 15000 and "India Policy Watch" not in text and "Global Policy Watch" not in text:
        return text.strip()

    # Pattern 4: Try to find the largest coherent block that's not a newsletter header
    lines = text.splitlines()
    framework_lines = []
    in_framework = False
    for i, line in enumerate(lines):
        if re.search(r"A\s*Framework\s*[Aa]\s*Week", line, re.IGNORECASE):
            in_framework = True
            continue
        if in_framework:
            if re.search(r"^(India Policy Watch|Global Policy Watch|HomeWork|Subscribe|Matsyanyaaya|PolicyWTF|Leave a comment)", line, re.IGNORECASE):
                break
            framework_lines.append(line)

    if framework_lines:
        return "\n".join(framework_lines).strip()

    return text.strip()


def main():
    for cache_file in sorted(CACHE_DIR.glob("*.txt")):
        slug = cache_file.stem
        text = cache_file.read_text(encoding="utf-8")
        section = extract_framework_section(text)
        out_path = SECTIONS_DIR / f"{slug}.txt"
        out_path.write_text(section, encoding="utf-8")
        print(f"{slug}: {len(section)} chars")


if __name__ == "__main__":
    main()
