#!/usr/bin/env python3
"""
One-shot script: rewrite "Related frameworks" external Substack links to internal
relative links where a matching framework page exists on this site.

Match logic: slugify the link label → find best-matching .qmd stem using shared
words. Substack post URLs are not used for matching (they contain the full post
title, not the framework name). Falls back to keeping the Substack URL with
" (newsletter)" suffix.

Run once, then archive: python3 scripts/relink-related.py
"""

import re, yaml
from pathlib import Path

ROOT = Path(__file__).parent.parent
CATEGORIES = ["public-policy", "political-thinking", "public-finance",
              "foreign-policy-defence-geopolitics", "society", "universe"]

STOP = {'a','an','the','and','for','of','to','in','on','at','by','from',
        'with','as','is','are','was','were','be','been','or','but','not',
        'its','it','this','that','how','what','when','why','who','which'}

def extract_title(qmd_path):
    text = qmd_path.read_text()
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if m:
        try:
            fm = yaml.safe_load(m.group(1))
            return fm.get('title', '')
        except Exception:
            pass
    return ''

def tokenise(s):
    words = re.sub(r'[^\w\s]', ' ', s.lower()).split()
    return {w for w in words if w not in STOP and len(w) > 2}

# Build title-tokens → (cat, filename) map
title_map = []  # list of (tokens, cat, stem)
for cat in CATEGORIES:
    for qmd in (ROOT / cat).glob('*.qmd'):
        if qmd.name == 'index.qmd':
            continue
        title = extract_title(qmd)
        if title:
            tokens = tokenise(title)
            title_map.append((tokens, cat, qmd.name))
        # Also index by stem tokens as fallback
        stem_tokens = tokenise(qmd.stem.replace('-', ' '))
        title_map.append((stem_tokens, cat, qmd.name))

def find_best_match(label):
    label_tokens = tokenise(label)
    if not label_tokens:
        return None
    best_score = 0
    best_match = None
    for tokens, cat, fname in title_map:
        shared = label_tokens & tokens
        if not shared:
            continue
        # Jaccard-like: shared / union, weighted by label coverage
        score = len(shared) / len(label_tokens | tokens) + len(shared) / len(label_tokens) * 0.5
        if score > best_score:
            best_score = score
            best_match = (cat, fname)
    # Require reasonable confidence
    return best_match if best_score > 0.4 else None

def make_relative_link(from_cat, to_cat, filename):
    if from_cat == to_cat:
        return filename
    return f'../{to_cat}/{filename}'

changed_files = [0]
changed_links = [0]
kept_external = [0]

for cat in CATEGORIES:
    for qmd in sorted((ROOT / cat).glob('*.qmd')):
        if qmd.name == 'index.qmd':
            continue
        text = qmd.read_text()

        def rewrite_link(lm, _cat=cat):
            label = lm.group(1)
            url   = lm.group(2)
            if 'substack.com' not in url:
                return lm.group(0)  # already non-Substack
            # Strip " (newsletter)" suffix if present for cleaner matching
            clean_label = re.sub(r'\s*\(newsletter\)\s*$', '', label).strip()
            match = find_best_match(clean_label)
            if match:
                to_cat, fname = match
                rel = make_relative_link(_cat, to_cat, fname)
                changed_links[0] += 1
                return f'[{clean_label}]({rel})'
            # No match — keep external, ensure " (newsletter)" suffix
            kept_external[0] += 1
            if '(newsletter)' not in label:
                return f'[{label} (newsletter)]({url})'
            return lm.group(0)

        def rewrite_related_section(m):
            return re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', rewrite_link, m.group(0))

        new_text = re.sub(
            r'^## Related frameworks\s*\n.*?(?=^## |\Z)',
            rewrite_related_section,
            text,
            flags=re.MULTILINE | re.DOTALL
        )

        if new_text != text:
            qmd.write_text(new_text)
            changed_files[0] += 1

print(f'Rewrote {changed_links[0]} links to internal → across {changed_files[0]} files.')
print(f'Kept {kept_external[0]} external (no match found).')
print('Done. Move to archive: mv scripts/relink-related.py scripts/_archive/')
