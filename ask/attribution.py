from __future__ import annotations

import re

KNOWN_HEADERS = (
    "India Policy Watch",
    "Global Policy Watch",
    "World Policy Watch",
    "World Politics Watch",
    "Matsyanyaaya",
    "PolicyWTF",
    "PolicyWTFs",
    "PolicWTF",
    "Not(PolicyWTF)",
    "Not a PolicyWTF",
    "Global PolicyWTF",
    "PolicyWTF (revisited)",
    "PolicyFTW",
    "A Framework a Week",
    "A Framework A Week",
    "Lights, Camera, (Policy Precedes) Action",
    "Another Perspective",
    "A Counter-view",
    "Book Review",
    "Numbers that Ought to Matter",
    "A Sixth Of Humanity",
    "Prof AISH",
    "Quiz",
    "Homework",
    "HomeWork",
    "Course reminder",
    "Money Quote",
    "Flashback",
    "Bonus",
    "AIforPublicPolicy",
    "Poetry In Public Policy",
    "Announcement",
)

BOUNDARY_HEADERS = (
    "HomeWork",
    "Homework",
    "Leave a comment",
    "Share Anticipating the Unintended",
    "Share",
    "Subscribe now",
)

_header_alts = "|".join(re.escape(h) for h in sorted(KNOWN_HEADERS, key=len, reverse=True))
SECTION_HEADER_PATTERN = re.compile(
    rf"^({_header_alts})(?:\s*#\d+)?:\s+([A-Z][^\n]{{3,80}})", re.MULTILINE
)

_boundary_alts = "|".join(re.escape(h) for h in sorted(BOUNDARY_HEADERS, key=len, reverse=True))
BOUNDARY_PATTERN = re.compile(
    rf"^({_boundary_alts})\s*$", re.MULTILINE
)

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
    matches = list(SECTION_HEADER_PATTERN.finditer(body_text))
    boundaries = list(BOUNDARY_PATTERN.finditer(body_text))
    all_breaks = [(m.start(), "header", m) for m in matches] + \
                 [(b.start(), "boundary", b) for b in boundaries]
    all_breaks.sort(key=lambda x: x[0])

    sections = []
    for i, m in enumerate(matches):
        header_name = m.group(1).strip()
        title = m.group(2).strip()
        start = m.end()
        # End at next header OR next boundary, whichever comes first
        next_breaks = [pos for pos, _, _ in all_breaks if pos > m.start()]
        end = next_breaks[0] if next_breaks else len(body_text)
        section_text = body_text[start:end].strip()

        if len(section_text) < MIN_SECTION_LENGTH:
            continue

        # Signature appears at top of section, within first 300 chars
        top_text = section_text[:300]
        sig_match = SIGNATURE_PATTERN.search(top_text)
        author = classify_signature(sig_match.group(1)) if sig_match else "Joint"
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
