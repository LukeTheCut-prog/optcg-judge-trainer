#!/usr/bin/env python3
"""
OPTCG Judge Trainer — Meta Deck Fetcher
========================================
Fetches meta deck data from onepiece.limitlesstcg.com and updates
public/data/decks.json with leader-grouped decks.

For each meta leader it collects:
  - The "core cards" (cards present in >=50% of tournament lists)
  - The leader card ID

Usage:
    python scripts/fetch_meta_decks.py --format OP15
    python scripts/fetch_meta_decks.py --format OP14
    python scripts/fetch_meta_decks.py --format OP15 --min-share 0.75
    python scripts/fetch_meta_decks.py --list-formats

Requirements:
    pip install requests beautifulsoup4
"""

import json
import re
import sys
import time
import argparse
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    print("Missing dependencies. Run:\n  pip install requests beautifulsoup4")
    sys.exit(1)

ROOT       = Path(__file__).parent.parent
DECKS_FILE = ROOT / "public" / "data" / "decks.json"

BASE    = "https://onepiece.limitlesstcg.com"
DELAY   = 1.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


# ── HTTP ──────────────────────────────────────────────────────────────────────
def _get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        print("    Network error: {}".format(e))
        return None


# ── Scrapers ──────────────────────────────────────────────────────────────────
def get_meta_leaders(fmt):
    """
    Returns list of dicts: {name, deck_id, leader_id, share}
    from /decks?format=OP15
    """
    url = "{}/decks?format={}".format(BASE, fmt.upper())
    print("Fetching meta leaders from {}".format(url))
    soup = _get(url)
    if not soup:
        return []

    leaders = []
    # Table rows: rank | img | name+link | points | share
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        link = row.find("a", href=re.compile(r"/decks/\d+$"))
        if not link:
            continue
        name    = link.get_text(strip=True)
        deck_id = re.search(r"/decks/(\d+)$", link["href"])
        if not deck_id:
            continue

        # Share % — last cell
        share_text = cells[-1].get_text(strip=True).replace("%", "").strip()
        try:
            share = float(share_text) / 100
        except ValueError:
            share = 0.0

        leaders.append({
            "name":    name,
            "deck_id": deck_id.group(1),
            "share":   share,
        })

    return leaders


def get_leader_data(deck_id):
    """
    Returns {leader_card_id, core_cards: [(card_id, pct), ...]}
    from /decks/{id}
    """
    url = "{}/decks/{}".format(BASE, deck_id)
    soup = _get(url)
    if not soup:
        return None

    # Leader card ID — shown as text like "OP15-058" near the top
    leader_id = None
    for tag in soup.find_all(string=re.compile(r"[A-Z]{2,5}\d{2}-\d{3}")):
        m = re.search(r"([A-Z]{2,5}\d{2}-\d{3})", str(tag))
        if m:
            leader_id = m.group(1)
            break

    # Core cards — img tags with alt=card_id and a "X in Y%" text nearby
    core_cards = []
    seen = set()
    for img in soup.select("img[alt]"):
        alt = img.get("alt", "")
        if not re.match(r"[A-Z]{2,5}\d{2}-\d{3}", alt):
            continue
        if alt == leader_id or alt in seen:
            continue

        # Find share % in surrounding text
        parent = img.parent
        text   = parent.get_text(" ", strip=True) if parent else ""
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        pct = float(m.group(1)) / 100 if m else 0.0

        seen.add(alt)
        core_cards.append((alt, pct))

    return {"leader_id": leader_id, "core_cards": core_cards}


# ── Database ──────────────────────────────────────────────────────────────────
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


# ── Commands ──────────────────────────────────────────────────────────────────
def cmd_fetch(fmt, min_share):
    leaders = get_meta_leaders(fmt)
    if not leaders:
        print("No leaders found for format {}. Check the format code.".format(fmt))
        return

    print("Found {} meta leaders for {}".format(len(leaders), fmt))

    decks = load_decks()
    # Remove old entries for this format so we don't accumulate stale data
    decks = [d for d in decks if d.get("format") != fmt.upper()]

    added = 0
    for leader in leaders:
        name    = leader["name"]
        deck_id = leader["deck_id"]
        share   = leader["share"]

        print("\n  {} ({:.0f}% meta share)...".format(name, share * 100))
        time.sleep(DELAY)

        data = get_leader_data(deck_id)
        if not data:
            print("    Could not fetch deck data, skipping.")
            continue

        leader_id = data["leader_id"]
        # Filter core cards by minimum share threshold
        card_ids = [
            cid for cid, pct in data["core_cards"]
            if pct >= min_share
        ]

        if not card_ids:
            print("    No core cards above {:.0f}% threshold, skipping.".format(min_share * 100))
            continue

        deck = {
            "id":          "{}-{}".format(slugify(name), fmt.lower()),
            "name":        name,
            "leader":      leader_id,
            "format":      fmt.upper(),
            "meta_share":  round(share * 100, 1),
            "cards":       ([leader_id] if leader_id else []) + card_ids,
            "description": "{:.0f}% meta share in {} · {} core cards (≥{:.0f}% of lists)".format(
                share * 100, fmt.upper(), len(card_ids), min_share * 100
            ),
        }

        decks.append(deck)
        added += 1
        print("    Leader: {} | {} core cards".format(leader_id or "?", len(card_ids)))

    save_decks(decks)
    print("\n-- Done: {} decks added for {} --".format(added, fmt.upper()))
    print("   {}".format(DECKS_FILE))


def cmd_list_formats():
    """Show available format codes by checking the decks page."""
    print("Common format codes (use with --format):")
    formats = [
        ("OP15", "Adventure on Kami's Island (current)"),
        ("OP14", "The Azure Sea's Seven"),
        ("OP13", "Carrying On His Will"),
        ("OP12", "Legacy of the Master"),
        ("OP11", "A Fist of Divine Speed"),
        ("OP10", "Royal Blood"),
    ]
    for code, name in formats:
        print("  {:<8} {}".format(code, name))
    print("\nTip: check https://onepiece.limitlesstcg.com/decks for the latest format.")


def cmd_show():
    decks = load_decks()
    if not decks:
        print("No decks in database.")
        return
    print("\n{:<40} {:<8} {:<8} {}".format("Name", "Format", "Share%", "Cards"))
    print("-" * 72)
    for d in sorted(decks, key=lambda x: (-x.get("meta_share", 0))):
        print("{:<40} {:<8} {:<8} {}".format(
            d["name"][:39],
            d.get("format", "?"),
            "{}%".format(d.get("meta_share", "?")),
            len(d.get("cards", []))
        ))
    print("\nTotal: {} decks".format(len(decks)))


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="OPTCG Judge Trainer -- Meta Deck Fetcher (Limitless TCG)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Fetch current meta (OP15):
    python scripts/fetch_meta_decks.py --format OP15

  Only include cards present in 75%+ of lists:
    python scripts/fetch_meta_decks.py --format OP15 --min-share 0.75

  Show all decks currently in the database:
    python scripts/fetch_meta_decks.py --show

  Show available format codes:
    python scripts/fetch_meta_decks.py --list-formats
        """
    )
    parser.add_argument("--format",       "-f", metavar="FMT",  help="Format code, e.g. OP15")
    parser.add_argument("--min-share",          metavar="N",    type=float, default=0.5,
                        help="Min fraction of lists a card must appear in (default: 0.5 = 50%%)")
    parser.add_argument("--list-formats",        action="store_true", help="Show available format codes")
    parser.add_argument("--show",          "-s", action="store_true", help="List all decks in database")
    args = parser.parse_args()

    if args.list_formats:
        cmd_list_formats()
    elif args.show:
        cmd_show()
    elif args.format:
        cmd_fetch(args.format, args.min_share)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
