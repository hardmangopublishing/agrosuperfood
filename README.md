# agrosuperfood.com

A flat static site. No build toolchain, no Node, no npm, no package manager.
Every file sits in one folder so the whole thing can be dropped into a GitHub
repository and served by GitHub Pages with no configuration.

## Putting it live

1. Create a new GitHub repository.
2. Upload every file in this zip to the root of the repository. Do not create folders.
3. Repository **Settings** then **Pages**. Under **Source** choose **Deploy from a branch**, branch `main`, folder `/ (root)`. Save.
4. Wait a minute. The site appears at `https://YOURNAME.github.io/REPONAME/`.
5. For the custom domain: still under **Pages**, enter `agrosuperfood.com` in **Custom domain**. At your registrar, point the apex A records at GitHub's Pages IP addresses and add a `www` CNAME to `YOURNAME.github.io`. GitHub's current IP list is in their Pages documentation. Tick **Enforce HTTPS** once the certificate provisions.

The `CNAME` file in this zip already contains the domain. The `.nojekyll` file
stops GitHub running Jekyll over the folder, which it otherwise does by default.

## Before you publish

Two things are deliberately unfinished and both are one-line edits.

**Associates tag.** Already set to `peteragro-20` in `products.json`. To change it, edit
that one field; it is the only place the tag appears.

**ASINs are live.** All ten products carry real ASINs. `products.json` is the
single source of truth, and the gate fails the build if an ASIN or tag appears
in any hand-edited source file.

To place a link in an article, write `{{product:led-grow-bar}}` in the markdown.
The builder renders it as a tagged link with `rel="sponsored nofollow noopener"`.
The gate fails if a token names a product that does not exist or has no live ASIN.

Product images must come from official SiteStripe or Product Advertising API
output only. Never hotlink Amazon-hosted images and never redraw them. Verify
the current Associates operating agreement before launch, since the terms and
the fee schedule both change.

## Editing

Content lives in the `src-*.md` files. Edit those, never the `.html` files,
which are generated and will be overwritten.

```
python3 build.py       # regenerates every .html, plus sitemap.xml and robots.txt
python3 preflight.py   # runs every gate; exit 0 means safe to push
```

Run `preflight.py` before every push. It exits non-zero on any defect and will
tell you exactly which file and which rule.

## What the gate checks

| Gate | Rule |
|---|---|
| Word floor | Hubs 3,300 words. Spokes 1,700. |
| Em dashes | Zero. Spaced en dashes also fail, since substituting one for the other is the same tic in disguise. |
| Banned filler | Twenty stock phrases fail the build outright. |
| Prose budget | Bare emphasis italics, "not X but Y", explanatory similes and hedged descriptors, each capped per 10,000 words. |
| Link geometry | Every spoke carries exactly one up-link to its hub and exactly two sibling links. |
| Dead links | Every local href and src must resolve to a file that exists. |
| Disclosure | Affiliate disclosure present on every built page. |
| Affiliate rails | No ASIN or tag outside `products.json`. No Amazon-hosted imagery. |
| Illustrations | Every SVG needs a viewBox, a title, a desc, and unique alt text in `illustrations.json`. Fifteen kilobyte ceiling each, sixty per page. |
| Structured data | Article JSON-LD and a lang attribute on every page. |
| Headings | Exactly one h1 per page, and no empty eyebrow or standfirst elements. |

`python3 preflight.py --final` additionally enforces the complete six hub and
sixty spoke build. It will fail until the site is finished, which is the point.

## Current status

55 pages, 107,200 words, 14 illustrations, 32 products linked. All gates green.

Live: the sprouting, juicing, dehydrating, fermenting, and powders hubs, each
with all ten guides.

Next: the home grain milling hub.

## Illustration system

Hand-authored SVG, checked in as code rather than generated as raster. One rule
governs the whole set: terracotta marks what is alive or changing, deep green
marks structure. Every diagram obeys it, which is why five separate drawings
read as one system.

## Content rails

Every dollar figure is illustrative and carries a disclaimer. Health claims stay
at pattern level with verify-current-guidance framing. Where a specific number
could not be sourced, the article says so rather than inventing one. Three such
claims are listed in the `verify:` block of the relevant markdown frontmatter and
need sources attached before publication.
