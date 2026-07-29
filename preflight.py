#!/usr/bin/env python3
"""
agrosuperfood.com PRE-FLIGHT GATE
Run before every push. Deterministic; no judgement calls.

    python3 preflight.py            # wave mode
    python3 preflight.py --final    # enforce the complete 6 hub / 60 spoke build

Exit 0 = green. Non-zero = do not push.
"""
import argparse, json, os, re, sys
from xml.dom import minidom

HERE = os.path.dirname(os.path.abspath(__file__))
FAILS, WARNS = [], []
def fail(m): FAILS.append(m); print(f"  x FAIL  {m}")
def ok(m):   print(f"  .       {m}")
def warn(m): WARNS.append(m); print(f"  ! WARN  {m}")

HUB_FLOOR, SPOKE_FLOOR = 3300, 1700
SVG_MAX = 15 * 1024
FINAL_HUBS, FINAL_SPOKES = 6, 60

# Zero em dashes is a standing instruction, not a budget. The Prose skill warns
# the tic reasserts itself inside its own fix, so en dashes used as dashes fail too.
HARD_PHRASES = [
    "delve", "tapestry", "testament to", "in today's world", "look no further",
    "let's dive", "game-changer", "game changer", "unlock the", "elevate your",
    "seamless", "plethora", "when it comes to", "at the end of the day",
    "it's worth noting", "worth noting that", "navigating the landscape",
    "in the realm of", "a myriad of", "harness the",
]
SOFT_BUDGET = {"bare emphasis italics": 40, "not X, but Y": 5,
               "the way X did": 15, "hedged descriptor": 12}


def read(p): return open(p, encoding="utf-8").read()


def front(t):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, re.S)
    if not m: return {}, t
    meta = {}
    for line in m.group(1).split("\n"):
        if ":" in line and not line.startswith((" ", "-")):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, m.group(2)


def words(body):
    t = re.sub(r"```.*?```", "", body, flags=re.S)
    t = re.sub(r"!!fig \S+", "", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return len(t.split())


def sources():
    out = []
    for f in sorted(os.listdir(HERE)):
        if f.startswith("src-") and f.endswith(".md"):
            meta, body = front(read(os.path.join(HERE, f)))
            out.append((f, meta, body))
    return out


# ------------------------------------------------------------------ CONTENT
def check_content(docs, final):
    print("\n=== CONTENT ===")
    hubs = [d for d in docs if d[1].get("kind") == "hub"]
    spokes = [d for d in docs if d[1].get("kind") == "spoke"]
    print(f"  {len(hubs)} hub(s), {len(spokes)} spoke(s)")

    if final:
        if len(hubs) != FINAL_HUBS: fail(f"hub count {len(hubs)} != {FINAL_HUBS}")
        if len(spokes) != FINAL_SPOKES: fail(f"spoke count {len(spokes)} != {FINAL_SPOKES}")
    else:
        done = len(hubs) + len(spokes)
        warn(f"wave mode: {done} of 66 planned pages complete")

    for label, group, floor in (("hub", hubs, HUB_FLOOR), ("spoke", spokes, SPOKE_FLOOR)):
        for f, m, b in group:
            w = words(b)
            if w >= floor: ok(f"{f}: {w} words (floor {floor})")
            else: fail(f"{f}: {w} words - UNDER {label} floor {floor}; expand, never pad")

    hub_slugs = {m["slug"] for _, m, _ in hubs}
    spoke_slugs = {m["slug"] for _, m, _ in spokes}
    for f, m, b in spokes:
        links = re.findall(r"\]\(([a-z0-9-]+)\.html\)", b)
        up = [l for l in links if l in hub_slugs]
        sib = {l for l in links if l in spoke_slugs and l != m["slug"]}
        dead = [l for l in links if l not in hub_slugs | spoke_slugs and l != "index"]
        if len(up) < 1: fail(f"{f}: no up-link to a hub")
        elif len(set(up)) > 1: fail(f"{f}: links to {len(set(up))} hubs; expected 1")
        if len(sib) != 2: fail(f"{f}: {len(sib)} sibling link(s); need exactly 2")
        if dead: fail(f"{f}: links to non-existent pages {dead}")
    if spokes and not FAILS: ok("link geometry: 1 up-link + 2 siblings on every spoke")


# ------------------------------------------------------------------ PROSE
def check_prose(docs):
    print("\n=== PROSE ===")
    totals = {k: 0 for k in SOFT_BUDGET}
    corpus = 0
    for f, m, b in docs:
        w = words(b); corpus += w
        em = b.count("\u2014") + len(re.findall(r"(?<!-)--(?!-)", b)) + b.count("&mdash;")
        if em: fail(f"{f}: {em} em dash(es) - standing instruction is zero")
        en = len(re.findall(r"\s\u2013\s", b)) + b.count("&ndash;")
        if en: fail(f"{f}: {en} spaced en dash(es) - the tic wearing a disguise")
        hits = [h for h in HARD_PHRASES if h in b.lower()]
        if hits: fail(f"{f}: banned filler {hits}")
        c = {
            "bare emphasis italics": len(re.findall(r"(?<![*\w])\*(?!\*)([^*\n]{1,22})\*(?!\*)", b)),
            "not X, but Y": len(re.findall(r"\bnot\b[^.\n]{1,60}?,\s*but\b", b, re.I)),
            "the way X did": len(re.findall(r"\bthe way (a|an|the|he|she|they|it|you)\b", b, re.I)),
            "hedged descriptor": len(re.findall(
                r"\b(something adjacent to|a kind of|a sort of|as if it were|almost like)\b", b, re.I)),
        }
        for k, v in c.items(): totals[k] += v
        ok(f"{f}: {w}w | 0 em dash | " + ", ".join(f"{k} {v}" for k, v in c.items()))
    print(f"  corpus: {corpus} words")
    for k, ceil in SOFT_BUDGET.items():
        rate = totals[k] * 10000 / max(corpus, 1)
        if rate <= ceil: ok(f"{k}: {totals[k]} = {rate:.1f}/10k (ceiling {ceil})")
        else: fail(f"{k}: {rate:.1f}/10k over ceiling {ceil} - rewrite, do not script")


# ------------------------------------------------------------------ BUILD
def check_build(docs):
    print("\n=== BUILT HTML ===")
    expected = [m["slug"] + ".html" for _, m, _ in docs] + ["index.html"]
    built = [f for f in expected if os.path.exists(os.path.join(HERE, f))]
    missing = [f for f in expected if f not in built]
    if missing: fail(f"not built: {missing} - run build.py")
    else: ok(f"all {len(expected)} page(s) built")

    on_disk = set(os.listdir(HERE))
    for f in built:
        t = read(os.path.join(HERE, f))
        # marker must survive the word "Amazon" being wrapped in an anchor
        if "Associate this site earns from qualifying purchases" not in t:
            fail(f"{f}: affiliate disclosure missing")
        broken = [h for h in re.findall(r'(?:href|src)="([^":]+)"', t)
                  if not h.startswith(("#", "//")) and h not in on_disk]
        if broken: fail(f"{f}: broken local reference(s) {sorted(set(broken))}")
        if 'lang="en"' not in t: fail(f"{f}: no lang attribute")
        if "application/ld+json" not in t: fail(f"{f}: no structured data")
    if not FAILS: ok("disclosure, structured data and local links verified on every page")


# ------------------------------------------------------------------ AFFILIATE
def check_affiliate(docs):
    print("\n=== AFFILIATE RAILS ===")
    d = json.load(open(os.path.join(HERE, "products.json"), encoding="utf-8"))
    pmap = {p["id"]: p for p in d["products"]}
    ok(f"manifest parses, {len(d['products'])} product(s)")

    # a token inside markdown link brackets would nest one anchor in another
    for f, m, b in docs:
        if "]({{product:" in b:
            fail(f"{f}: product token wrapped in markdown link syntax; use the bare token")

    # every {{product:id}} token must resolve to a LIVE asin
    used = set()
    for f, m, b in docs:
        for pid in re.findall(r"\{\{product:([a-z0-9-]+)\}\}", b):
            used.add(pid)
            if pid not in pmap:
                fail(f"{f}: product token '{pid}' is not in products.json")
            elif pmap[pid]["asin"] == "PENDING":
                fail(f"{f}: product token '{pid}' has no live ASIN - link would break")
    if used: ok(f"{len(used)} product token(s) resolve to live ASINs")
    unused = [p["id"] for p in d["products"] if p["id"] not in used]
    if unused: warn(f"products in manifest with no link on any page: {unused}")

    # every rendered Amazon link must carry the tag and rel=sponsored
    for f in os.listdir(HERE):
        if not f.endswith(".html"): continue
        t = read(os.path.join(HERE, f))
        for a in re.findall(r'<a href="(https://www\.amazon\.com[^"]*)"([^>]*)>', t):
            if f"tag={d['tag']}" not in a[0]:
                fail(f"{f}: Amazon link missing associates tag: {a[0][:60]}")
            if "sponsored" not in a[1]:
                fail(f"{f}: Amazon link missing rel=sponsored: {a[0][:60]}")
    if d["tag"].startswith("REPLACE_"):
        warn("associates tag is still a placeholder - set it before launch")
    asin = re.compile(r"\bB0[A-Z0-9]{8}\b")
    tag = re.compile(r"tag=[A-Za-z0-9-]+")
    strays = []
    for f in os.listdir(HERE):
        # .html is generated output and MUST contain ASINs; it is verified
        # separately below for tag and rel. Only hand-edited sources are scanned.
        if f == "products.json" or not f.endswith((".md", ".json", ".css")):
            continue
        t = read(os.path.join(HERE, f))
        if asin.search(t) or tag.search(t): strays.append(f)
    if strays: fail(f"hardcoded ASIN or tag outside products.json: {strays}")
    else: ok("no ASINs or tags outside products.json")
    amz = [f for f in os.listdir(HERE) if f.endswith((".md", ".html"))
           and re.search(r"media-amazon\.com|ssl-images-amazon\.com", read(os.path.join(HERE, f)))]
    if amz: fail(f"Amazon-hosted images referenced directly (policy violation): {amz}")
    else: ok("no directly-referenced Amazon imagery")


# ------------------------------------------------------------------ SVG
def check_svgs():
    print("\n=== ILLUSTRATIONS ===")
    files = sorted(f for f in os.listdir(HERE) if f.endswith(".svg"))
    man = json.load(open(os.path.join(HERE, "illustrations.json"), encoding="utf-8"))
    print(f"  {len(files)} SVG file(s), {len(man)} manifest entr(ies)")
    seen = {}
    for f in files:
        p = os.path.join(HERE, f); raw = read(p); size = os.path.getsize(p)
        key = f[:-4]; probs = []
        try: minidom.parseString(raw.encode("utf-8"))
        except Exception as e: fail(f"{f}: malformed XML - {e}"); continue
        if "viewBox" not in raw: probs.append("no viewBox")
        if "<title" not in raw: probs.append("no <title>")
        if "<desc" not in raw: probs.append("no <desc>")
        if re.search(r"(<image\b|data:image/(png|jpe?g))", raw): probs.append("embedded raster")
        if size > SVG_MAX: probs.append(f"{size}B over {SVG_MAX}B")
        if key not in man: probs.append("absent from illustrations.json")
        else:
            alt = man[key].get("alt", "").strip()
            if len(alt) < 30: probs.append("alt missing or too short")
            elif alt in seen: probs.append(f"alt duplicates {seen[alt]}")
            else: seen[alt] = f
        if probs: fail(f"{f}: " + "; ".join(probs))
        else: ok(f"{f}: {size}B, viewBox + title + desc + unique alt")
    orphans = [k for k in man if k + ".svg" not in files]
    if orphans: fail(f"manifest entries with no file: {orphans}")
    heaviest = sorted((os.path.getsize(os.path.join(HERE, f)) for f in files), reverse=True)[:3]
    if sum(heaviest) <= 60 * 1024: ok(f"worst-case page payload {sum(heaviest)}B (ceiling 61440B)")
    else: fail(f"three heaviest SVGs total {sum(heaviest)}B, over the 60KB ceiling")


PLACEHOLDERS = [
    "PENDING", "REPLACE_", "In production", "Coming soon", "TBD", "TODO",
    "Lorem ipsum", "placeholder", "XXXX", "FIXME", "your-tag-here",
]


def check_dates(docs):
    """A typo in a frontmatter year ships a page dated in the future."""
    print("\n=== DATES ===")
    from datetime import date
    today = date.today().isoformat()
    bad = []
    for f, m, b in docs:
        d = m.get("updated", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            bad.append(f"{f}: malformed updated date {d!r}")
        elif d > today:
            bad.append(f"{f}: updated date {d} is in the future")
    if bad:
        for x in bad: fail(x)
    else:
        ok(f"all {len(docs)} dates well formed and not in the future")


def check_placeholders():
    """Nothing shipped may advertise itself as unfinished."""
    print("\n=== PLACEHOLDERS ===")
    hits = []
    for f in sorted(os.listdir(HERE)):
        if not f.endswith((".md", ".html", ".json", ".css", ".txt", ".xml")):
            continue
        body = read(os.path.join(HERE, f))
        # frontmatter verify: notes are editorial provenance, never rendered
        scan = re.sub(r"^---\n.*?\n---\n", "", body, flags=re.S) if f.endswith(".md") else body
        for p in PLACEHOLDERS:
            # word boundaries, or 'PENDING' matches inside 'spending'
            pat = rf"\b{re.escape(p)}" + (r"\b" if p[-1].isalnum() else "")
            if re.search(pat, scan, re.I):
                hits.append(f"{f}: '{p}'")
    if hits:
        for h in hits: fail(f"placeholder text shipped {h}")
    else:
        ok(f"no placeholder text in any shipped file")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    docs = sources()
    check_content(docs, a.final)
    check_prose(docs)
    check_build(docs)
    check_affiliate(docs)
    check_svgs()
    check_dates(docs)
    check_placeholders()
    print("\n" + "=" * 62)
    if FAILS:
        print(f"RESULT: {len(FAILS)} FAILURE(S) - DO NOT PUSH")
        for f in FAILS: print(f"  x {f}")
    else:
        print("RESULT: ALL CHECKS PASSED - cleared to push")
    if WARNS:
        print(f"\n{len(WARNS)} warning(s):")
        for w in WARNS: print(f"  ! {w}")
    print("=" * 62)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
