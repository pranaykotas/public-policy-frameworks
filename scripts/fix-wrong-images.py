#!/usr/bin/env python3
"""Remove wrong scraped images from framework pages, replacing with category defaults."""
import re
import os
from pathlib import Path

DEFAULTS = {
    'public-policy': 'images/defaults/public-policy.png',
    'political-thinking': 'images/defaults/political-thinking.png',
    'public-finance': 'images/defaults/public-finance.png',
    'foreign-policy-defence-geopolitics': 'images/defaults/foreign-policy-defence-geopolitics.png',
    'society': 'images/defaults/society.png',
    'universe': 'images/defaults/universe.png',
}

TO_FIX = [
    ('public-policy', 'anticipating-unintended-policy-consequences'),
    ('public-policy', 'complexity-and-public-policy'),
    ('public-policy', 'eight-things-to-unlearn-before-learning-public-policy'),
    ('public-policy', 'four-components-of-an-economic-strategy'),
    ('public-policy', 'good-policy-problem-definition'),
    ('public-policy', 'hyper-multi-objective-optimisation'),
    ('public-policy', 'one-instrument-one-target'),
    ('public-policy', 'opportunity-cost-neglect'),
    ('public-policy', 'policies-vs-programmes-vs-practices'),
    ('public-policy', 'public-policy-solutionism'),
    ('public-policy', 'seven-stages-policy-pipeline'),
    ('public-policy', 'sunset-clauses'),
    ('public-policy', 'two-is-better-than-one'),
    ('public-policy', 'when-conditions-become-policy-problems'),
    ('political-thinking', 'cognitive-maps'),
    ('political-thinking', 'confronting-trade-offs'),
    ('political-thinking', 'kingdon-three-streams'),
    ('political-thinking', 'overton-window'),
    ('political-thinking', 'political-policymaking'),
    ('political-thinking', 'rules-for-political-survival'),
    ('political-thinking', 'stakeholder-management-in-public-policy'),
    ('political-thinking', 'what-makes-a-good-narrative'),
    ('political-thinking', 'why-weak-dictators-get-softer-loans'),
    ('political-thinking', 'wilson-interest-group-matrix'),
    ('public-finance', 'a-taxing-month-ahead'),
    ('public-finance', 'a-useful-thumb-rule'),
    ('public-finance', 'algorithm-for-fiscal-federalism'),
    ('public-finance', 'marginal-cost-of-public-finance'),
    ('foreign-policy-defence-geopolitics', 'a-taxonomy-of-defence-innovation'),
    ('foreign-policy-defence-geopolitics', 'decoupling-dynamics'),
    ('foreign-policy-defence-geopolitics', 'describing-state-policy-on-geopolitical-issues'),
    ('foreign-policy-defence-geopolitics', 'dictatorship-and-democracy-in-israel-and-pakistan'),
    ('foreign-policy-defence-geopolitics', 'how-to-deter-reasonable-people-from-undesirable-behaviour'),
    ('foreign-policy-defence-geopolitics', 'hypocrisy-in-international-relations'),
    ('foreign-policy-defence-geopolitics', 'ingredients-of-a-new-world-order'),
    ('foreign-policy-defence-geopolitics', 'paradoxes-of-indias-westernophobia'),
    ('foreign-policy-defence-geopolitics', 'three-schools-of-thought-on-indiaus-relations'),
    ('society', 'building-digital-communities'),
    ('society', 'defence-against-the-dark-arts-in-the-information-age'),
    ('society', 'how-social-norms-flip'),
    ('society', 'how-to-analyse-an-analysis'),
    ('society', 'internet-and-politics'),
    ('society', 'terrorism-poverty-and-education'),
    ('society', 'the-right-wrong-of-ages-past'),
    ('society', 'the-state-and-the-society'),
    ('society', 'three-truths-of-ideology'),
    ('society', 'we-hate-cognitive-dissonance'),
    ('society', 'what-the-census-reveals-about-state-and-society'),
    ('society', 'why-large-whatsapp-groups-are-so-ineffective'),
    ('society', 'why-we-do-stupid-things-in-groups'),
    ('universe', 'building-models'),
    ('universe', 'hal-varians-tips-on-building-an-economic-model'),
    ('universe', 'how-to-build-a-good-2x2-matrix'),
    ('universe', 'inter-state-water-sharing'),
    ('universe', 'moralising-is-central-to-storytelling'),
    ('universe', 'social-medias-rule-of-three'),
    ('universe', 'the-impossible-trinity-of-indian-cities'),
    ('universe', 'what-s-easy-what-s-not'),
]

base = str(Path(__file__).parent.parent)
fixed = 0
not_found = 0

for category, slug in TO_FIX:
    fpath = os.path.join(base, category, f'{slug}.qmd')
    if not os.path.exists(fpath):
        print(f'NOT FOUND: {category}/{slug}.qmd')
        not_found += 1
        continue

    with open(fpath) as f:
        content = f.read()

    default_img = DEFAULTS[category]

    # Replace front-matter image line
    content = re.sub(r'^image:.*$', f'image: "{default_img}"', content, flags=re.MULTILINE)

    # Remove body image embed lines (handles webp and png, with or without {attrs})
    content = re.sub(r'!\[[^\]]*\]\(\.\./images/[^)]+\)(\{[^}]*\})?\n?', '', content)

    with open(fpath, 'w') as f:
        f.write(content)

    print(f'Fixed: {category}/{slug}')
    fixed += 1

print(f'\nDone. Fixed: {fixed}, Not found: {not_found}')
