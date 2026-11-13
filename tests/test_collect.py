import json
from pathlib import Path

from gazette.collect import EXTRAIT_MAX, ecrire_json, nettoyer_extrait, parse

FIXTURE = Path(__file__).parent / "fixtures" / "liberation_sample.xml"


def items():
    return parse(FIXTURE.read_bytes(), "Libération")


def test_items_valides_seulement():
    liens = [i["lien"] for i in items()]
    assert len(liens) == 3
    assert all("sans-titre" not in lien for lien in liens)


def test_champs_autorises_uniquement():
    for item in items():
        assert set(item) == {"source", "titre", "extrait", "lien", "date_publication"}


def test_titre_entites_decodees():
    assert items()[0]["titre"] == "Premier titre & accents : éàç"


def test_extrait_sans_html():
    assert items()[0]["extrait"] == "Un extrait avec du HTML."


def test_extrait_tronque():
    extrait = items()[1]["extrait"]
    assert len(extrait) <= EXTRAIT_MAX + 1
    assert extrait.endswith("…")


def test_dates_converties_en_utc():
    assert items()[0]["date_publication"] == "2026-11-13T07:30:00+00:00"
    assert items()[1]["date_publication"] == "2026-11-13T06:00:00+00:00"
    assert items()[2]["date_publication"] is None


def test_nettoyer_extrait_vide():
    assert nettoyer_extrait(None) == ""


def test_ecrire_json(tmp_path):
    out = tmp_path / "raw" / "libe.json"
    ecrire_json(items(), out)
    relu = json.loads(out.read_text(encoding="utf-8"))
    assert len(relu) == 3

def test_slugifier():
    from gazette.collect import slugifier
    assert slugifier("Libération") == "liberation"
    assert slugifier("Le Dauphiné Libéré") == "le-dauphine-libere"