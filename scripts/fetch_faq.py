#!/usr/bin/env python3
"""
OPTCG Judge Trainer -- Official Card Q&A (FAQ) Fetcher
======================================================
Downloads the official per-set Q&A PDFs from en.onepiece-cardgame.com and
builds public/data/faq.json mapping each card id to its list of Q&A entries:

    { "P-001": [ { "q": "...", "a": "..." }, ... ], "OP16-080": [ ... ] }

The PDFs are laid out as a table (Card No. | Card Name | Question | Answer).
Text is extracted by coordinates (not reading order, which is ambiguous):
columns are split by X position, rows by Y position. This handles cells that
wrap over several lines and cards that have multiple Q&A entries.

Usage:
    python scripts/fetch_faq.py

Requirements:
    pip install requests beautifulsoup4 pymupdf
"""

import json
import re
import sys
import time
from pathlib import Path

try:
    import requests
    import urllib3
    from bs4 import BeautifulSoup
    import fitz  # PyMuPDF
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("Missing dependencies. Run:\n  pip install requests beautifulsoup4 pymupdf")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
FAQ_FILE   = ROOT / "public" / "data" / "faq.json"
CARDS_FILE = ROOT / "public" / "data" / "cards.json"

# ── Config ────────────────────────────────────────────────────────────────────
BASE     = "https://en.onepiece-cardgame.com"
FAQ_PAGE = BASE + "/rules/faq/"
HEADERS  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

# Card id in the "Card No." column, e.g. P-001 / OP16-080 / ST30-001 / EB02-010.
NO_RE = re.compile(r'^(P|OP\d{2}|ST\d{2}|EB\d{2}|PRB\d{2}|EX\d{2})-\d{3}$')

# Column geometry (constant across every official PDF, verified empirically):
#   card no.  : x < 70
#   name      : 70 .. 168   (ignored — we have names in cards.json)
#   question  : 168 .. 368
#   answer    : x >= 368
NO_LEFT      = 70.0
CONTENT_LEFT = 168.0
QA_SPLIT     = 368.0


def get_pdf_links():
    """Scrape the FAQ page for every per-set Q&A PDF (skips the general rules)."""
    r = requests.get(FAQ_PAGE, headers=HEADERS, timeout=20, verify=False)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=re.compile(r"/pdf/(qa|faq)_.*\.pdf")):
        href = a["href"].split("?")[0]
        if "qa_rules" in href:          # general rules: no card numbers
            continue
        links.append(href if href.startswith("http") else BASE + href)
    return list(dict.fromkeys(links))


def parse_pdf(data):
    """Parse one Q&A PDF (bytes) into {card_id: [{q, a}, ...]}."""
    doc = fitz.open(stream=data, filetype="pdf")
    out = {}
    for page in doc:
        words = page.get_text("words")  # (x0, y0, x1, y1, text, block, line, word)
        # Header row ("Card No. / Card Name / Question / Answer") — skip above it.
        # The words "No."/"Answer" also occur in the body (answers start with
        # "No."), so the header is identified as the only row where the column
        # labels "Question" and "Answer" sit on the same line.
        ans_ys = [w[1] for w in words if w[4] == "Answer"]
        hdr_y = 0.0
        for w in words:
            if w[4] == "Question" and any(abs(w[1] - ay) < 3 for ay in ans_ys):
                hdr_y = max(hdr_y, w[1])
        top = hdr_y + 8 if hdr_y else 95.0

        # Each card-number occurrence anchors one table row (centered vertically).
        anchors = sorted((w[1], w[4]) for w in words if w[0] < NO_LEFT and NO_RE.match(w[4]))
        if not anchors:
            continue
        ays = [a[0] for a in anchors]
        # Row bands: split at the midpoints between consecutive anchors.
        bounds = [top] + [(ays[i] + ays[i + 1]) / 2 for i in range(len(ays) - 1)] + [1e9]
        rows = [{"no": a[1], "q": [], "a": []} for a in anchors]

        for w in words:
            x, y, t = w[0], w[1], w[4]
            if y < top or x < CONTENT_LEFT:
                continue
            i = 0
            while i < len(rows) and not (bounds[i] <= y < bounds[i + 1]):
                i += 1
            if i >= len(rows):
                continue
            (rows[i]["a"] if x >= QA_SPLIT else rows[i]["q"]).append((y, x, t))

        for r in rows:
            q = " ".join(t for _, _, t in sorted(r["q"])).replace("<br>", " ")
            a = " ".join(t for _, _, t in sorted(r["a"])).replace("<br>", " ")
            q = re.sub(r"\s+", " ", q).strip()
            a = re.sub(r"\s+", " ", a).strip()
            if q and a:
                out.setdefault(r["no"], []).append({"q": q, "a": a})
    return out


def main():
    print("Fetching FAQ PDF list from {}...".format(FAQ_PAGE))
    links = get_pdf_links()
    print("Found {} Q&A PDFs".format(len(links)))

    faq = {}
    for url in links:
        name = url.rsplit("/", 1)[-1]
        try:
            data = requests.get(url, headers=HEADERS, timeout=30, verify=False).content
            part = parse_pdf(data)
        except Exception as e:
            print("  {:32} FAILED: {}".format(name, e))
            continue
        n = sum(len(v) for v in part.values())
        for cid, items in part.items():
            faq.setdefault(cid, []).extend(items)
        print("  {:32} {:3} cards, {:3} Q&A".format(name, len(part), n))
        time.sleep(0.3)

    # Drop duplicate Q&A within a card (a card can appear in more than one PDF).
    for cid in faq:
        seen, uniq = set(), []
        for e in faq[cid]:
            k = (e["q"], e["a"])
            if k not in seen:
                seen.add(k)
                uniq.append(e)
        faq[cid] = uniq

    # Coverage sanity check against the card database.
    try:
        ids = {c["id"] for c in json.loads(CARDS_FILE.read_text(encoding="utf-8"))}
        unmatched = sorted(c for c in faq if c not in ids)
        matched = len([c for c in faq if c in ids])
        print("\nCoverage: {} FAQ card-ids match the database.".format(matched))
        if unmatched:
            print("WARNING: {} FAQ ids NOT in DB (first 15): {}".format(
                len(unmatched), unmatched[:15]))
    except (OSError, ValueError):
        pass

    FAQ_FILE.write_text(json.dumps(faq, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved {} cards / {} Q&A -> {}".format(
        len(faq), sum(len(v) for v in faq.values()), FAQ_FILE))


if __name__ == "__main__":
    main()
