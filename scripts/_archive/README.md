# Archived one-shot import scripts

These scripts were used during the initial import of newsletter content into this site.
They are kept here for reference but are not part of the normal build.

| Script | What it did |
|--------|-------------|
| `scrape-newsletter.py` | Fetched Substack posts via RSS/API and saved raw HTML |
| `fetch-posts.py` | Downloaded individual post HTML from Substack |
| `fetch-images.py` | Scraped and downloaded framework diagram images from posts |
| `generate-stubs.py` | Generated skeleton .qmd files from a list of framework titles |
| `generate-missing-stubs.py` | Re-ran stub generation for titles not yet in the site |
| `extract-framework-sections.py` | Parsed raw HTML and extracted framework sections into qmd structure |
| `extract-missing-frameworks.py` | Found frameworks in newsletter not yet imported |
| `add-images-to-body.py` | Added image embeds inside the "What it says" section of existing qmds |
| `fix-image-placement.py` | Moved misplaced image embeds to the correct section |
| `assign-default-images.py` | Assigned category-default images to qmds missing a specific image |
| `generate-defaults.py` | Generated the category default images in images/defaults/ |
| `auto-tag.py` | Bulk-assigned tags and use_cases using keyword heuristics |

For the ongoing build pipeline, use `../build.sh` instead.
