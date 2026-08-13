from __future__ import annotations

import re

SECTION_HEADER_PATTERN = re.compile(
    r"^([A-Z][A-Za-z ,()#\-']+?):\s+([A-Z][^\n]{3,80})", re.MULTILINE
)

NOISE_HEADERS = frozenset({
    "leave a comment", "share", "subscribe now", "source", "outcome",
    "result", "course advertisement", "programming note", "translation",
    "data source", "ps", "pps", "share anticipating the unintended",
})

SIGNATURE_PATTERN = re.compile(r"^[—-]\s*([A-Z][A-Za-z .]{2,60})\s*$", re.MULTILINE)

MIN_SECTION_LENGTH = 100

PRANAY_ALIASES = ("pranay kotasthane", "pranay kotashane")
RSJ_ALIASES = ("rsj", "raghu sanjaylal jaitley")


def classify_signature(sig_text: str) -> str | None:
    """Classify a signature line into 'Pranay', 'RSJ', 'Joint', or None (drop)."""
    s = sig_text.lower()
    has_pranay = any(alias in s for alias in PRANAY_ALIASES)
    has_rsj = any(alias in s for alias in RSJ_ALIASES)
    if has_pranay and has_rsj:
        return "Joint"
    if has_pranay:
        return "Pranay"
    if has_rsj:
        return "RSJ"
    return None


def split_sections(body_text: str) -> list[dict]:
    """Split a post body into ATU sections, tagging each with its author.

    Any Title Case header followed by a colon and title is treated as a
    section boundary. CTA/noise headers are skipped. Sections signed by
    someone other than Pranay or RSJ are dropped, as are sections under the
    minimum length.
    """
    all_matches = list(SECTION_HEADER_PATTERN.finditer(body_text))
    matches = [m for m in all_matches if m.group(1).strip().lower() not in NOISE_HEADERS]
    sections = []
    for i, m in enumerate(matches):
        header_name = re.sub(r"\s*#\d+", "", m.group(1)).strip()
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body_text)
        section_text = body_text[start:end].strip()

        if len(section_text) < MIN_SECTION_LENGTH:
            continue

        sig_matches = SIGNATURE_PATTERN.findall(section_text)
        author = classify_signature(sig_matches[-1]) if sig_matches else "Joint"
        if author is None:
            continue

        sections.append(
            {
                "header": header_name,
                "title": title,
                "author": author,
                "text": section_text,
            }
        )
    return sections
