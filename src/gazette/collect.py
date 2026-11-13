"""Collecte d'une source RSS/Atom : lecture, parsing, ecriture JSON.

Seules les metadonnees sont gardees (titre, extrait, lien, date), jamais l'article entier.
"""

from __future__ import annotations

import argparse
import calendar
import html
import json
import re
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import feedparser

USER_AGENT = "LaGazette/0.1 (projet etudiant EFREI M2Ops)"
EXTRAIT_MAX = 300
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def fetch(url: str, timeout: float = 15.0) -> bytes:
    """Telecharge le flux brut (aucun contournement : un 403 reste un 403)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def nettoyer_extrait(texte: str | None, max_len: int = EXTRAIT_MAX) -> str:
    """Retire le HTML, decode les entites, compacte les espaces, tronque."""
    if not texte:
        return ""
    texte = _SPACE_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", texte))).strip()
    if len(texte) <= max_len:
        return texte
    return texte[:max_len].rsplit(" ", 1)[0] + "…"


def _date_utc(entry) -> str | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc).isoformat()


def parse(contenu: bytes, source: str) -> list[dict]:
    """Transforme un flux RSS/Atom en liste d'items normalises."""
    flux = feedparser.parse(contenu)
    items = []
    for entry in flux.entries:
        lien = entry.get("link")
        titre = (entry.get("title") or "").strip()
        if not lien or not titre:
            continue
        items.append(
            {
                "source": source,
                "titre": html.unescape(titre),
                "extrait": nettoyer_extrait(entry.get("summary")),
                "lien": lien,
                "date_publication": _date_utc(entry),
            }
        )
    return items


def slugifier(nom: str) -> str:
    """'Libération' -> 'liberation' (pour nommer les fichiers)."""
    sans_accents = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sans_accents.lower()).strip("-")


def ecrire_json(items: list[dict], chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Collecte une source RSS vers un fichier JSON")
    ap.add_argument("--source", required=True, help="nom de la source (cf. sources.csv)")
    ap.add_argument("--url", required=True, help="URL du flux RSS/Atom")
    ap.add_argument("--out", type=Path, default=None, help="fichier JSON de sortie")
    args = ap.parse_args(argv)

    items = parse(fetch(args.url), args.source)
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or Path("data/raw") / f"{slugifier(args.source)}_{horodatage}.json"
    ecrire_json(items, out)
    print(f"{len(items)} items -> {out}")


if __name__ == "__main__":
    main()