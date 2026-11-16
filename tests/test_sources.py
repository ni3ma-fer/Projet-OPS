import csv
from pathlib import Path

SOURCES = Path(__file__).parent.parent / "sources.csv"


def lire():
    with SOURCES.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_colonnes_attendues():
    assert {"nom", "slug", "type", "format", "url", "actif"} <= set(lire()[0])


def test_slugs_uniques():
    slugs = [s["slug"] for s in lire()]
    assert len(slugs) == len(set(slugs))


def test_urls_https():
    for s in lire():
        assert s["url"].startswith("https://"), s["nom"]


def test_type_et_actif_valides():
    for s in lire():
        assert s["type"] in {"PQN", "PQR"}, s["nom"]
        assert s["actif"] in {"oui", "non"}, s["nom"]