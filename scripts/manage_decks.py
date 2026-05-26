#!/usr/bin/env python3
"""
OPTCG Judge Trainer — Deck Manager
====================================
Creates and updates meta deck entries in public/data/decks.json.

Usage:
    python scripts/manage_decks.py --add "Red Luffy" --leader OP01-001 --set OP01 OP01-001 OP01-002 OP01-003
    python scripts/manage_decks.py --add "Red Luffy" --leader OP01-001 --set OP01 --file luffy_deck.txt
    python scripts/manage_decks.py --list
    python scripts/manage_decks.py --remove red-luffy-op01
"""

import json
import re
import argparse
from pathlib import Path

ROOT       = Path(__file__).parent.parent
DECKS_FILE = ROOT / "public" / "data" / "decks.json"
CARDS_FILE = ROOT / "public" / "data" / "cards.json"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_json(path: Path) -> list:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add_deck(name, leader, set_id, card_ids, description, force):
    decks = load_json(DECKS_FILE)
    cards_db = {c["id"].upper() for c in load_json(CARDS_FILE)}

    deck_id = slugify(f"{name}-{set_id}")

    # Check all card IDs are in the database
    missing = [cid for cid in card_ids if cid.upper() not in cards_db]
    if missing:
        print(f"⚠ Warning: these card IDs are not in cards.json:\n  {', '.join(missing)}")
        print("  Add them first with: python scripts/add_cards.py " + " ".join(missing))

    existing = next((d for d in decks if d["id"] == deck_id), None)
    if existing and not force:
        print(f"Deck '{deck_id}' already exists. Use --force to overwrite.")
        return

    deck = {
        "id":          deck_id,
        "name":        name,
        "leader":      leader.upper() if leader else None,
        "set":         set_id.upper() if set_id else None,
        "cards":       [cid.upper() for cid in card_ids],
        "description": description or "",
    }

    if existing:
        decks = [deck if d["id"] == deck_id else d for d in decks]
        print(f"✓ Updated deck: {name} ({len(deck['cards'])} cards)")
    else:
        decks.append(deck)
        print(f"✓ Added deck: {name} ({len(deck['cards'])} cards)")

    save_json(DECKS_FILE, decks)


def list_decks():
    decks = load_json(DECKS_FILE)
    if not decks:
        print("No decks in database.")
        return
    print(f"{'ID':<28} {'Name':<20} {'Leader':<12} {'Cards':<6} Set")
    print("─" * 72)
    for d in decks:
        print(
            f"{d['id']:<28} {d['name']:<20} "
            f"{(d.get('leader') or '—'):<12} {len(d['cards']):<6} {d.get('set','?')}"
        )
    print(f"\nTotal: {len(decks)} decks")


def remove_deck(deck_id):
    decks = load_json(DECKS_FILE)
    before = len(decks)
    decks = [d for d in decks if d["id"] != deck_id]
    if len(decks) == before:
        print(f"Deck '{deck_id}' not found.")
    else:
        save_json(DECKS_FILE, decks)
        print(f"✓ Removed deck: {deck_id}")


def main():
    parser = argparse.ArgumentParser(description="OPTCG Deck Manager")
    parser.add_argument("--add",         metavar="NAME",    help="Deck name to add")
    parser.add_argument("--leader",      metavar="CARD_ID", help="Leader card ID")
    parser.add_argument("--set",         metavar="SET_ID",  help="Set code, e.g. OP01")
    parser.add_argument("--description", metavar="TEXT",    help="Short description")
    parser.add_argument("--file",        metavar="FILE",    help="Text file with card IDs (one per line)")
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--list",  "-l", action="store_true", help="List all decks")
    parser.add_argument("--remove",      metavar="DECK_ID", help="Remove deck by ID")
    parser.add_argument("card_ids",      nargs="*",         help="Card IDs to include")
    args = parser.parse_args()

    if args.list:
        list_decks()
    elif args.remove:
        remove_deck(args.remove)
    elif args.add:
        ids = list(args.card_ids)
        if args.file:
            p = Path(args.file)
            ids += [l.strip() for l in p.read_text().splitlines() if l.strip()]
        if not ids:
            print("No card IDs provided. Use positional args or --file.")
            return
        add_deck(args.add, args.leader, args.set, ids, args.description, args.force)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
