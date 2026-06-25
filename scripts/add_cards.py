#!/usr/bin/env python3
"""
OPTCG Judge Trainer — Card Database Manager
============================================
Adds/updates cards in public/data/cards.json using optcgapi.com.
Images are downloaded locally to public/images/cards/.

Data coverage: OP01-OP13, EB01-EB03, PRB01-PRB02, ST01-ST28

Usage:
    python scripts/add_cards.py OP01-001
    python scripts/add_cards.py OP01-001 OP01-002
    python scripts/add_cards.py --list cards.txt
    python scripts/add_cards.py --set OP01
    python scripts/add_cards.py --promos
    python scripts/add_cards.py --list-sets
    python scripts/add_cards.py --check-sets
    python scripts/add_cards.py --show
    python scripts/add_cards.py --redownload-images

Requirements:
    pip install requests
"""

import json
import sys
import time
import argparse
from pathlib import Path

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("Missing dependency. Run:\n  pip install requests")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
CARDS_FILE = ROOT / "public" / "data" / "cards.json"
DECKS_FILE = ROOT / "public" / "data" / "decks.json"
FAQ_FILE   = ROOT / "public" / "data" / "faq.json"
IMAGES_DIR = ROOT / "public" / "images" / "cards"

# ── Set ID mapping ─────────────────────────────────────────────────────────────
# API uses "OP-01" format; users can type "OP01" or "OP-01" — both work.
SET_ID_MAP = {
    "OP01": "OP-01",  "OP02": "OP-02",  "OP03": "OP-03",  "OP04": "OP-04",
    "OP05": "OP-05",  "OP06": "OP-06",  "OP07": "OP-07",  "OP08": "OP-08",
    "OP09": "OP-09",  "OP10": "OP-10",  "OP11": "OP-11",  "OP12": "OP-12",
    "OP13": "OP-13",  "EB01": "EB-01",  "EB02": "EB-02",  "EB03": "EB-03",
    "PRB01": "PRB-01", "PRB02": "PRB-02",
    # Mixed sets — OP14 and OP15 share EB04
    "OP14": "OP14-EB04", "OP14-EB04": "OP14-EB04",
    "OP15": "OP15-EB04", "OP15-EB04": "OP15-EB04",
    "EB04": "OP14-EB04",
    # Starter Decks — API uses ST-01 format
    "ST01": "ST-01",  "ST02": "ST-02",  "ST03": "ST-03",  "ST04": "ST-04",
    "ST05": "ST-05",  "ST06": "ST-06",  "ST07": "ST-07",  "ST08": "ST-08",
    "ST09": "ST-09",  "ST10": "ST-10",  "ST11": "ST-11",  "ST12": "ST-12",
    "ST13": "ST-13",  "ST14": "ST-14",  "ST15": "ST-15",  "ST16": "ST-16",
    "ST17": "ST-17",  "ST18": "ST-18",  "ST19": "ST-19",  "ST20": "ST-20",
    "ST21": "ST-21",  "ST22": "ST-22",  "ST23": "ST-23",  "ST24": "ST-24",
    "ST25": "ST-25",  "ST26": "ST-26",  "ST27": "ST-27",  "ST28": "ST-28",
    # Allow already-hyphenated ST format passthrough
    "ST-01": "ST-01", "ST-02": "ST-02", "ST-03": "ST-03", "ST-04": "ST-04",
    "ST-05": "ST-05", "ST-06": "ST-06", "ST-07": "ST-07", "ST-08": "ST-08",
    "ST-09": "ST-09", "ST-10": "ST-10", "ST-11": "ST-11", "ST-12": "ST-12",
    "ST-13": "ST-13", "ST-14": "ST-14", "ST-15": "ST-15", "ST-16": "ST-16",
    "ST-17": "ST-17", "ST-18": "ST-18", "ST-19": "ST-19", "ST-20": "ST-20",
    "ST-21": "ST-21", "ST-22": "ST-22", "ST-23": "ST-23", "ST-24": "ST-24",
    "ST-25": "ST-25", "ST-26": "ST-26", "ST-27": "ST-27", "ST-28": "ST-28",
}

def normalize_set_id(raw):
    import re
    key = raw.strip().upper().replace("-", "")
    if key in SET_ID_MAP:
        return SET_ID_MAP[key]
    # Auto-hyphenate standard sets not in the map (e.g. OP16 -> OP-16, EB05 -> EB-05).
    # The optcgapi uses the "OP-16" form for regular boosters/starter decks.
    m = re.match(r"^(OP|EB|ST|PRB)(\d+)$", key)
    if m:
        return "{}-{}".format(m.group(1), m.group(2))
    return raw.strip().upper()

# ── API ────────────────────────────────────────────────────────────────────────
API_BASE         = "https://optcgapi.com/api"
CARD_ENDPOINT    = API_BASE + "/sets/card/{card_id}/"
SET_ENDPOINT     = API_BASE + "/sets/{set_id}/"
ST_CARD_ENDPOINT = API_BASE + "/decks/card/{card_id}/"
ST_SET_ENDPOINT  = API_BASE + "/decks/{set_id}/"

BANDAI_IMAGE_URL = "https://en.onepiece-cardgame.com/images/cardlist/card/{card_id}.png"
BANDAI_HEADERS   = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://en.onepiece-cardgame.com/",
}

DELAY      = 0.5
API_HEADERS = {"Accept": "application/json", "User-Agent": "optcg-judge-trainer/1.0"}


# ── Image download ─────────────────────────────────────────────────────────────
def download_image(card_id, remote_url=None):
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMAGES_DIR / "{}.png".format(card_id)

    if dest.exists():
        return "/images/cards/{}.png".format(card_id)

    urls_to_try = []
    if remote_url and remote_url.startswith("http"):
        urls_to_try.append((remote_url, API_HEADERS))
    urls_to_try.append((BANDAI_IMAGE_URL.format(card_id=card_id), BANDAI_HEADERS))

    for url, headers in urls_to_try:
        try:
            r = requests.get(url, headers=headers, timeout=15, verify=False, stream=True)
            content_type = r.headers.get("Content-Type", "")
            if r.status_code == 200 and ("image" in content_type or url.endswith(".jpg") or url.endswith(".png")):
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                return "/images/cards/{}.png".format(card_id)
        except requests.RequestException:
            continue

    return None


# ── API helpers ────────────────────────────────────────────────────────────────
def _get(url):
    try:
        r = requests.get(url, headers=API_HEADERS, timeout=10, verify=False)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print("    Network error: {}".format(e))
        return None


def fetch_card(card_id):
    cid = card_id.upper()
    data = _get(CARD_ENDPOINT.format(card_id=cid))
    if data is None and cid.startswith("ST"):
        data = _get(ST_CARD_ENDPOINT.format(card_id=cid))
    if data is None:
        return None
    if isinstance(data, list):
        if len(data) == 0:
            return None
        data = data[0]
    resolved_id = (data.get("card_set_id") or data.get("card_id") or cid).upper()
    return _normalize(data, resolved_id)


def fetch_set(set_id):
    sid = normalize_set_id(set_id)
    is_st = sid.startswith("ST-")
    url = ST_SET_ENDPOINT.format(set_id=sid) if is_st else SET_ENDPOINT.format(set_id=sid)
    data = _get(url)
    if not data:
        print("  X Set '{}' not found. Run --list-sets to see available sets.".format(set_id))
        return []
    cards_raw = data if isinstance(data, list) else data.get("cards", [])
    result = []
    for raw in cards_raw:
        if isinstance(raw, list):
            raw = raw[0] if raw else {}
        # ST endpoint uses different field names
        cid = (
            raw.get("card_set_id") or
            raw.get("card_id") or
            raw.get("id") or
            ""
        ).upper()
        if cid:
            result.append(_normalize(raw, cid))
    return result


def _normalize(raw, card_id):
    def to_int(val):
        if val is None or val == "" or val == "-":
            return None
        try:
            return int(str(val).replace(",", "").replace("+", "").strip())
        except (ValueError, TypeError):
            return None

    set_id = card_id.split("-")[0] if "-" in card_id else "UNKNOWN"
    remote_image = (
        raw.get("card_image") or
        raw.get("image_url") or
        BANDAI_IMAGE_URL.format(card_id=card_id)
    )

    return {
        "id":        card_id,
        "name":      raw.get("card_name") or raw.get("name") or card_id,
        "color":     raw.get("card_color") or raw.get("color"),
        "type":      raw.get("card_type") or raw.get("type"),
        "cost":      to_int(raw.get("card_cost") or raw.get("cost")),
        "power":     to_int(raw.get("card_power") or raw.get("power")),
        "counter":   to_int(raw.get("counter_amount") or raw.get("counter")),
        "attribute": raw.get("sub_types") or raw.get("attribute"),
        "effect":    raw.get("card_text") or raw.get("effect") or "",
        "image_url": remote_image,
        "set":       set_id,
    }


# ── Database helpers ───────────────────────────────────────────────────────────
def load_db():
    if not CARDS_FILE.exists():
        CARDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        return []
    return json.loads(CARDS_FILE.read_text(encoding="utf-8"))


def save_db(cards):
    CARDS_FILE.write_text(
        json.dumps(sorted(cards, key=lambda c: c["id"]), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def upsert_cards(new_cards, db, force):
    index = {c["id"].upper(): i for i, c in enumerate(db)}
    added = updated = skipped = 0
    for card in new_cards:
        cid = card["id"].upper()
        if cid in index:
            if force:
                db[index[cid]] = card
                updated += 1
            else:
                skipped += 1
        else:
            db.append(card)
            index[cid] = len(db) - 1
            added += 1
    return added, updated, skipped


def _summary(added, updated, skipped, failed, total):
    print("\n-- Result: {} added, {} updated, {} skipped, {} failed --".format(
        added, updated, skipped, failed))
    print("   Database: {} total cards  ->  {}".format(total, CARDS_FILE))


# ── Commands ───────────────────────────────────────────────────────────────────
def cmd_add(card_ids, force):
    db = load_db()
    added = updated = skipped = failed = 0

    for raw_id in card_ids:
        cid = raw_id.strip().upper()
        if not cid:
            continue
        print("  -> {}...".format(cid), end=" ", flush=True)
        card = fetch_card(cid)
        src = "optcgapi"
        if not card and HAS_BS4:
            # optcgapi is missing many cards (e.g. starter-deck reprints like
            # ST29-007); fall back to scraping the card from Limitless.
            card = fetch_promo_card(cid)
            if card:
                src = "Limitless"
        if not card:
            print("NOT FOUND")
            failed += 1
            time.sleep(DELAY)
            continue

        local_path = download_image(cid, card["image_url"])
        if local_path:
            card["image_url"] = local_path
            img_status = "img OK"
        else:
            img_status = "img FAILED"

        a, u, s = upsert_cards([card], db, force)
        added += a; updated += u; skipped += s

        if s:
            print("already exists (use --force to overwrite)")
        else:
            print("OK  {} [{}, {}]".format(card["name"], img_status, src))

        time.sleep(DELAY)

    save_db(db)
    _summary(added, updated, skipped, failed, len(db))


def cmd_add_set(set_id, force):
    print("Fetching all cards for set {}...".format(set_id.upper()))
    cards = fetch_set(set_id)
    if not cards:
        return

    print("Downloading {} card images...".format(len(cards)))
    img_ok = img_fail = 0
    for card in cards:
        # Only throttle when we actually hit the network — cached images that
        # already exist locally shouldn't cost a 0.5s sleep each (keeps a full
        # "update all sets" re-run fast).
        cached = (IMAGES_DIR / "{}.png".format(card["id"])).exists()
        local_path = download_image(card["id"], card["image_url"])
        if local_path:
            card["image_url"] = local_path
            img_ok += 1
        else:
            img_fail += 1
        print("  {} {}".format(card["id"], "OK" if local_path else "FAILED"), flush=True)
        if not cached:
            time.sleep(DELAY)

    db = load_db()
    added, updated, skipped = upsert_cards(cards, db, force)
    save_db(db)
    failed = len(cards) - added - updated - skipped
    print("Images: {} downloaded, {} failed".format(img_ok, img_fail))
    _summary(added, updated, skipped, failed, len(db))


def cmd_show():
    db = load_db()
    if not db:
        print("Database is empty.")
        return
    print("\n{:<12} {:<32} {:<8} {:<12} {:<6} Set".format("ID", "Name", "Color", "Type", "Img"))
    print("-" * 78)
    for c in db:
        has_img = "local" if c.get("image_url", "").startswith("/images/") else "remote"
        print("{:<12} {:<32} {:<8} {:<12} {:<6} {}".format(
            c["id"], (c["name"] or "?")[:31],
            (c["color"] or "?"), (c["type"] or "?"),
            has_img, c.get("set", "?")))
    print("\nTotal: {} cards  ->  {}".format(len(db), CARDS_FILE))


def expected_prefixes(api_id):
    """Map an API set id to the DB 'set' prefix(es) it produces.

    "OP-16" -> ["OP16"];  "OP15-EB04" -> ["OP15", "EB04"];  "ST-30" -> ["ST30"].
    """
    import re
    tokens = api_id.split("-")
    out, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        if re.fullmatch(r"[A-Za-z]+", t) and i + 1 < len(tokens) and re.fullmatch(r"\d+", tokens[i + 1]):
            out.append((t + tokens[i + 1]).upper())
            i += 2
        else:
            out.append(t.upper())
            i += 1
    return out


def released_sets():
    """Return [(api_id, name, is_deck), ...] of all released sets + decks."""
    out = []
    data = _get(API_BASE + "/allSets/")
    for s in (data or []):
        out.append((s.get("set_id", ""), s.get("set_name", ""), False))
    decks = _get(API_BASE + "/allDecks/")
    for s in (decks or []):
        sid  = s.get("structure_deck_id") or s.get("st_id") or s.get("set_id", "")
        name = s.get("structure_deck_name") or s.get("st_name") or s.get("set_name", "")
        out.append((sid, name, True))
    return out


def cmd_list_sets():
    print("Fetching available sets...")
    sets = released_sets()
    boosters = [s for s in sets if not s[2]]
    decks    = [s for s in sets if s[2]]
    if boosters:
        print("\n{:<12} {}".format("ID", "Set Name"))
        print("-" * 50)
        for sid, name, _ in boosters:
            print("{:<12} {}".format(sid, name))
    if decks:
        print("\n{:<12} {}".format("ID", "Starter Deck Name"))
        print("-" * 50)
        for sid, name, _ in decks:
            print("{:<12} {}".format(sid, name))


def cmd_update_all_sets(force):
    """Download/refresh every released set the API knows about (incl. new ones)."""
    sets = released_sets()
    ids = [sid for sid, _, _ in sets if sid]
    if not ids:
        print("Could not fetch the released-set list (network error).")
        return
    print("Updating {} sets: {}".format(len(ids), ", ".join(ids)))
    print("=" * 60, flush=True)
    for sid in ids:
        print("\n### {} ###".format(sid), flush=True)
        try:
            cmd_add_set(sid, force)
        except Exception as e:
            print("  ERROR on {}: {}".format(sid, e), flush=True)
    print("\n=== ALL SETS UPDATED ===", flush=True)


def cmd_check_sets():
    """Compare released sets (optcgapi) against what's in the local database."""
    print("Fetching released set list from optcgapi...")
    sets = released_sets()
    if not sets:
        print("  Could not fetch set list (network error).")
        return

    db = load_db()
    local = {}
    for c in db:
        local[c.get("set", "").upper()] = local.get(c.get("set", "").upper(), 0) + 1

    missing, partial, present = [], [], []
    for sid, name, is_deck in sets:
        prefixes = expected_prefixes(sid)
        have = [p for p in prefixes if local.get(p, 0) > 0]
        if not have:
            missing.append((sid, name))
        elif len(have) < len(prefixes):
            partial.append((sid, name, [p for p in prefixes if p not in have]))
        else:
            present.append((sid, name))

    print("\n=== Set coverage ===")
    print("Released: {}   In database: {}   Missing: {}".format(
        len(sets), len(present), len(missing)))

    if missing:
        print("\n-- MISSING (not in database) --")
        for sid, name in missing:
            print("  X {:<12} {}".format(sid, name))
    if partial:
        print("\n-- PARTIAL (some sub-sets missing) --")
        for sid, name, miss in partial:
            print("  ~ {:<12} {}  (missing: {})".format(sid, name, ", ".join(miss)))
    if not missing and not partial:
        print("\nAll released sets are present in the database. [OK]")

    # Promo note — promos live under set "P" and aren't in the optcgapi list.
    p_count = local.get("P", 0)
    print("\nPromo cards (P-xxx) in database: {}".format(p_count))


def cmd_redownload_images():
    db = load_db()
    if not db:
        print("Database is empty.")
        return
    ok = fail = skip = 0
    for card in db:
        cid = card["id"]
        local_dest = IMAGES_DIR / "{}.png".format(cid)
        if card.get("image_url", "").startswith("/images/") and local_dest.exists():
            skip += 1
            continue
        print("  -> {}...".format(cid), end=" ", flush=True)
        if local_dest.exists():
            local_dest.unlink()
        local_path = download_image(cid, BANDAI_IMAGE_URL.format(card_id=cid))
        if local_path:
            card["image_url"] = local_path
            print("OK")
            ok += 1
        else:
            print("FAILED")
            fail += 1
        time.sleep(DELAY)
    save_db(db)
    print("\nImages: {} downloaded, {} failed, {} already local".format(ok, fail, skip))


# ── Limitless scraper (for promo cards only) ──────────────────────────────────
LIMITLESS_BASE = "https://onepiece.limitlesstcg.com"
LIMITLESS_CDN  = "https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/one-piece/P/{card_id}_EN.webp"
LIMITLESS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html",
}

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


def _get_html(url):
    try:
        r = requests.get(url, headers=LIMITLESS_HEADERS, timeout=15, verify=False)
        if r.status_code != 200:
            return None
        if not HAS_BS4:
            return r.text  # raw text fallback
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        print("    Network error: {}".format(e))
        return None


def fetch_promo_card(card_id):
    """Scrape a single promo card from Limitless (P-001, P-002, ...).

    Limitless renders card data in a structured ``.card-text`` block with
    ``data-tooltip`` labels (Category / Color / Attribute / Type). We parse
    those directly instead of regex-matching the whole page, which is far more
    reliable.
    """
    if not HAS_BS4:
        print("    beautifulsoup4 required for promos. Run: pip install beautifulsoup4")
        return None

    cid = card_id.upper()
    soup = _get_html("{}/cards/{}".format(LIMITLESS_BASE, cid))
    if not soup:
        return None

    import re

    def to_int(val):
        if val is None:
            return None
        try:
            return int(str(val).replace(",", "").replace("+", "").strip())
        except (ValueError, TypeError):
            return None

    def tooltip(label):
        el = soup.find("span", attrs={"data-tooltip": label})
        return el.get_text(strip=True) if el else None

    block = soup.find(class_="card-text")
    if not block:
        return None

    # Name
    name_el = soup.find(class_="card-text-name")
    name = name_el.get_text(strip=True) if name_el else cid

    # Category / Color come from labelled tooltips
    card_type = tooltip("Category")
    color     = tooltip("Color")

    # Cost lives at the end of the type line: "Character • Red • 5 Cost"
    cost = None
    type_line = soup.find(class_="card-text-type")
    if type_line:
        m = re.search(r"(\d+)\s*Cost", type_line.get_text(" ", strip=True))
        if m:
            cost = m.group(1)

    # Power / Counter live in the stat section: "6000 Power • Special • +2000 Counter"
    power = counter = None
    for sec in block.find_all(class_="card-text-section"):
        txt = sec.get_text(" ", strip=True)
        pm = re.search(r"(\d+)\s*Power", txt)
        cm = re.search(r"\+?(\d+)\s*Counter", txt)
        if pm and power is None:
            power = pm.group(1)
        if cm and counter is None:
            counter = cm.group(1)

    # Family / traits (e.g. "Whitebeard Pirates") — stored as "attribute" to
    # match the optcgapi-sourced cards (which put sub_types here).
    family = tooltip("Type")

    # Effect: sections that are neither the title, the stat line, the family,
    # nor the artist credit.
    effect_parts = []
    for sec in block.find_all(class_="card-text-section", recursive=False):
        classes = sec.get("class", [])
        if "card-text-artist" in classes:
            continue
        if sec.find(class_="card-text-title"):
            continue
        if sec.find("span", attrs={"data-tooltip": "Type"}):
            continue
        txt = sec.get_text(" ", strip=True)
        if not txt or re.search(r"\d+\s*Power", txt):
            continue
        effect_parts.append(txt)
    effect = " ".join(effect_parts).strip()

    return {
        "id":        cid,
        "name":      name,
        "color":     color,
        "type":      card_type,
        "cost":      to_int(cost),
        "power":     to_int(power),
        "counter":   to_int(counter),
        "attribute": family,
        "effect":    effect,
        "image_url": LIMITLESS_CDN.format(card_id=cid),
        "set":       cid.split("-")[0] if "-" in cid else "P",
    }


def fetch_promo_pack(pack_slug):
    """
    Scrape all P-xxx card IDs from a promo pack page.
    """
    if not HAS_BS4:
        print("beautifulsoup4 required. Run: pip install beautifulsoup4")
        return []

    import re
    soup = _get_html("{}/cards/{}".format(LIMITLESS_BASE, pack_slug))
    if not soup:
        print("  Pack '{}' not found.".format(pack_slug))
        return []

    card_ids = []
    seen = set()

    # Method 1: links like /cards/P-001
    for a in soup.find_all("a", href=re.compile(r"^/cards/P-\d+")):
        m = re.search(r"/cards/(P-\d+)", a["href"])
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            card_ids.append(m.group(1))

    # Method 2: image URLs like .../P/P-001_EN.webp
    for img in soup.find_all("img"):
        src = img.get("src", "")
        m = re.search(r"/P/(P-\d+)_", src)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            card_ids.append(m.group(1))

    return card_ids


def fetch_all_promo_packs():
    """Scrape the full list of promo pack slugs from /cards/promos."""
    if not HAS_BS4:
        print("beautifulsoup4 required. Run: pip install beautifulsoup4")
        return []

    import re
    soup = _get_html("{}/cards/promos".format(LIMITLESS_BASE))
    if not soup:
        return []

    # Collect every lowercase slug link on the promos page. Card-detail links
    # (P-001) and main set pages (OP-16) are uppercase, so a lowercase-leading
    # pattern naturally skips them. We then drop the main-set landing pages
    # (e.g. "op16-the-time-of-battle") and known utility pages. Pages that
    # aren't real promo packs simply contribute no P-xxx ids downstream.
    EXCLUDED = {"promos", "advanced", "cards"}

    slugs = []
    seen = set()
    for a in soup.find_all("a", href=re.compile(r"^/cards/[a-z][a-z0-9\-]*$")):
        slug = a["href"].replace("/cards/", "")
        if slug in seen or slug in EXCLUDED:
            continue
        # Skip main-set landing pages like "op16-...", "eb05-...", "st29-...".
        if re.match(r"^(op|eb|st|prb)\d", slug):
            continue
        seen.add(slug)
        slugs.append(slug)

    return slugs


PROMO_MAX_GAP = 12  # stop the sequential scan after this many consecutive misses

def cmd_add_promos(force, max_gap=PROMO_MAX_GAP):
    """Download all promo cards (P-001, P-002, ...) from Limitless.

    Promos aren't on optcgapi, so we use two complementary passes against
    Limitless and take the union:

      1. Sequential scan from P-001 upward, stopping after `max_gap`
         consecutive missing ids. Picks up brand-new promos the moment they
         go live, even before they're listed in a pack.
      2. Pack discovery, which catches isolated clusters that sit *past* a
         numbering gap larger than `max_gap` (e.g. P-135 when P-120..134 are
         empty).
    """
    if not HAS_BS4:
        print("beautifulsoup4 required. Run: pip install beautifulsoup4")
        return

    db = load_db()
    index = {c["id"].upper(): c for c in db}
    processed = set()
    stats = {"added": 0, "updated": 0, "skipped": 0, "failed": 0}

    def handle(cid):
        """Fetch+store one promo. Returns True if the card exists, else False."""
        cid = cid.upper()
        if cid in processed:
            return True
        processed.add(cid)
        if cid in index and not force:
            stats["skipped"] += 1
            return True
        card = fetch_promo_card(cid)
        if not card:
            return False
        local_path = download_image(cid, LIMITLESS_CDN.format(card_id=cid))
        img_status = "img OK" if local_path else "img FAILED"
        if local_path:
            card["image_url"] = local_path
        a, u, s = upsert_cards([card], db, force)
        stats["added"] += a; stats["updated"] += u; stats["skipped"] += s
        print("  -> {}  {} [{}]".format(cid, card["name"], img_status), flush=True)
        time.sleep(DELAY)
        return True

    # Pass 1 — sequential scan
    print("Scanning promo cards from P-001 upward "
          "(stops after {} consecutive misses)...".format(max_gap))
    misses = n = 0
    while misses < max_gap:
        n += 1
        if handle("P-{:03d}".format(n)):
            misses = 0
        else:
            misses += 1
    print("Sequential scan reached P-{:03d}.".format(n))

    # Pass 2 — pack discovery (catches outliers past large gaps)
    print("Checking promo packs for outliers...")
    pack_ids = set()
    for slug in fetch_all_promo_packs():
        for cid in fetch_promo_pack(slug):
            pack_ids.add(cid.upper())
        time.sleep(DELAY)
    extras = sorted(c for c in pack_ids if c not in processed)
    if extras:
        print("Found {} promo(s) outside the scanned range: {}".format(
            len(extras), ", ".join(extras)))
        for cid in extras:
            handle(cid)

    save_db(db)
    _summary(stats["added"], stats["updated"], stats["skipped"], stats["failed"], len(db))


def cmd_fill_missing(force):
    """Fetch cards referenced by FAQ or meta decks but missing from the DB.

    optcgapi omits many cards (notably starter-deck reprints like ST29-007),
    so anything referenced elsewhere but absent is pulled from Limitless.
    """
    if not HAS_BS4:
        print("beautifulsoup4 required. Run: pip install beautifulsoup4")
        return

    db = load_db()
    have = {c["id"].upper() for c in db}

    referenced = set()
    if FAQ_FILE.exists():
        try:
            referenced |= {k.upper() for k in json.loads(FAQ_FILE.read_text(encoding="utf-8"))}
        except ValueError:
            pass
    if DECKS_FILE.exists():
        try:
            for d in json.loads(DECKS_FILE.read_text(encoding="utf-8")):
                if d.get("leader"):
                    referenced.add(d["leader"].upper())
                referenced |= {c.upper() for c in d.get("cards", [])}
        except ValueError:
            pass

    missing = sorted(c for c in referenced if c not in have)
    if not missing:
        print("No missing referenced cards. Database is complete.")
        return

    print("Found {} referenced card(s) missing from the DB. Fetching from Limitless...".format(
        len(missing)))
    added = updated = skipped = failed = 0
    for cid in missing:
        print("  -> {}...".format(cid), end=" ", flush=True)
        card = fetch_promo_card(cid)
        if not card:
            print("not on Limitless (skipped)")
            failed += 1
            time.sleep(DELAY)
            continue
        local_path = download_image(cid, LIMITLESS_CDN.format(card_id=cid))
        if local_path:
            card["image_url"] = local_path
        a, u, s = upsert_cards([card], db, force)
        added += a; updated += u; skipped += s
        print("OK  {}".format(card["name"]))
        time.sleep(DELAY)

    save_db(db)
    _summary(added, updated, skipped, failed, len(db))


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="OPTCG Judge Trainer -- Card Database Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/add_cards.py OP01-001 OP01-002
  python scripts/add_cards.py P-001 P-002
  python scripts/add_cards.py --list my_cards.txt
  python scripts/add_cards.py --set OP01
  python scripts/add_cards.py --promos
  python scripts/add_cards.py --force --set OP01
  python scripts/add_cards.py --list-sets
  python scripts/add_cards.py --check-sets
  python scripts/add_cards.py --fill-missing
  python scripts/add_cards.py --redownload-images
  python scripts/add_cards.py --show
        """
    )
    parser.add_argument("card_ids",            nargs="*",         help="Card IDs (e.g. OP01-001 or P-001)")
    parser.add_argument("--list",              metavar="FILE",    help="File with card IDs, one per line")
    parser.add_argument("--set",               metavar="SET_ID",  help="Import all cards from a set (e.g. OP01)")
    parser.add_argument("--update-all-sets",   action="store_true", help="Download/refresh every released set the API knows about")
    parser.add_argument("--promos",            action="store_true", help="Download ALL promo cards from Limitless TCG (requires beautifulsoup4)")
    parser.add_argument("--force",      "-f",  action="store_true", help="Overwrite existing cards")
    parser.add_argument("--show",              action="store_true", help="List all cards in the database")
    parser.add_argument("--list-sets",         action="store_true", help="Show all available sets")
    parser.add_argument("--check-sets",        action="store_true", help="Compare released sets vs. what's in the database (shows missing sets)")
    parser.add_argument("--fill-missing",      action="store_true", help="Fetch cards referenced by FAQ/decks but missing from the DB (via Limitless)")
    parser.add_argument("--redownload-images", action="store_true", help="Re-download images for all cards")
    args = parser.parse_args()

    if args.show:
        cmd_show()
    elif args.list_sets:
        cmd_list_sets()
    elif args.check_sets:
        cmd_check_sets()
    elif args.fill_missing:
        cmd_fill_missing(args.force)
    elif args.update_all_sets:
        cmd_update_all_sets(args.force)
    elif args.redownload_images:
        cmd_redownload_images()
    elif args.promos:
        cmd_add_promos(args.force)
    elif args.set:
        cmd_add_set(args.set, args.force)
    else:
        ids = list(args.card_ids)
        if args.list:
            p = Path(args.list)
            if not p.exists():
                print("File not found: {}".format(p))
                sys.exit(1)
            ids += [line.strip() for line in p.read_text().splitlines() if line.strip()]
        if not ids:
            parser.print_help()
            sys.exit(0)

        # Route P-xxx to Limitless, everything else to optcgapi
        promo_ids   = [i for i in ids if i.upper().startswith("P-")]
        regular_ids = [i for i in ids if not i.upper().startswith("P-")]

        if regular_ids:
            print("Fetching {} card(s) from optcgapi.com...\n".format(len(regular_ids)))
            cmd_add(regular_ids, args.force)

        if promo_ids:
            if not HAS_BS4:
                print("beautifulsoup4 required for promo cards. Run: pip install beautifulsoup4")
            else:
                print("Fetching {} promo card(s) from Limitless...\n".format(len(promo_ids)))
                db = load_db()
                added = updated = skipped = failed = 0
                for cid in promo_ids:
                    cid = cid.upper()
                    print("  -> {}...".format(cid), end=" ", flush=True)
                    card = fetch_promo_card(cid)
                    if not card:
                        print("FAILED")
                        failed += 1
                        continue
                    local_path = download_image(cid, LIMITLESS_CDN.format(card_id=cid))
                    if local_path:
                        card["image_url"] = local_path
                    a, u, s = upsert_cards([card], db, args.force)
                    added += a; updated += u; skipped += s
                    print("OK  {}".format(card["name"]))
                    time.sleep(DELAY)
                save_db(db)
                _summary(added, updated, skipped, failed, len(db))


if __name__ == "__main__":
    main()
