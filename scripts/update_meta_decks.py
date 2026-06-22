#!/usr/bin/env python3
"""
OPTCG Judge Trainer — Meta Deck Updater
========================================
Scrapes meta deck data from onepiece.limitlesstcg.com and updates
public/data/decks.json with card lists grouped by leader.

Usage:
    python scripts/update_meta_decks.py
    python scripts/update_meta_decks.py --format OP15
    python scripts/update_meta_decks.py --format OP15 --min-share 3.0
    python scripts/update_meta_decks.py --list-formats

Requirements:
    pip install requests beautifulsoup4
"""

import json
import sys
import time
import argparse
import re
from pathlib import Path

try:
    import requests
    import urllib3
    from bs4 import BeautifulSoup
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("Missing dependencies. Run:\n  pip install requests beautifulsoup4")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
DECKS_FILE = ROOT / "public" / "data" / "decks.json"
CARDS_FILE = ROOT / "public" / "data" / "cards.json"

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL = "https://onepiece.limitlesstcg.com"
DELAY    = 1.0  # seconds between requests — be polite

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── egman events (deckbuilder.egmanevents.com) — real tournament data ────────────
# Backed by a public Supabase project; the publishable key is embedded in the
# site's JS bundle. Unlike Limitless, egman filters tournaments by exact format,
# so it can serve genuine OP16 data (and returns nothing for a format that isn't
# out yet — which is exactly what we want for the "don't touch it" guard).
EGMAN_API = "https://resgvirjzcpamfumrygh.supabase.co/rest/v1"
EGMAN_KEY = "sb_publishable_bdDgor6ifmOvryEuZKWniw_RBzb3vuh"
EGMAN_HEADERS = {"apikey": EGMAN_KEY, "Accept": "application/json"}
EGMAN_SITE = "https://deckbuilder.egmanevents.com/optcg/tournaments"


def _card_names():
    """Map card id -> (name, color) from cards.json, for nice deck labels."""
    try:
        db = json.loads(CARDS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {c["id"].upper(): (c.get("name") or c["id"], c.get("color") or "") for c in db}


# ── HTTP helper ───────────────────────────────────────────────────────────────
def _get(path):
    url = BASE_URL + path if path.startswith("/") else path
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        print("  Network error fetching {}: {}".format(path, e))
        return None


# ── Scraping functions ────────────────────────────────────────────────────────
def get_available_formats():
    """Scrape the list of available formats from the decks page."""
    soup = _get("/decks")
    if not soup:
        return []
    formats = []
    # Format links look like /decks?format=OP15
    for a in soup.find_all("a", href=re.compile(r"/decks\?format=")):
        fmt = re.search(r"format=([^&]+)", a["href"])
        if fmt:
            formats.append(fmt.group(1))
    # Also check for format options in select elements or text
    for opt in soup.find_all(string=re.compile(r"^OP\d+")):
        txt = opt.strip()
        if txt and txt not in formats:
            formats.append(txt)
    return list(dict.fromkeys(formats))  # deduplicate preserving order


def _api_format(fmt):
    """Limitless deck filter expects the hyphenated set id: OP16 -> OP-16."""
    f = fmt.strip().upper()
    if "-" in f:
        return f
    m = re.match(r"^([A-Z]+)(\d+)$", f)
    return "{}-{}".format(m.group(1), m.group(2)) if m else f


def get_meta_decks(format_id, min_share=0.0):
    """
    Scrape the deck list for a given format.
    Returns list of dicts: {id, name, share, leader_card_id}
    """
    soup = _get("/decks?format={}".format(_api_format(format_id)))
    if not soup:
        return []

    decks = []
    # Each row in the ranking table: deck name links to /decks/{id}
    for a in soup.find_all("a", href=re.compile(r"^/decks/\d+$")):
        deck_id = re.search(r"/decks/(\d+)$", a["href"])
        if not deck_id:
            continue
        name = a.get_text(strip=True)
        if not name:
            continue

        # Share % lives in its own <td> in the same row (the name and the
        # share are separate cells), so scan the row's cells for the one that
        # actually contains a percentage rather than the cell wrapping the link.
        share = 0.0
        row = a.find_parent("tr")
        if row:
            for td in row.find_all("td"):
                pct = re.search(r"([\d.]+)\s*%", td.get_text(strip=True))
                if pct:
                    share = float(pct.group(1))
                    break

        if share >= min_share:
            decks.append({
                "limitless_id": int(deck_id.group(1)),
                "name":         name,
                "share":        share,
            })

    return decks


def get_deck_cards(limitless_id):
    """
    Scrape the card breakdown page for a deck.
    Returns (leader_card_id, [card_id, ...])
    """
    soup = _get("/decks/{}/cards".format(limitless_id))
    if not soup:
        return None, []

    # Card IDs come in two shapes: regular sets "OP15-061" / "ST10-010" and
    # promos "P-045". The old pattern only matched the regular shape, silently
    # dropping every promo card from the deck list.
    card_id_pattern = re.compile(r'\b((?:OP|ST|EB|PRB)\d{2}-\d{3}|P-\d{3})\b')

    leader_id = None
    card_ids  = []

    # Leader section — look for "Leader" heading or leader card link
    full_text = soup.get_text()
    # Find leader: it's listed before "Character" section
    leader_match = re.search(
        r'Leader\s*[\n\r]+.*?((?:OP|ST|EB|PRB)\d{2}-\d{3}|P-\d{3})',
        full_text, re.DOTALL)
    if leader_match:
        leader_id = leader_match.group(1)

    # All card IDs from image URLs (most reliable). Folder + filename, e.g.
    # /OP15/OP15-061_EN.webp, /ST10/ST10-010_EN.webp, /P/P-045_EN.webp
    img_pattern = re.compile(r'/[A-Za-z0-9]+/((?:OP|ST|EB|PRB)\d{2}-\d{3}|P-\d{3})_')
    seen = set()
    for img in soup.find_all("img"):
        src = img.get("src", "")
        m = img_pattern.search(src)
        if m:
            cid = m.group(1)
            if cid not in seen:
                seen.add(cid)
                card_ids.append(cid)

    # Also extract from anchor hrefs: /cards/OP15-061, /cards/P-045
    for a in soup.find_all("a", href=re.compile(r"/cards/((?:OP|ST|EB|PRB)\d{2}-\d{3}|P-\d{3})")):
        m = re.search(r"/cards/((?:OP|ST|EB|PRB)\d{2}-\d{3}|P-\d{3})", a["href"])
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            card_ids.append(m.group(1))

    # Identify leader from card list (usually labeled separately on page)
    # Check page title area for leader card ID
    title_area = soup.find("h1") or soup.find("h2")
    if title_area:
        nearby = title_area.find_next(string=re.compile(r'[A-Z]{2,5}\d{2}-\d{3}'))
        if nearby:
            leader_id = card_id_pattern.search(nearby.strip()).group(1) if card_id_pattern.search(nearby.strip()) else leader_id

    # Remove leader from card_ids list (it's stored separately)
    if leader_id and leader_id in card_ids:
        card_ids.remove(leader_id)

    return leader_id, card_ids


# ── Database helpers ──────────────────────────────────────────────────────────
def load_decks():
    if not DECKS_FILE.exists():
        DECKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        return []
    return json.loads(DECKS_FILE.read_text(encoding="utf-8"))


def save_decks(decks):
    DECKS_FILE.write_text(
        json.dumps(decks, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ── Deck builders (return full deck records, source-agnostic) ────────────────────
def build_limitless_decks(format_id, min_share):
    """Build deck records from Limitless. NOTE: Limitless ignores the format
    parameter and always returns the *current* meta, so this cannot give
    historical/specific formats — use the egman source for that."""
    meta = get_meta_decks(format_id, min_share)
    if not meta:
        return []
    decks = []
    for m in meta:
        lid, name = m["limitless_id"], m["name"]
        print("  [{}] {}...".format(lid, name), flush=True)
        leader_id, card_ids = get_deck_cards(lid)
        if not card_ids:
            print("    No cards found, skipping.")
            time.sleep(DELAY)
            continue
        decks.append({
            "id":          slugify("{}-{}".format(name, format_id)),
            "name":        name,
            "leader":      leader_id,
            "set":         format_id,
            "format":      format_id,
            "share":       m["share"],
            "cards":       card_ids,
            "description": "Meta deck from Limitless TCG ({}) - {:.1f}% share".format(
                format_id, m["share"]),
            "source":      "https://onepiece.limitlesstcg.com/decks/{}".format(lid),
        })
        time.sleep(DELAY)
    return decks


def _egman_get(path):
    try:
        r = requests.get(EGMAN_API + path, headers=EGMAN_HEADERS, timeout=20, verify=False)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print("  Network error (egman): {}".format(e))
        return None


def _parse_egman_deck(url):
    """'.../?deck=OP15-061:4,OP16-080:1,...&type=optcg' -> ['OP15-061', ...]."""
    m = re.search(r'[?&]deck=([^&]+)', url)
    if not m:
        return []
    ids = []
    for part in m.group(1).split(","):
        cid = part.split(":")[0].strip().upper()
        if cid:
            ids.append(cid)
    return ids


def build_egman_decks(format_id, min_share):
    """Build deck records from real egman tournament data for an exact format.

    Returns [] if the format has no tournaments (e.g. not released yet), so the
    caller leaves decks.json untouched.
    """
    from collections import defaultdict

    tours = _egman_get(
        "/tournaments?game_id=eq.optcg&format=eq.{}"
        "&select=id,tournament_name,leader_breakdown".format(format_id))
    if not tours:
        return []
    print("Found {} {} tournament(s) on egman.".format(len(tours), format_id))

    # Aggregate true meta share from the per-tournament leader breakdowns.
    leader_count = defaultdict(int)
    total = 0
    for t in tours:
        for lb in (t.get("leader_breakdown") or []):
            leader_count[(lb.get("deck_type") or "").upper()] += lb.get("count", 0)
            total += lb.get("count", 0)

    # Pull the actual decklists (top-cut) to get each archetype's card pool.
    tids = [t["id"] for t in tours]
    results = _egman_get(
        "/tournament_results?tournament_id=in.({})"
        "&select=deck_type,deck_list_url".format(",".join(tids))) or []

    pool = defaultdict(list)
    seen = defaultdict(set)
    freq = defaultdict(int)
    for r in results:
        leader = (r.get("deck_type") or "").upper()
        urls = r.get("deck_list_url") or []
        if not leader or not urls:
            continue
        ids = _parse_egman_deck(urls[0])
        if not ids:
            continue
        freq[leader] += 1
        for cid in ids:
            if cid not in seen[leader]:
                seen[leader].add(cid)
                pool[leader].append(cid)

    names = _card_names()
    decks = []
    for leader, card_ids in pool.items():
        # Share: prefer the full-field leader breakdown, else top-cut frequency.
        if total:
            share = 100.0 * leader_count.get(leader, 0) / total
        else:
            share = 100.0 * freq[leader] / max(1, sum(freq.values()))
        if share < min_share:
            continue
        lname, lcolor = names.get(leader, (leader, ""))
        # Clean up disambiguation noise in card names: "Nami (041)",
        # "Rosinante (061) (Alternate Art)", "Mihawk - OP14-020", "Enel (OP15-058)".
        lname = re.sub(r"\s*\([^)]*\)", "", lname)
        lname = re.sub(r"\s*-\s*[A-Z0-9-]+$", "", lname).strip() or leader
        name = "{} {}".format(lcolor, lname).strip() if lcolor else lname
        body = [c for c in card_ids if c != leader]  # leader stored separately
        decks.append({
            "id":          slugify("{}-{}-{}".format(name, leader, format_id)),
            "name":        name,
            "leader":      leader,
            "set":         format_id,
            "format":      format_id,
            "share":       round(share, 2),
            "cards":       body,
            "description": "Meta deck from egman events ({}) - {:.1f}% share".format(
                format_id, share),
            "source":      "{}?format={}".format(EGMAN_SITE, format_id),
        })
    decks.sort(key=lambda d: -d["share"])
    return decks


# ── Main command ──────────────────────────────────────────────────────────────
def cmd_update(format_id, min_share, replace_format, source="egman"):
    # Store the canonical short form (OP16) for the stored deck records.
    format_id = format_id.strip().upper().replace("-", "")
    print("Fetching meta decks for format {} from {}...".format(format_id, source))

    if source == "limitless":
        decks = build_limitless_decks(format_id, min_share)
    else:
        decks = build_egman_decks(format_id, min_share)

    # SAFETY: if the requested format yielded nothing, leave decks.json alone.
    # (Prevents Limitless' "current meta" fallback or a not-yet-released format
    # from overwriting good data with unrelated decks.)
    if not decks:
        print("No decks found for format '{}' on {}. Nothing changed.".format(
            format_id, source))
        return

    print("Built {} decks (share >= {}%).".format(len(decks), min_share))

    all_decks = load_decks()
    if replace_format:
        before = len(all_decks)
        all_decks = [d for d in all_decks if d.get("format") != format_id]
        print("Removed {} existing {} decks".format(before - len(all_decks), format_id))

    added = updated = 0
    existing_ids = {d["id"]: i for i, d in enumerate(all_decks)}
    for deck in decks:
        if deck["id"] in existing_ids:
            all_decks[existing_ids[deck["id"]]] = deck
            updated += 1
        else:
            all_decks.append(deck)
            existing_ids[deck["id"]] = len(all_decks) - 1
            added += 1

    save_decks(all_decks)
    print("\n-- Done: {} added, {} updated --".format(added, updated))
    print("   decks.json now has {} decks".format(len(all_decks)))


def cmd_list_formats():
    print("Fetching available formats from Limitless...")
    fmts = get_available_formats()
    if fmts:
        print("Available formats:")
        for f in fmts:
            print("  {}".format(f))
    else:
        print("Could not fetch formats. Try manually: OP15, OP14, OP13, OP12...")


def cmd_update_all(min_share, source="egman"):
    """Re-fetch and replace all formats currently present in decks.json."""
    all_decks = load_decks()
    formats = list(dict.fromkeys(
        d.get("format") for d in all_decks if d.get("format")
    ))

    if not formats:
        print("No formats found in decks.json. Run --format OP16 first.")
        return

    print("Formats to update: {}".format(", ".join(formats)))
    for fmt in formats:
        print("\n" + "="*50)
        cmd_update(fmt, min_share, replace_format=True, source=source)

    print("\n" + "="*50)
    print("All formats updated.")


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="OPTCG Judge Trainer -- Meta Deck Updater (sources: egman events / Limitless TCG)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Update meta decks for current format:
    python scripts/update_meta_decks.py --format OP15

  Replace (full refresh, removes dropped cards):
    python scripts/update_meta_decks.py --format OP15 --replace

  Update ALL formats already in decks.json (full refresh):
    python scripts/update_meta_decks.py --update-all

  Only include decks with at least 5%% meta share:
    python scripts/update_meta_decks.py --format OP15 --min-share 5.0

  Use the Limitless source instead (current meta only, ignores format):
    python scripts/update_meta_decks.py --format OP16 --source limitless

  List available formats:
    python scripts/update_meta_decks.py --list-formats
        """
    )
    parser.add_argument("--format",       default="OP16",  help="Format to import (default: OP16)")
    parser.add_argument("--source",       default="egman", choices=["egman", "limitless"],
                        help="Data source: egman (real tournament data, exact format) or limitless (current meta only)")
    parser.add_argument("--min-share",    type=float, default=0.0, help="Minimum meta share %% to include (default: 0)")
    parser.add_argument("--replace",      action="store_true", help="Replace existing decks for this format")
    parser.add_argument("--update-all",   action="store_true", help="Re-fetch and replace ALL formats in decks.json")
    parser.add_argument("--list-formats", action="store_true", help="List available formats")
    args = parser.parse_args()

    if args.list_formats:
        cmd_list_formats()
    elif args.update_all:
        cmd_update_all(args.min_share, args.source)
    else:
        cmd_update(args.format, args.min_share, args.replace, args.source)


if __name__ == "__main__":
    main()
