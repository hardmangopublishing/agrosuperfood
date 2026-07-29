#!/usr/bin/env python3
"""
agrosuperfood.com static builder.

Reads every src-*.md in this folder and writes a matching .html beside it,
plus index.html and sitemap.xml. Standard library only: no pip install,
no node, no build toolchain.

    python3 build.py

Everything lives flat in one folder so the whole site can be dragged into a
GitHub repo and served by Pages with no configuration.
"""
import html as H
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://agrosuperfood.com"
BRAND = "agrosuperfood"

BOX_HEADINGS = {
    "run the numbers": "numbers",
    "what goes wrong": "wrong",
    "do this now": "now",
}

DISCLOSURE = (
    "As an Amazon Associate this site earns from qualifying purchases. "
    "Links to products may be affiliate links. This costs you nothing extra "
    "and does not change what gets recommended. Nothing here is medical advice."
)


def linked_disclosure(tag):
    """Same statement, with only the word Amazon carrying the tagged link.
    The tag comes from products.json so it stays single-source."""
    url = f"https://www.amazon.com/?tag={tag}"
    anchor = (f'<a href="{url}" rel="sponsored nofollow noopener" '
              f'target="_blank">Amazon</a>')
    return DISCLOSURE.replace("Amazon Associate", f"{anchor} Associate", 1)


# ----------------------------------------------------------------- frontmatter
def split_front(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    meta, body = {}, m.group(2)
    key = None
    for line in m.group(1).split("\n"):
        if not line.strip():
            continue
        if line.startswith(("  - ", "- ")) and key:
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(line.split("- ", 1)[1].strip().strip('"'))
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()
            if val.startswith("[") and val.endswith("]"):
                meta[key] = [v.strip().strip('"') for v in val[1:-1].split(",") if v.strip()]
            elif val:
                meta[key] = val.strip('"')
            else:
                meta[key] = []
    return meta, body


# ----------------------------------------------------------------- inline
def inline(t):
    t = H.escape(t, quote=False)
    t = product_links(t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", t)
    return t


PRODUCTS = json.load(open(os.path.join(HERE, "products.json"), encoding="utf-8"))
PMAP = {p["id"]: p for p in PRODUCTS["products"]}
TAG = PRODUCTS["tag"]


def product_links(t):
    """Render {{product:id}} as a tagged, rel-sponsored Amazon link.
    ASINs live only in products.json; nothing here is hardcoded."""
    def sub(m):
        pid = m.group(1)
        p = PMAP.get(pid)
        if not p or p["asin"] == "PENDING":
            print(f"  ! product token '{pid}' has no live ASIN; rendered as plain text")
            return p["link_text"] if p else pid
        url = f"https://www.amazon.com/dp/{p['asin']}?tag={TAG}"
        return (f'<a href="{url}" rel="sponsored nofollow noopener" '
                f'target="_blank">{H.escape(p["link_text"])}</a>')
    return re.sub(r"\{\{product:([a-z0-9-]+)\}\}", sub, t)


def figure(key, illos):
    meta = illos.get(key)
    if not meta:
        print(f"  ! figure '{key}' is not in illustrations.json")
        return ""
    return (f'<figure><img src="{key}.svg" alt="{H.escape(meta["alt"], quote=True)}" '
            f'loading="lazy" decoding="async">'
            f'<figcaption>{inline(meta["caption"])}</figcaption></figure>')


# ----------------------------------------------------------------- block parse
def render(body, illos):
    out, i = [], 0
    lines = body.split("\n")
    box = None          # open box class, or None

    def close_box():
        nonlocal box
        if box:
            out.append("</div>")
            box = None

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if not s:
            i += 1
            continue

        if s.startswith("!!fig "):
            close_box()
            out.append(figure(s[6:].strip(), illos))
            i += 1
            continue

        if s.startswith(":::"):
            tag = s[3:].strip()
            if tag:
                close_box()
                out.append(f'<div class="box box-{tag}">')
                box = tag
            else:
                close_box()
            i += 1
            continue

        if s.startswith("#"):
            level = len(s) - len(s.lstrip("#"))
            txt = s.lstrip("#").strip()
            if level == 2 and txt.lower() in BOX_HEADINGS:
                close_box()
                cls = BOX_HEADINGS[txt.lower()]
                out.append(f'<div class="box box-{cls}">'
                           f'<p class="box-label">{H.escape(txt.upper())}</p>')
                box = cls
                i += 1
                continue
            if level > 1:
                close_box()
            out.append(f"<h{level}>{inline(txt)}</h{level}>")
            i += 1
            continue

        # box label as the first line of an explicit ::: block
        if box and s.isupper() and len(s) < 40 and "box-label" not in "".join(out[-1:]):
            out.append(f'<p class="box-label">{H.escape(s)}</p>')
            i += 1
            continue

        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            body_rows = [r for r in rows[1:] if not re.match(r"^:?-+:?$", r[0].replace(" ", ""))]
            th = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
            tb = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                         for r in body_rows)
            out.append(f"<table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table>")
            continue

        if re.match(r"^\d+\.\s", s):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i].strip()):
                items.append(inline(re.sub(r"^\d+\.\s", "", lines[i].strip())))
                i += 1
            out.append("<ol class='plain'>" + "".join(f"<li>{x}</li>" for x in items) + "</ol>")
            continue

        if s.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(inline(lines[i].strip()[2:]))
                i += 1
            out.append("<ul class='plain'>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
            continue

        para = []
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#|\||:::|!!fig|- |\d+\.\s)", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")

    close_box()
    return "\n".join(x for x in out if x)


# ----------------------------------------------------------------- page shell
def shell(meta, content, nav_items, extra_rail=""):
    title = meta.get("title", BRAND)
    desc = meta.get("description", "")
    slug = meta["slug"]
    kind = meta.get("kind", "page")
    eyebrow = {"hub": "Hub", "spoke": "Guide"}.get(kind, "")
    nav = "".join(f'<a href="{s}.html">{t}</a>' for s, t in nav_items)

    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": desc,
        "datePublished": meta.get("updated", str(date.today())),
        "dateModified": meta.get("updated", str(date.today())),
        "mainEntityOfPage": f"{SITE}/{slug}.html",
        "publisher": {"@type": "Organization", "name": BRAND},
    }

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{H.escape(title)} | {BRAND}</title>
<meta name="description" content="{H.escape(desc, quote=True)}">
<link rel="canonical" href="{SITE}/{slug}.html">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@400;600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
<script type="application/ld+json">{json.dumps(schema)}</script>
</head>
<body>
<header class="masthead"><div class="masthead-inner">
  <a class="wordmark" href="index.html">agro<span>super</span>food</a>
  <nav>{nav}</nav>
</div></header>

<main class="sheet">
  {f'<p class="eyebrow">{eyebrow}</p>' if eyebrow else ''}
  <h1>{H.escape(title)}</h1>
  {f'<p class="standfirst">{H.escape(desc)}</p>' if desc else ''}
  <p class="byline">Updated {meta.get("updated", "")}</p>
  <p class="disclosure">{linked_disclosure(TAG)}</p>
  {content}
  {extra_rail}
</main>

<footer class="site"><div>
  <p>{BRAND} &middot; Independent guides to growing and using whole foods at home.</p>
  <p>{linked_disclosure(TAG)}</p>
  <p>Educational content only. Verify current food safety guidance with your national authority before eating any raw sprouted food.</p>
</div></footer>
</body>
</html>
"""


# ----------------------------------------------------------------- build
def main():
    illos = json.load(open(os.path.join(HERE, "illustrations.json"), encoding="utf-8"))
    srcs = sorted(f for f in os.listdir(HERE) if f.startswith("src-") and f.endswith(".md"))
    docs = []
    for f in srcs:
        meta, body = split_front(open(os.path.join(HERE, f), encoding="utf-8").read())
        meta["_src"] = f
        docs.append((meta, body))

    hubs = [d for d in docs if d[0].get("kind") == "hub"]
    spokes = [d for d in docs if d[0].get("kind") == "spoke"]
    nav = [(m["slug"], m["title"].split(",")[0]) for m, _ in hubs]

    print(f"building {len(docs)} page(s)")
    for meta, body in docs:
        # the shell renders the title as h1; drop the body's duplicate
        body = re.sub(r"^\s*#\s+.*?\n", "", body, count=1)
        content = render(body, illos)
        rail = ""
        if meta.get("kind") == "hub":
            kids = [m for m, _ in spokes if m.get("hub") == meta["slug"]]
            if kids:
                li = "".join(
                    f'<li><a href="{k["slug"]}.html">{H.escape(k["title"])}</a>'
                    f'<span class="note">{H.escape(k.get("description", ""))}</span></li>'
                    for k in kids)
                rail = f'<div class="rail"><h2>Guides in this hub</h2><ul>{li}</ul></div>'
        out = shell(meta, content, nav, rail)
        path = os.path.join(HERE, meta["slug"] + ".html")
        open(path, "w", encoding="utf-8").write(out)
        print(f"  wrote {os.path.basename(path)}")

    # ---- index
    cards = ""
    for m, _ in hubs:
        cards += (f'<div class="hubcard"><h3><a href="{m["slug"]}.html">'
                  f'{H.escape(m["title"])}</a></h3>'
                  f'<p>{H.escape(m.get("description", ""))}</p></div>')

    idx_meta = {
        "title": "Grow it, then eat it",
        "slug": "index",
        "kind": "page",
        "description": "Independent, tested guides to sprouting, microgreens, "
                       "and the equipment that makes whole food worth growing at home.",
        "updated": str(date.today()),
    }
    idx_body = (
        figure("img-six-hubs", illos)
        + "<p>Every guide here is written to be used in a kitchen rather than skimmed. "
        "Each one carries the numbers, the failure modes, and the honest downside, "
        "because the parts people leave out are the parts that decide whether it works.</p>"
        f'<div class="hublist">{cards}</div>'
        "<h2>Start here</h2>"
        "<p>If you have never sprouted anything, begin with "
        '<a href="guide-mung-beans.html">mung beans start to finish</a>. '
        "It is a four day cycle, it costs almost nothing, and it teaches you what a "
        "healthy jar smells like before you work with a seed that punishes mistakes.</p>"
    )
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(
        shell(idx_meta, idx_body, nav))
    print("  wrote index.html")

    # ---- sitemap
    urls = "".join(f"<url><loc>{SITE}/{m['slug']}.html</loc>"
                   f"<lastmod>{m.get('updated', date.today())}</lastmod></url>"
                   for m, _ in docs)
    urls = f"<url><loc>{SITE}/</loc></url>" + urls
    open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    print("  wrote sitemap.xml")

    open(os.path.join(HERE, "robots.txt"), "w", encoding="utf-8").write(
        f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print("  wrote robots.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
