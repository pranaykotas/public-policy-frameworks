#!/usr/bin/env python3
"""
Move framework images from the top of the body (after card-meta) into the 
'What it says' section where the visual diagram/chart belongs.
"""

import re
from pathlib import Path

ROOT = Path("/Users/pranay-karma/Projects/frameworks")

def fix_file(f):
    text = f.read_text()
    # Find the image markdown we inserted
    img_pattern = r'(::: \{\.card-meta\}\n.*?\n:::)\n\n(!\[.*?\]\(.*?\)\{.*?\})\n\n'
    m = re.search(img_pattern, text, re.DOTALL)
    if not m:
        # Try without the extra blank line
        img_pattern2 = r'(::: \{\.card-meta\}\n.*?\n:::)\n(!\[.*?\]\(.*?\)\{.*?\})\n\n'
        m = re.search(img_pattern2, text, re.DOTALL)
        if not m:
            return False, "image not found at top"
    
    card_meta_block = m.group(1)
    image_md = m.group(2)
    
    # Remove image from after card-meta
    text_without_img = text.replace(m.group(0), card_meta_block + "\n\n", 1)
    
    # Find "## What it says" and insert image after it
    # Look for the heading followed by content
    what_it_says_pattern = r'(## What it says\n\n)'
    if not re.search(what_it_says_pattern, text_without_img):
        return False, "no 'What it says' section"
    
    # Insert image after the heading, before the first paragraph
    new_text = re.sub(what_it_says_pattern, r'\1' + image_md + '\n\n', text_without_img, count=1)
    
    if new_text == text_without_img:
        return False, "insert failed"
    
    f.write_text(new_text)
    return True, "moved"

for f in ROOT.rglob("*.qmd"):
    name = f.name
    if name == "index.qmd" or name == "about.qmd" or name == "find-framework.qmd":
        continue
    if "_site" in str(f) or ".quarto" in str(f):
        continue
    
    ok, msg = fix_file(f)
    if ok:
        print(f"FIXED: {f.relative_to(ROOT)}")
    elif msg != "image not found at top":
        print(f"SKIP ({msg}): {f.relative_to(ROOT)}")
