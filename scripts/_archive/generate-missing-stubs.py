#!/usr/bin/env python3
"""
Generates stub .qmd files for missing frameworks extracted from the newsletter.
Reads cached .txt files and creates proper frontmatter + brief body.
"""

import re, json, yaml
from pathlib import Path

ROOT = Path("/Users/pranay-karma/Projects/frameworks")
CACHE_DIR = ROOT / ".cache/posts"

CATEGORIES = ["public-policy", "political-thinking", "public-finance",
              "foreign-policy-defence-geopolitics", "society", "universe"]

# Map framework slugs to categories based on content analysis
CATEGORY_MAP = {
    "a-taxonomy-of-defence-innovation": "foreign-policy-defence-geopolitics",
    "rules-for-political-survival": "political-thinking",
    "sunset-clauses": "public-policy",
    "a-covid-19-vaccine-deployment-strategy-for-india": "public-policy",
    "no-more-cop-outs": "public-policy",
    "what-makes-a-policy-chance-stick": "public-policy",
    "the-purva-paksha-debate": "political-thinking",
    "instruments-of-technology-geopolitics": "foreign-policy-defence-geopolitics",
    "two-is-better-than-one": "public-policy",
    "the-right-wrong-of-ages-past": "society",
    "we-hate-cognitive-dissonance": "society",
    "a-taxing-month-ahead": "public-finance",
    "social-norms-and-public-policy": "society",
    "norm-flipping": "society",
    "a-useful-thumb-rule": "public-finance",
    "understanding-cognitive-maps": "political-thinking",
    "when-do-conditions-become-problems": "public-policy",
    "how-to-anticipate-the-unintended": "public-policy",
    "internet-politics": "society",
    "the-domar-rule-for-public-debt-sustainability": "public-finance",
    "wilson-s-interest-group-ig-matrix": "political-thinking",
    "kingdon-s-three-streams-schema": "political-thinking",
    "describing-a-state-s-policy-on-a-geopolitical-issue": "foreign-policy-defence-geopolitics",
    "guns-butter": "foreign-policy-defence-geopolitics",
    "errors-of-omission-and-commission-how-vlsi-relates-to-subsidies": "public-policy",
    "a-taxonomy-of-policy-failures-and-policy-successes": "public-policy",
    "the-three-binding-constraints-on-technological-progress": "universe",
    "conceptualising-opportunity-cost-neglect": "public-policy",
    "terrorism-poverty-education": "society",
    "how-to-deter-reasonable-people-from-engaging-in-undesirable-behaviour": "universe",
    "china-s-predicament": "foreign-policy-defence-geopolitics",
    "policies-programmes-and-practices": "public-policy",
    "things-governments-do": "public-policy",
    "8-things-to-unlearn-before-learning-public-policy": "public-policy",
    "the-overton-window": "political-thinking",
    "seven-stages-of-the-policy-pipeline": "public-policy",
    "what-made-the-us-enable-china-s-rise": "foreign-policy-defence-geopolitics",
    "hal-varian-s-tips-on-building-an-economic-model": "universe",
    "responding-to-the-standoff-on-the-lac-in-ladakh": "foreign-policy-defence-geopolitics",
}

# Skip ones that are clearly duplicates of existing well-covered frameworks
SKIP = {
    "the-overton-window",  # same as overton-window
    "the-domar-rule-for-public-debt-sustainability",  # same as domar-rule
    "wilson-s-interest-group-ig-matrix",  # same as wilson-interest-group-matrix
    "kingdon-s-three-streams-schema",  # same as kingdon-three-streams
    "describing-a-state-s-policy-on-a-geopolitical-issue",  # same as describing-state-policy-on-geopolitical-issues
    "guns-butter",  # same as guns-and-butter
    "errors-of-omission-and-commission-how-vlsi-relates-to-subsidies",  # same as errors-of-omission-and-commission
    "a-taxonomy-of-policy-failures-and-policy-successes",  # same as taxonomy-of-policy-failures-and-successes
    "the-three-binding-constraints-on-technological-progress",  # same as three-binding-constraints-tech-progress
    "conceptualising-opportunity-cost-neglect",  # same as opportunity-cost-neglect
    "terrorism-poverty-education",  # same as terrorism-poverty-and-education
    "how-to-deter-reasonable-people-from-engaging-in-undesirable-behaviour",  # same as how-to-deter-reasonable-people-from-undesirable-behaviour
    "china-s-predicament",  # same as chinas-predicament
    "policies-programmes-and-practices",  # same as policies-vs-programmes-vs-practices
    "things-governments-do",  # same as all-things-governments-do
    "8-things-to-unlearn-before-learning-public-policy",  # same as eight-things-to-unlearn-before-learning-public-policy
    "seven-stages-of-the-policy-pipeline",  # same as seven-stages-policy-pipeline
    "what-made-the-us-enable-china-s-rise",  # same as what-made-the-us-enable-chinas-rise
    "hal-varian-s-tips-on-building-an-economic-model",  # same as hal-varians-tips-on-building-an-economic-model
    "responding-to-the-standoff-on-the-lac-in-ladakh",  # same as responding-to-lac-standoff-in-ladakh
    "when-do-conditions-become-problems",  # same as when-conditions-become-policy-problems
    "how-to-anticipate-the-unintended",  # same as anticipating-unintended-policy-consequences
    "internet-politics",  # same as internet-and-politics
    "understanding-cognitive-maps",  # same as cognitive-maps
    "norm-flipping",  # same as how-social-norms-flip
}

TAG_MAP = {
    "a-taxonomy-of-defence-innovation": ["security", "design", "institutions", "technology"],
    "rules-for-political-survival": ["political-economy", "incentives", "institutions", "decision-making"],
    "sunset-clauses": ["design", "evaluation", "institutions", "implementation"],
    "a-covid-19-vaccine-deployment-strategy-for-india": ["implementation", "design", "state-capacity", "evaluation"],
    "no-more-cop-outs": ["evaluation", "design", "trade", "unintended-consequences"],
    "what-makes-a-policy-chance-stick": ["political-economy", "implementation", "institutions", "narrative"],
    "the-purva-paksha-debate": ["decision-making", "narrative", "institutions", "behaviour"],
    "instruments-of-technology-geopolitics": ["security", "technology", "trade", "international-relations"],
    "two-is-better-than-one": ["design", "institutions", "implementation", "state-capacity"],
    "the-right-wrong-of-ages-past": ["morality", "narrative", "institutions", "behaviour"],
    "we-hate-cognitive-dissonance": ["behaviour", "causality", "narrative", "decision-making"],
    "a-taxing-month-ahead": ["federalism", "institutions", "design", "state-capacity"],
    "social-norms-and-public-policy": ["behaviour", "institutions", "design", "implementation"],
    "a-useful-thumb-rule": ["evaluation", "design", "decision-making"],
}

def slugify(title):
    return re.sub(r'[^\w]+', '-', title.lower()).strip('-')

def extract_summary(text):
    """Extract a one-sentence summary from the framework text."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # Skip header lines
    content_lines = []
    for line in lines:
        if re.search(r'A\s+Framework\s+A\s+Week', line, re.IGNORECASE):
            continue
        if line in ["Tools for thinking public policy", "Tools for thinking about public policy", "— Pranay Kotasthane", "— RSJ"]:
            continue
        content_lines.append(line)
    
    # Find first substantial sentence
    for line in content_lines[:10]:
        if len(line) > 40 and len(line) < 300 and line.endswith('.'):
            return line
    
    # Fallback: concatenate first few meaningful lines
    meaningful = [l for l in content_lines[:5] if len(l) > 20]
    if meaningful:
        summary = " ".join(meaningful)
        if len(summary) > 200:
            summary = summary[:197] + "..."
        return summary
    
    return "A framework for thinking about public policy."

def generate_stub(slug, title, category, tags, summary, url):
    cat_display = category.replace("-", " ").title()
    if cat_display == "Foreign Policy Defence Geopolitics":
        cat_display = "Foreign Policy, Defence & Geopolitics"
    
    tag_lines = "\n".join([f"  - {t}" for t in tags])
    
    body = f"""---
title: "{title}"
summary: "{summary}"
categories: [{cat_display}]
date: 2026-05-03
---

::: {{.card-meta}}
[{cat_display}]{{.badge}} [{tags[0]}]{{.badge}} [{tags[1]}]{{.badge}}
:::

> {summary}

## Origin

This framework was explored in the *Anticipating the Unintended* newsletter.

## What it says

This framework helps think about {tags[0]} and {tags[1]} in the context of {cat_display.lower()}.

## Applied

- When analyzing policy problems in this domain.
- When designing interventions that account for institutional constraints.

## When it falls short

- When the context is too specific to generalise.
- When data needed to apply the framework is unavailable.

## Related frameworks

- [[Wicked Problems]](../public-policy/wicked-problems.qmd)

## Further reading

- [Original newsletter essay]({url})

---

*Source: [Anticipating the Unintended](https://publicpolicy.substack.com) newsletter.*
"""
    return body

def main():
    with open(ROOT / ".cache/scrape-results.json") as f:
        data = json.load(f)
    
    created = 0
    for m in data["missing_frameworks"]:
        slug = m["slug"]
        if slug in SKIP:
            print(f"SKIP (dupe): {m['title']}")
            continue
        
        cache_file = CACHE_DIR / f"{slug}.txt"
        if not cache_file.exists():
            print(f"SKIP (no cache): {m['title']}")
            continue
        
        text = cache_file.read_text()
        if len(text) < 500:
            print(f"SKIP (too short): {m['title']} ({len(text)} chars)")
            continue
        
        category = CATEGORY_MAP.get(slug, "universe")
        tags = TAG_MAP.get(slug, ["problem-definition", "design"])
        summary = extract_summary(text)
        
        out_dir = ROOT / category
        out_file = out_dir / f"{slug}.qmd"
        
        # Don't overwrite existing files
        if out_file.exists():
            print(f"SKIP (exists): {slug}")
            continue
        
        body = generate_stub(slug, m["title"], category, tags, summary, m["url"])
        out_file.write_text(body)
        print(f"CREATED: {out_file}")
        created += 1
    
    print(f"\nCreated {created} stub files.")

if __name__ == "__main__":
    main()
