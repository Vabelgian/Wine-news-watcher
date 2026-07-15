#!/usr/bin/env python3
"""
Wine News Watcher
Surveille des flux RSS (critiques vin + Google News par mot-clé) et envoie
un digest groupé sur Discord des nouveaux articles pertinents.

Ne récupère jamais le contenu des articles : uniquement titre, source,
lien et date. Le lecteur clique pour lire l'article sur le site d'origine.
"""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests
import yaml

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.yaml"
STATE_PATH = ROOT / "state.json"

MAX_SEEN_ENTRIES = 1000  # évite que state.json grossisse indéfiniment


def normalize(text: str) -> str:
    """Retire les accents pour un matching de mots-clés insensible aux accents."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"seen": []}


def save_state(state: dict) -> None:
    # On garde seulement les N derniers liens vus, en conservant l'ordre.
    state["seen"] = state["seen"][-MAX_SEEN_ENTRIES:]
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def match_keywords(text: str, keywords: list) -> str | None:
    norm_text = normalize(text)
    for kw in keywords:
        if normalize(kw) in norm_text:
            return kw
    return None


def google_news_feed_url(keyword: str) -> str:
    # On force la présence d'un terme lié au vin en plus du mot-clé, pour
    # éviter de remonter des actus hors-sujet sur des noms de région
    # génériques (ex: "Piémont" seul pourrait remonter de la politique,
    # de la météo, du sport local, etc.)
    query = f'"{keyword}" (vin OR wine OR vino OR cave OR vignoble)'
    q = quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl=fr&gl=FR&ceid=FR:fr"


def fetch_entries(feed_url: str) -> list:
    try:
        parsed = feedparser.parse(feed_url)
        return parsed.entries or []
    except Exception as exc:  # noqa: BLE001
        print(f"[ERREUR] flux {feed_url}: {exc}", file=sys.stderr)
        return []


def entry_id(entry) -> str:
    return entry.get("id") or entry.get("link") or entry.get("title", "")


def main() -> int:
    config = load_config()
    state = load_state()
    seen = set(state.get("seen", []))

    keywords = config.get("keywords", [])
    new_matches = []  # liste de dicts: title, link, source, keyword

    # 1) Flux directs des critiques (filtrés par mot-clé)
    for feed in config.get("feeds", []):
        entries = fetch_entries(feed["url"])
        for entry in entries:
            eid = entry_id(entry)
            if not eid or eid in seen:
                continue
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            kw = match_keywords(f"{title} {summary}", keywords)
            if kw:
                new_matches.append(
                    {
                        "title": title,
                        "link": entry.get("link", ""),
                        "source": feed["name"],
                        "keyword": kw,
                    }
                )
            seen.add(eid)

    # 2) Google News RSS par mot-clé (couvre beaucoup plus de sources)
    max_per_kw = config.get("google_news_max_per_keyword", 5)
    for kw in keywords:
        entries = fetch_entries(google_news_feed_url(kw))
        for entry in entries[:max_per_kw]:
            eid = entry_id(entry)
            if not eid or eid in seen:
                continue
            new_matches.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "source": entry.get("source", {}).get("title", "Google News")
                    if isinstance(entry.get("source"), dict)
                    else "Google News",
                    "keyword": kw,
                }
            )
            seen.add(eid)

    state["seen"] = list(seen)
    save_state(state)

    if new_matches:
        send_digest(new_matches)
        print(f"Digest envoyé ({len(new_matches)} article(s)).")
    else:
        print("Aucun nouvel article pertinent.")

    return 0


def send_digest(matches: list) -> None:
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"]

    lines = ["🍷 **Nouveaux articles vin détectés**\n"]
    for m in matches:
        lines.append(f"**[{m['keyword']}]** {m['title']} — *{m['source']}*\n{m['link']}")

    body = "\n\n".join(lines)

    # Discord limite à 2000 caractères par message : on découpe si besoin.
    chunk = ""
    chunks = []
    for line in body.split("\n\n"):
        if len(chunk) + len(line) + 2 > 1900:
            chunks.append(chunk)
            chunk = ""
        chunk += (line + "\n\n")
    if chunk:
        chunks.append(chunk)

    for c in chunks:
        resp = requests.post(webhook_url, json={"content": c.strip()}, timeout=15)
        resp.raise_for_status()


if __name__ == "__main__":
    sys.exit(main())
