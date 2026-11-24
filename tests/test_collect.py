import json
from pathlib import Path

from gazette.collect import EXTRAIT_MAX, ecrire_json, nettoyer_extrait, parse, slugifier

FIXTURE = Path(__file__).parent / "fixtures" / "liberation.xml"  # capture réelle du 13/11/2026


def items():
    return parse(FIXTURE.read_bytes(), "Libération")


# ---- Sur le vrai flux enregistré ----
def test_flux_reel_5_items():
    assert len(items()) == 5


def test_champs_autorises_uniquement():
    champs = {"source", "titre", "resume", "lien", "publie_le", "rubrique", "payload"}
    for item in items():
        assert set(item) == champs


def test_liens_vers_liberation():
    for item in items():
        assert item["lien"].startswith("https://www.liberation.fr/")


def test_dates_en_utc():
    for item in items():
        assert item["publie_le"].endswith("+00:00")


def test_resumes_propres():
    for item in items():
        assert "<" not in item["resume"]
        assert len(item["resume"]) <= EXTRAIT_MAX + 1


def test_payload_sans_texte_ni_auteur():
    for item in items():
        assert set(item["payload"]) == {"guid", "tags", "publie_brut"}


def test_ecrire_json(tmp_path):
    out = tmp_path / "raw" / "libe.json"
    ecrire_json(items(), out)
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 5


# ---- Cas limites (absents du flux du jour, construits pour le test) ----
def _rss(item_xml: str) -> bytes:
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{item_xml}</channel></rss>'.encode()


def test_item_sans_titre_ignore():
    assert parse(_rss("<item><title></title><link>https://x/</link></item>"), "s") == []


def test_item_sans_date():
    (item,) = parse(_rss("<item><title>T</title><link>https://x/</link></item>"), "s")
    assert item["publie_le"] is None


def test_date_convertie_en_utc():
    xml = "<item><title>T</title><link>https://x/</link><pubDate>Fri, 13 Nov 2026 08:30:00 +0100</pubDate></item>"
    (item,) = parse(_rss(xml), "s")
    assert item["publie_le"] == "2026-11-13T07:30:00+00:00"


def test_rubrique_et_payload():
    xml = (
        "<item><title>T</title><link>https://x/</link><guid>abc-1</guid>"
        "<category>Politique</category><category>Europe</category>"
        "<pubDate>Fri, 13 Nov 2026 08:30:00 +0100</pubDate></item>"
    )
    (item,) = parse(_rss(xml), "s")
    assert item["rubrique"] == "Politique"
    assert item["payload"] == {
        "guid": "abc-1",
        "tags": ["Politique", "Europe"],
        "publie_brut": "Fri, 13 Nov 2026 08:30:00 +0100",
    }


def test_item_sans_categorie():
    (item,) = parse(_rss("<item><title>T</title><link>https://x/</link></item>"), "s")
    assert item["rubrique"] is None
    assert item["payload"]["tags"] == []


def test_nettoyer_extrait():
    assert nettoyer_extrait("<p>Un <b>extrait</b> &amp; HTML</p>") == "Un extrait & HTML"
    assert nettoyer_extrait(None) == ""
    assert nettoyer_extrait("mot " * 200).endswith("…")


def test_slugifier():
    assert slugifier("Libération") == "liberation"
    assert slugifier("Le Dauphiné Libéré") == "le-dauphine-libere"