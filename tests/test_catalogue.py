from gazette.catalogue import vers_ligne
from gazette.sources import lire_sources


def test_vers_ligne():
    source = {
        "slug": "le-monde",
        "nom": "Le Monde",
        "type": "PQN",
        "url": "https://www.lemonde.fr/rss/une.xml",
        "actif": "oui",
    }
    assert vers_ligne(source) == {
        "slug": "le-monde",
        "nom": "Le Monde",
        "type": "PQN",
        "url_flux": "https://www.lemonde.fr/rss/une.xml",
        "actif": True,
    }


def test_source_inactive_devient_false():
    source = {"slug": "x", "nom": "X", "type": "PQR", "url": "https://x.fr", "actif": "non"}
    assert vers_ligne(source)["actif"] is False


def test_tout_le_csv_est_convertible():
    sources = lire_sources(seulement_actives=False)
    lignes = [vers_ligne(s) for s in sources]
    assert len(lignes) == len(sources) > 0
    assert {ligne["type"] for ligne in lignes} <= {"PQN", "PQR"}