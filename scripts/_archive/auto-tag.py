#!/usr/bin/env python3
"""
Auto-tag all framework .qmd files with tags and use_cases from the controlled vocabulary.
Uses keyword heuristics based on title, summary, and body content.
"""

import re, yaml
from pathlib import Path

ROOT = Path("/Users/pranay-karma/Projects/frameworks")
CATEGORIES = ["public-policy", "political-thinking", "public-finance",
              "foreign-policy-defence-geopolitics", "society", "universe"]

TAG_KEYWORDS = {
    "problem-definition": ["problem", "define", "definition", "wicked", "tame", "diagnose", "condition", "status"],
    "causality": ["causal", "cause", "narrative", "explain", "mechanism", "why", "because", "reason"],
    "incentives": ["incentive", "motivate", "reward", "penalty", "payoff", "game", "dilemma", "prisoner", "agent"],
    "institutions": ["institution", "organis", "bureaucr", "state capacity", "governance", "rules", "norms", "structure"],
    "federalism": ["federal", "state", "centre", "local", "municipal", "panchayat", "devolution", "fiscal transfer"],
    "trade": ["trade", "tariff", "import", "export", "supply chain", "decoupling", "economic strategy"],
    "security": ["security", "defence", "military", "war", "conflict", "terror", "deter", "strategic", "nuclear"],
    "narrative": ["narrative", "story", "framing", "window", "overton", "discourse", "public opinion", "media"],
    "political-economy": ["political economy", "interest group", "lobby", "vote", "election", "coalition", "rent", "capture"],
    "implementation": ["implement", "pipeline", "stage", "delivery", "last mile", "bureaucracy", "administration"],
    "evaluation": ["evaluat", "assess", "outcome", "output", "measure", "metric", "success", "failure", "taxonomy"],
    "design": ["design", "instrument", "target", "tool", "mechanism", "architecture", "blueprint"],
    "behaviour": ["behavio", "psycholog", "cognitive", "bias", "norm", "social", "nudge", "rational"],
    "international-relations": ["international", "diploma", "foreign", "global order", "alliance", "treaty", "geopolitic"],
    "state-capacity": ["state capacity", "capability", "ability", "perform", "weak state", "strong state"],
    "morality": ["moral", "ethic", "value", "ideology", "belief", "religion", "prohibition", "norm"],
    "technology": ["technolog", "innovation", "digital", "internet", "social media", "platform", "data"],
    "inequality": ["inequal", "equity", "fair", "justice", "distribution", "poverty", "disparity"],
    "unintended-consequences": ["unintended", "consequence", "side effect", "second order", "externalit", "spillover"],
    "decision-making": ["decision", "choice", "trade-off", "option", "optimis", "rationa", "bound"],
}

def extract_yaml(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if m:
        try:
            return yaml.safe_load(m.group(1))
        except Exception:
            pass
    return {}

def score_tags(title, summary, body):
    text = f"{title} {summary} {body[:2000]}".lower()
    scores = {}
    for tag, keywords in TAG_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text:
                score += 1
        scores[tag] = score
    # Pick top 3-4 tags
    sorted_tags = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    selected = []
    for tag, score in sorted_tags:
        if score > 0 and len(selected) < 4:
            selected.append(tag)
    return selected

def generate_use_cases(title, summary, body):
    """Generate 2-3 use case sentences based on content."""
    text = f"{title}. {summary} {body[:1500]}"
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('>') and not l.strip().startswith('`')]
    
    use_cases = []
    # Try to extract from first meaningful paragraph
    for line in lines[:10]:
        if len(line) > 30 and len(line) < 300:
            # Convert to "When..." form
            if use_cases:
                break
    
    # Fallback: generate generic use cases from title/summary
    t = title.lower()
    s = summary.lower()
    
    if "problem" in t or "problem" in s:
        use_cases.append(f"When diagnosing whether a situation qualifies as the type of problem this framework addresses.")
    if "trade-off" in t or "trade-off" in s:
        use_cases.append(f"When forced to choose between competing policy objectives with no clean win-win.")
    if "incentive" in t or "incentive" in s:
        use_cases.append(f"When designing or evaluating a policy whose effectiveness hinges on how people respond to rewards and penalties.")
    if "institution" in t or "institution" in s or "state" in t:
        use_cases.append(f"When assessing whether an organisation or state structure has the capacity to deliver on its mandate.")
    if "narrative" in t or "narrative" in s or "story" in s:
        use_cases.append(f"When crafting or critiquing the public story around a policy proposal.")
    if "implement" in t or "implement" in s or "pipeline" in t:
        use_cases.append(f"When a policy looks good on paper but fails to produce results on the ground.")
    if "evaluation" in t or "assess" in s or "outcome" in s:
        use_cases.append(f"When judging whether a policy has succeeded, failed, or produced mixed results.")
    if "design" in t or "instrument" in t:
        use_cases.append(f"When choosing which policy tool to deploy for a given objective.")
    if "international" in t or "foreign" in t or "geopolitic" in s:
        use_cases.append(f"When analyzing how states interact, compete, or cooperate in the international system.")
    if "security" in t or "defence" in t or "strategic" in t:
        use_cases.append(f"When thinking about national security, deterrence, or the use of military and strategic assets.")
    if "federal" in t or "decentralis" in t:
        use_cases.append(f"When navigating the division of powers and resources between national and sub-national governments.")
    if "inequal" in t or "equity" in s:
        use_cases.append(f"When debating what fairness means in the distribution of resources, opportunities, or outcomes.")
    if "behavio" in t or "cognitive" in t or "psycholog" in s:
        use_cases.append(f"When predicting or explaining why individuals and groups make seemingly irrational policy choices.")
    if "technology" in t or "innovation" in s or "digital" in s:
        use_cases.append(f"When assessing how technological change affects policy options and constraints.")
    if "moral" in t or "ethic" in s or "ideology" in s:
        use_cases.append(f"When policy debates turn on questions of values, beliefs, or ideological commitments.")
    if "unintended" in t or "consequence" in s:
        use_cases.append(f"When anticipating what could go wrong after a policy is implemented.")
    if "causal" in t or "cause" in s:
        use_cases.append(f"When constructing or testing explanations for why a policy problem exists.")
    if "decision" in t or "choice" in s:
        use_cases.append(f"When making or justifying a policy choice under uncertainty or competing pressures.")
    if "trade" in t or "econom" in s:
        use_cases.append(f"When analyzing cross-border economic flows, supply chains, or strategic trade policy.")
    if "tax" in t or "budget" in s or "fiscal" in s or "finance" in s:
        use_cases.append(f"When thinking about public revenue, expenditure, debt, or fiscal sustainability.")
    
    # If still empty, generic fallback
    if not use_cases:
        use_cases.append(f"When applying the {title} framework to a policy problem in its domain.")
        use_cases.append(f"When teaching or communicating how {title.lower()} shapes policy thinking.")
    
    return use_cases[:3]

def process_file(path):
    text = path.read_text()
    fm = extract_yaml(text)
    if not fm.get("title"):
        return False
    
    # Skip if already tagged
    if "tags" in fm and "use_cases" in fm:
        print(f"SKIP (already tagged): {path.name}")
        return False
    
    title = fm.get("title", "")
    summary = fm.get("summary", "")
    body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)
    
    tags = score_tags(title, summary, body)
    use_cases = generate_use_cases(title, summary, body)
    
    if not tags:
        tags = ["problem-definition"]  # default
    
    # Update YAML
    # Find the end of the frontmatter and insert before it
    old_yaml = re.match(r'^(---\s*\n.*?)(\n---\s*\n)', text, re.DOTALL)
    if not old_yaml:
        return False
    
    yaml_text = old_yaml.group(1)
    # Add tags and use_cases before the closing ---
    tag_lines = "\n".join([f"  - {t}" for t in tags])
    use_lines = "\n".join([f"  - \"{u}\"" for u in use_cases])
    new_yaml = yaml_text + f"\ntags:\n{tag_lines}\nuse_cases:\n{use_lines}"
    new_text = text.replace(old_yaml.group(0), new_yaml + "\n---\n", 1)
    
    path.write_text(new_text)
    print(f"TAGGED: {path.name} -> {tags}")
    return True

def main():
    total = 0
    for cat in CATEGORIES:
        cat_dir = ROOT / cat
        for f in cat_dir.glob("*.qmd"):
            if f.name == "index.qmd":
                continue
            if process_file(f):
                total += 1
    print(f"\nTagged {total} frameworks.")

if __name__ == "__main__":
    main()
