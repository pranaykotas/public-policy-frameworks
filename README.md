# Frameworks for Public Policy

Source for [frameworks.pranaykotas.com](https://frameworks.pranaykotas.com), a companion site to [publicpolicy.substack.com](https://publicpolicy.substack.com).

A growing reference of public policy frameworks, each with origin, explanation, an applied example, limitations, and links to original sources. Curated and explained by Pranay Kotasthane from a decade of writing in *Anticipating the Unintended*.

## Stack

- [Quarto](https://quarto.org) — static site generator
- Plain Markdown (`.qmd`) cards, one per framework
- Built-in Quarto listing pages with filter + search

No automation, no scraper, no build pipeline beyond `quarto render`.

## Local development

Install Quarto (https://quarto.org/docs/get-started/), then:

```bash
quarto preview     # live-reloading local server on http://localhost:4848
quarto render      # build static site into _site/
```

## Project layout

```
.
├── _quarto.yml                                 # site config
├── index.qmd                                   # homepage
├── about.qmd                                   # about / how to read this site
├── _stubs.qmd                                  # frameworks not yet written as full cards
├── styles.scss                                 # custom styling
├── public-policy/
│   ├── index.qmd                               # category landing page
│   ├── wicked-problems.qmd
│   ├── ooo.qmd
│   └── ...
├── political-thinking/
├── public-finance/
├── foreign-policy-defence-geopolitics/
├── society/
└── universe/
```

## Adding a new card

1. Pick the right category folder.
2. Copy an existing card (e.g., `public-policy/wicked-problems.qmd`) as a template.
3. Fill the frontmatter:

```yaml
---
title: "Framework Name"
summary: "One-line description that shows up in listings."
categories: [Category Name]
date: 2026-MM-DD
---
```

4. Use the standard sections: Origin → What it says → Applied → When it falls short → Related frameworks → Further reading → Attribution.
5. Move the framework's stub entry out of `_stubs.qmd` (so it does not appear twice).
6. `quarto preview` to check, commit, push.

## Deployment

The site is deployed to **frameworks.pranaykotas.com** as a subdomain of `pranaykotas.com`.

### One-time setup

1. **Choose a host.** Recommended: GitHub Pages (free, simple) or Netlify (free tier, automatic builds from git).

2. **GitHub Pages route**
   - Push this repo to GitHub.
   - In repo Settings → Pages, set the source to GitHub Actions.
   - Add a workflow at `.github/workflows/quarto-publish.yml` (use Quarto's official template: https://quarto.org/docs/publishing/github-pages.html).
   - In repo Settings → Pages, set the custom domain to `frameworks.pranaykotas.com` and tick "Enforce HTTPS" once the cert provisions.
   - Add a `CNAME` file at the repo root containing `frameworks.pranaykotas.com`.

3. **Netlify route**
   - Connect the repo, set build command to `quarto render` and publish directory to `_site`.
   - In Netlify Domain settings, add `frameworks.pranaykotas.com`.

4. **DNS**
   At your domain registrar for `pranaykotas.com`, add a CNAME record:
   ```
   Type:  CNAME
   Name:  frameworks
   Value: <username>.github.io        # for GitHub Pages
          <site-name>.netlify.app     # for Netlify
   TTL:   3600
   ```
   Propagation usually takes 10 minutes to a few hours.

### Subsequent updates

Push to `main`. The build runs automatically and the site updates within a couple of minutes.

## Style and editorial conventions

- **Voice.** First person plural is fine; first person singular sparingly. Direct, declarative. No throat-clearing.
- **Citations.** Every framework needs an origin paper or book named on the card. If the source is uncertain, say so — never invent.
- **Co-authors.** When a newsletter post is co-written with RSJ or another collaborator, name them in the closing attribution line.
- **Length.** 500–900 words per card. Long enough to be useful, short enough to scan.
- **Indian examples.** Preferred, but not required. Use the example that best illuminates the framework, regardless of geography.

## Companion to Substack

The newsletter remains the long-form home of these ideas. The site is the structured reference. There is no automated link between the two — when you write a new "Framework a Week" post on Substack, write the card here as a parallel exercise, not a downstream one.
