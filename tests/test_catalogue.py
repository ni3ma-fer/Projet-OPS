from datetime import datetime, timezone

from gazette.catalogue import parametres_passage, vers_ligne
from gazette.sources import Resultat, lire_sources

MAINTENANT = datetime(2026, 11, 24, 18, 0, tzinfo=timezone.utc)


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


def test_passage_200_remplace_les_validateurs():
    r = Resultat(slug="a", code_http=200, etag='"v2"', last_modified="lm")
    p = parametres_passage(r, "ok", None, MAINTENANT)
    assert p["remplacer"] is True
    assert (p["etag"], p["last_modified"]) == ('"v2"', "lm")
    assert p["reussite"] is True


def test_passage_304_garde_les_validateurs_memorises():
    p = parametres_passage(Resultat(slug="a", code_http=304), "ok", None, MAINTENANT)
    assert p["remplacer"] is False
    assert p["etag"] is None  # None + COALESCE en SQL = on garde l'ancien
    assert p["reussite"] is True


def test_passage_en_panne_ne_touche_pas_aux_validateurs():
    r = Resultat(slug="a", code_http=403, erreur="HTTP 403", etag='"piege"')
    p = parametres_passage(r, "panne", "HTTP 403", MAINTENANT)
    assert p["remplacer"] is False
    assert (p["etag"], p["last_modified"]) == (None, None)
    assert p["reussite"] is False


def test_flux_degrade_n_est_pas_une_reussite():
    r = Resultat(slug="a", code_http=200)
    p = parametres_passage(r, "degrade", "aucun article de moins de 24 h", MAINTENANT)
    assert p["reussite"] is False