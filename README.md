# OPTCG Judge Trainer ⚓

A flashcard-style study tool for **One Piece Card Game** judges. Learn card effects by heart — see the image, guess the effect, reveal to confirm.

**[▶ Open Web App](https://LukeTheCut-prog.github.io/optcg-judge-trainer/)**

---

## Features

- 🎲 **Random mode** — study the full card catalog, optionally filtered by color
- 🗂️ **Deck mode** — study a specific meta deck
- 👁 **Reveal on click** — image + stats always visible, effect hidden until you tap
- 📱 **Mobile-friendly** — works in any browser, no install needed
- 🖥️ **Desktop app** — installable via Tauri (see below)
- 🔄 **Auto-updates** — database updates pushed to the repo are live immediately on the web

---

## Quick Start (Web)

No setup needed. Open the link above in any browser.

---

## Local Development

```bash
# 1. Clone the repo
git clone https://github.com/LukeTheCut-prog/optcg-judge-trainer.git
cd optcg-judge-trainer

# 2. Install dependencies
npm install

# 3. Start dev server
npm run dev
```

---

## Managing the Card Database

All card data lives in **`public/data/cards.json`**.  
You manage it locally with the provided Python script, then push to GitHub.

### Add cards by ID

```bash
# Install Python dependencies (once)
pip install requests beautifulsoup4

# Add one or more cards
python scripts/add_cards.py OP01-001
python scripts/add_cards.py OP01-001 OP01-002 OP02-003

# Add from a text file (one ID per line)
python scripts/add_cards.py --list my_cards.txt

# Re-fetch and overwrite an existing card
python scripts/add_cards.py --force OP01-001

# List all cards currently in the database
python scripts/add_cards.py --show
```

### Manage meta decks

Deck data lives in **`public/data/decks.json`**.

```bash
# Add a new meta deck
python scripts/manage_decks.py \
  --add "Red Luffy" \
  --leader OP01-001 \
  --set OP01 \
  --description "Classic Red aggro deck" \
  OP01-001 OP01-002 OP01-003 OP02-001

# Add deck from a file
python scripts/manage_decks.py \
  --add "Blue Law" --leader OP01-060 --set OP01 \
  --file decks/blue_law.txt

# List all decks
python scripts/manage_decks.py --list

# Remove a deck by its ID
python scripts/manage_decks.py --remove blue-law-op01
```

### Publish updates

```bash
git add public/data/
git commit -m "chore: add OP05 cards"
git push
```

GitHub Actions will automatically rebuild and redeploy the web app within ~2 minutes.

---

## Deploying to GitHub Pages

1. Push this repo to GitHub
2. Go to **Settings → Pages → Source** → select **GitHub Actions**
3. Edit `vite.config.js` and replace `optcg-judge-trainer` with your actual repo name
4. Push any commit — the workflow will build and deploy automatically

---

## Desktop App (Tauri)

> Requires Rust + Tauri CLI. See [tauri.app/start](https://tauri.app/start/) for setup.

```bash
npm install
npm run tauri dev      # development
npm run tauri build    # production binary
```

For auto-updates from GitHub Releases, configure `tauri.conf.json` with your repo's
update endpoint. See the [Tauri updater docs](https://tauri.app/plugin/updater/).

---

## Security

- **No API keys** in the app — scraping runs locally on your machine
- **Static files only** — the app reads JSON from the repo, no backend
- **No user data** collected or stored anywhere
- **No auth required** — fully open, offline-capable after first load

---

## Card Data Source

Card data is fetched from the official One Piece Card Game website
([en.onepiece-cardgame.com](https://en.onepiece-cardgame.com)).  
This project is not affiliated with or endorsed by Bandai.

---

## Contributing

Open an issue or PR to suggest new meta decks or improvements.
