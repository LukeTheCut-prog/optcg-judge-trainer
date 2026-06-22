#!/usr/bin/env python3
"""
OPTCG Judge Trainer — Database Manager GUI
==========================================
Apri con: python manager_gui.py
Nessuna dipendenza aggiuntiva oltre a requests e beautifulsoup4.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import sys
import threading
import json
import re
from pathlib import Path

ROOT       = Path(__file__).parent
CARDS_FILE = ROOT / "public" / "data" / "cards.json"
DECKS_FILE = ROOT / "public" / "data" / "decks.json"

# ── Colori tema ────────────────────────────────────────────────────────────────
BG       = "#0d0a07"
SURFACE  = "#1c1814"
RAISED   = "#252018"
BORDER   = "#3a3020"
GOLD     = "#c9a84c"
GOLD_DIM = "#7a6228"
TEXT     = "#e8dfc8"
TEXT_DIM = "#a89870"
RED      = "#c0392b"
GREEN    = "#27724a"
GREEN_OK = "#3aab6e"
FONT     = ("Consolas", 10)
FONT_BIG = ("Consolas", 12, "bold")
FONT_TTL = ("Consolas", 14, "bold")


# ── Helpers ────────────────────────────────────────────────────────────────────
def run_script(args, output_widget, on_done=None):
    """Run a script in a thread, streaming output to a Text widget."""
    def _run():
        output_widget.config(state="normal")
        output_widget.delete("1.0", tk.END)
        output_widget.insert(tk.END, "$ python " + " ".join(args) + "\n\n", "cmd")
        try:
            proc = subprocess.Popen(
                [sys.executable] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(ROOT),
            )
            for line in proc.stdout:
                output_widget.insert(tk.END, line)
                output_widget.see(tk.END)
                output_widget.update()
            proc.wait()
            color = GREEN_OK if proc.returncode == 0 else RED
            output_widget.insert(tk.END, "\n[Done — exit code {}]\n".format(proc.returncode), "done")
        except Exception as e:
            output_widget.insert(tk.END, "\n[Error: {}]\n".format(e), "err")
        output_widget.config(state="disabled")
        if on_done:
            output_widget.after(0, on_done)
    threading.Thread(target=_run, daemon=True).start()


def db_stats():
    cards = json.loads(CARDS_FILE.read_text()) if CARDS_FILE.exists() else []
    decks = json.loads(DECKS_FILE.read_text()) if DECKS_FILE.exists() else []
    sets  = sorted(set(c.get("set","?") for c in cards))
    return len(cards), len(decks), sets


def styled_btn(parent, text, cmd, color=GOLD, width=22):
    b = tk.Button(
        parent, text=text, command=cmd,
        bg=RAISED, fg=color, activebackground=BORDER,
        activeforeground=color, relief="flat",
        font=FONT, width=width, cursor="hand2",
        padx=8, pady=6, bd=0,
        highlightbackground=BORDER, highlightthickness=1,
    )
    b.bind("<Enter>", lambda e: b.config(bg=BORDER))
    b.bind("<Leave>", lambda e: b.config(bg=RAISED))
    return b


def styled_entry(parent, width=30, **kw):
    e = tk.Entry(
        parent, bg=RAISED, fg=TEXT, insertbackground=GOLD,
        relief="flat", font=FONT, width=width,
        highlightbackground=BORDER, highlightthickness=1,
        **kw
    )
    return e


def section_label(parent, text):
    tk.Label(parent, text=text, bg=BG, fg=GOLD,
             font=FONT_TTL, anchor="w").pack(fill="x", pady=(16, 4))
    tk.Frame(parent, bg=GOLD_DIM, height=1).pack(fill="x", pady=(0, 10))


# ── Main App ───────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OPTCG Judge Trainer — Manager")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(900, 640)

        # Layout: left panel (controls) + right panel (output)
        pane = tk.PanedWindow(self, orient="horizontal", bg=BG,
                              sashwidth=4, sashrelief="flat")
        pane.pack(fill="both", expand=True, padx=0, pady=0)

        left  = tk.Frame(pane, bg=BG, padx=16, pady=12)
        right = tk.Frame(pane, bg=SURFACE, padx=12, pady=12)
        pane.add(left,  minsize=320, width=360)
        pane.add(right, minsize=400)

        self._build_left(left)
        self._build_right(right)
        self._refresh_stats()

    # ── Left panel ─────────────────────────────────────────────────────────────
    def _build_left(self, parent):
        # Header
        tk.Label(parent, text="⚓  OPTCG Manager", bg=BG, fg=GOLD,
                 font=FONT_TTL).pack(anchor="w")
        tk.Label(parent, text="Judge Trainer Database Tool", bg=BG,
                 fg=TEXT_DIM, font=FONT).pack(anchor="w", pady=(0, 4))

        # Stats bar
        self.stats_var = tk.StringVar(value="Loading...")
        tk.Label(parent, textvariable=self.stats_var, bg=BG,
                 fg=TEXT_DIM, font=FONT, justify="left").pack(anchor="w", pady=(0, 8))

        scroll = tk.Frame(parent, bg=BG)
        scroll.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroll, bg=BG, highlightthickness=0, bd=0)
        vsb    = tk.Scrollbar(scroll, orient="vertical", command=canvas.yview,
                              bg=BG, troughcolor=SURFACE)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(
            win_id, width=e.width))

        self._build_sections(inner)

    def _build_sections(self, p):

        # ── 1. Aggiorna tutto ──────────────────────────────────────────────────
        section_label(p, "1 · Aggiorna tutto")
        tk.Label(p, text="Scarica nuove carte di tutti i set già presenti.\nNon riscarca ciò che hai già.", 
                 bg=BG, fg=TEXT_DIM, font=FONT, justify="left").pack(anchor="w", pady=(0, 8))
        styled_btn(p, "🔄  Aggiorna database completo",
                   self.cmd_update_all, color=GREEN_OK, width=34).pack(anchor="w", pady=2)

        # ── 2. Nuovo set / set esistente ──────────────────────────────────────
        section_label(p, "2 · Aggiungi / aggiorna un set")
        tk.Label(p, text="Es: OP16, ST29, EB05, OP14-EB04, PRB01",
                 bg=BG, fg=TEXT_DIM, font=FONT).pack(anchor="w", pady=(0, 4))
        row = tk.Frame(p, bg=BG)
        row.pack(anchor="w", fill="x", pady=2)
        self.set_entry = styled_entry(row, width=14)
        self.set_entry.pack(side="left", padx=(0, 8))
        self.set_entry.bind("<Return>", lambda e: self.cmd_add_set())
        styled_btn(row, "Scarica set", self.cmd_add_set, width=16).pack(side="left")
        self.set_force_var = tk.BooleanVar()
        tk.Checkbutton(p, text="Force (riscarica anche le carte già presenti)",
                       variable=self.set_force_var,
                       bg=BG, fg=TEXT_DIM, selectcolor=RAISED,
                       activebackground=BG, font=FONT).pack(anchor="w")

        # ── 3. Carte singole ──────────────────────────────────────────────────
        section_label(p, "3 · Carte singole")
        tk.Label(p, text="Separa gli ID con spazi. Funziona anche per promo (P-001).",
                 bg=BG, fg=TEXT_DIM, font=FONT).pack(anchor="w", pady=(0, 4))
        row2 = tk.Frame(p, bg=BG)
        row2.pack(anchor="w", fill="x", pady=2)
        self.cards_entry = styled_entry(row2, width=22)
        self.cards_entry.pack(side="left", padx=(0, 8))
        self.cards_entry.bind("<Return>", lambda e: self.cmd_add_cards())
        styled_btn(row2, "Aggiungi carte", self.cmd_add_cards, width=16).pack(side="left")

        # ── 4. Promo ──────────────────────────────────────────────────────────
        section_label(p, "4 · Carte promo")
        tk.Label(p, text="Scarica tutte le carte promo (P-xxx) da Limitless TCG.",
                 bg=BG, fg=TEXT_DIM, font=FONT).pack(anchor="w", pady=(0, 8))
        styled_btn(p, "📦  Scarica tutte le promo",
                   self.cmd_promos, width=34).pack(anchor="w", pady=2)

        # ── 5. Meta deck ──────────────────────────────────────────────────────
        section_label(p, "5 · Meta deck (Limitless)")
        tk.Label(p, text="Formato (es: OP15, OP16):",
                 bg=BG, fg=TEXT_DIM, font=FONT).pack(anchor="w", pady=(0, 4))
        row3 = tk.Frame(p, bg=BG)
        row3.pack(anchor="w", fill="x", pady=2)
        self.deck_fmt_entry = styled_entry(row3, width=10)
        self.deck_fmt_entry.insert(0, "OP15")
        self.deck_fmt_entry.pack(side="left", padx=(0, 8))

        tk.Label(p, text="Share minima %:",
                 bg=BG, fg=TEXT_DIM, font=FONT).pack(anchor="w", pady=(4, 2))
        row4 = tk.Frame(p, bg=BG)
        row4.pack(anchor="w", fill="x", pady=2)
        self.deck_share_entry = styled_entry(row4, width=8)
        self.deck_share_entry.insert(0, "0.0")
        self.deck_share_entry.pack(side="left", padx=(0, 8))

        self.deck_replace_var = tk.BooleanVar(value=True)
        tk.Checkbutton(p, text="Replace (rimuovi deck vecchi del formato)",
                       variable=self.deck_replace_var,
                       bg=BG, fg=TEXT_DIM, selectcolor=RAISED,
                       activebackground=BG, font=FONT).pack(anchor="w")

        styled_btn(p, "🗂  Aggiorna meta deck",
                   self.cmd_update_decks, width=34).pack(anchor="w", pady=(8, 2))
        styled_btn(p, "🔄  Aggiorna TUTTI i formati",
                   self.cmd_update_all_decks, width=34).pack(anchor="w", pady=2)

        # ── 6. Pubblica ───────────────────────────────────────────────────────
        section_label(p, "6 · Pubblica su GitHub")
        tk.Label(p, text="Commit message:",
                 bg=BG, fg=TEXT_DIM, font=FONT).pack(anchor="w", pady=(0, 4))
        self.commit_entry = styled_entry(p, width=34)
        self.commit_entry.insert(0, "update card database")
        self.commit_entry.pack(anchor="w", pady=(0, 8))
        styled_btn(p, "🚀  git add → commit → push",
                   self.cmd_publish, color=GOLD, width=34).pack(anchor="w", pady=2)

        # ── 7. Utility ────────────────────────────────────────────────────────
        section_label(p, "7 · Utility")
        styled_btn(p, "🔍  Confronta set (mancanti)",
                   self.cmd_check_sets, color=GREEN_OK, width=34).pack(anchor="w", pady=2)
        styled_btn(p, "📋  Mostra database (--show)",
                   self.cmd_show, width=34).pack(anchor="w", pady=2)
        styled_btn(p, "🖼  Re-scarica immagini mancanti",
                   self.cmd_redownload, width=34).pack(anchor="w", pady=2)
        styled_btn(p, "🔃  Aggiorna stats",
                   self._refresh_stats, color=TEXT_DIM, width=34).pack(anchor="w", pady=(2, 16))

    # ── Right panel (output) ───────────────────────────────────────────────────
    def _build_right(self, parent):
        tk.Label(parent, text="Output", bg=SURFACE, fg=GOLD,
                 font=FONT_BIG).pack(anchor="w", pady=(0, 6))
        self.output = scrolledtext.ScrolledText(
            parent, bg=BG, fg=TEXT, insertbackground=GOLD,
            font=FONT, state="disabled", relief="flat",
            wrap="word", padx=8, pady=8,
        )
        self.output.pack(fill="both", expand=True)
        self.output.tag_config("cmd",  foreground=GOLD)
        self.output.tag_config("done", foreground=GREEN_OK)
        self.output.tag_config("err",  foreground=RED)

    # ── Stats refresh ──────────────────────────────────────────────────────────
    def _refresh_stats(self):
        try:
            n_cards, n_decks, sets = db_stats()
            sets_str = ", ".join(sets[:8]) + ("…" if len(sets) > 8 else "")
            self.stats_var.set(
                "📦 {} carte  •  🗂 {} deck\n🗃 Set: {}".format(n_cards, n_decks, sets_str or "nessuno")
            )
        except Exception as e:
            self.stats_var.set("Errore lettura DB: {}".format(e))

    def _after_run(self):
        self._refresh_stats()

    # ── Commands ───────────────────────────────────────────────────────────────
    def cmd_update_all(self):
        """Scarica/aggiorna tutti i set rilasciati (lista presa dall'API,
        quindi i nuovi set futuri vengono inclusi automaticamente)."""
        run_script(["scripts/add_cards.py", "--update-all-sets"],
                   self.output, self._after_run)

    def _run_sequence(self, cmd_list, title):
        """Run a list of commands sequentially in a thread."""
        self.output.config(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "=== {} ===\n\n".format(title), "cmd")
        self.output.config(state="disabled")

        def _seq():
            for args in cmd_list:
                done_event = threading.Event()
                self.output.after(0, lambda a=args: self._start_cmd(a, done_event))
                done_event.wait()
            self.output.after(0, self._after_run)

        threading.Thread(target=_seq, daemon=True).start()

    def _start_git_cmd(self, args, done_event):
        """Run a git command directly (no python prefix)."""
        self.output.config(state="normal")
        self.output.insert(tk.END, "\n$ {}\n".format(" ".join(args)), "cmd")
        self.output.config(state="disabled")
        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, cwd=str(ROOT),
            )
            def _read():
                for line in proc.stdout:
                    self.output.config(state="normal")
                    self.output.insert(tk.END, line)
                    self.output.see(tk.END)
                    self.output.update()
                    self.output.config(state="disabled")
                proc.wait()
                done_event.set()
            threading.Thread(target=_read, daemon=True).start()
        except Exception as e:
            self.output.config(state="normal")
            self.output.insert(tk.END, "Error: {}\n".format(e), "err")
            self.output.config(state="disabled")
            done_event.set()

    def _start_cmd(self, args, done_event):
        self.output.config(state="normal")
        self.output.insert(tk.END, "\n$ python {}\n".format(" ".join(args)), "cmd")
        self.output.config(state="disabled")
        try:
            proc = subprocess.Popen(
                [sys.executable] + args,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, cwd=str(ROOT),
            )
            def _read():
                for line in proc.stdout:
                    self.output.config(state="normal")
                    self.output.insert(tk.END, line)
                    self.output.see(tk.END)
                    self.output.update()
                    self.output.config(state="disabled")
                proc.wait()
                done_event.set()
            threading.Thread(target=_read, daemon=True).start()
        except Exception as e:
            self.output.config(state="normal")
            self.output.insert(tk.END, "Error: {}\n".format(e), "err")
            self.output.config(state="disabled")
            done_event.set()

    def cmd_add_set(self):
        s = self.set_entry.get().strip()
        if not s:
            messagebox.showwarning("Input mancante", "Inserisci un set ID (es: OP16)")
            return
        args = ["scripts/add_cards.py", "--set", s]
        if self.set_force_var.get():
            args.append("--force")
        run_script(args, self.output, self._after_run)

    def cmd_add_cards(self):
        raw = self.cards_entry.get().strip()
        if not raw:
            messagebox.showwarning("Input mancante", "Inserisci uno o più card ID")
            return
        ids = raw.split()
        args = ["scripts/add_cards.py"] + ids
        run_script(args, self.output, self._after_run)

    def cmd_promos(self):
        run_script(["scripts/add_cards.py", "--promos"], self.output, self._after_run)

    def cmd_update_decks(self):
        fmt   = self.deck_fmt_entry.get().strip() or "OP15"
        share = self.deck_share_entry.get().strip() or "0.0"
        args  = ["scripts/update_meta_decks.py", "--format", fmt, "--min-share", share]
        if self.deck_replace_var.get():
            args.append("--replace")
        run_script(args, self.output, self._after_run)

    def cmd_update_all_decks(self):
        share = self.deck_share_entry.get().strip() or "0.0"
        run_script(
            ["scripts/update_meta_decks.py", "--update-all", "--min-share", share],
            self.output, self._after_run
        )

    def cmd_publish(self):
        msg = self.commit_entry.get().strip() or "update card database"
        if not messagebox.askyesno("Conferma", 
            "Pubblicare su GitHub?\n\ngit add .\ngit commit -m \"{}\"\ngit push".format(msg)):
            return
        def _git():
            self.output.config(state="normal")
            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, "=== Pubblicazione su GitHub ===\n\n", "cmd")
            self.output.config(state="disabled")
            for cmd in [
                ["git", "add", "."],
                ["git", "commit", "-m", msg],
                ["git", "push"],
            ]:
                done = threading.Event()
                self.output.after(0, lambda c=cmd: self._start_git_cmd(c, done))
                done.wait()
            self.output.after(0, lambda: self.output.config(state="normal"))
            self.output.after(0, lambda: self.output.insert(tk.END, "\n✓ Push completato!\n", "done"))
            self.output.after(0, lambda: self.output.config(state="disabled"))
        threading.Thread(target=_git, daemon=True).start()

    def cmd_check_sets(self):
        run_script(["scripts/add_cards.py", "--check-sets"], self.output)

    def cmd_show(self):
        run_script(["scripts/add_cards.py", "--show"], self.output)

    def cmd_redownload(self):
        run_script(["scripts/add_cards.py", "--redownload-images"], self.output, self._after_run)


if __name__ == "__main__":
    app = App()
    app.mainloop()
