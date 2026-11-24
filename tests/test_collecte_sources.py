import urllib.error
import urllib.request
from pathlib import Path

from gazette import collect
from gazette import sources as src
from gazette.collect import Reponse

FIXTURE = Path(__file__).parent / "fixtures" / "liberation.xml"
SOURCE = {"slug": "liberation", "nom": "Libération", "url": "https://exemple.test/rss"}


def faux_fetch(code, contenu=b"", etag=None, last_modified=None):
    """Remplace fetch_conditionnel : renvoie toujours la meme reponse."""
    return lambda *args, **kwargs: Reponse(code, contenu, etag, last_modified)


def test_source_ok(monkeypatch):
    monkeypatch.setattr(src, "fetch_conditionnel", faux_fetch(200, FIXTURE.read_bytes()))
    r = src.collecter_source(SOURCE)
    assert (r.code_http, len(r.items), r.statut) == (200, 5, "ok")


def test_source_en_panne_403(monkeypatch):
    monkeypatch.setattr(src, "fetch_conditionnel", faux_fetch(403))
    r = src.collecter_source(SOURCE)
    assert (r.statut, r.erreur, r.items) == ("panne", "HTTP 403", [])


def test_source_en_panne_reseau(monkeypatch):
    def boom(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(src, "fetch_conditionnel", boom)
    r = src.collecter_source(SOURCE)
    assert r.statut == "panne"
    assert "TimeoutError" in r.erreur


def test_source_degradee_flux_vide(monkeypatch):
    vide = b'<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
    monkeypatch.setattr(src, "fetch_conditionnel", faux_fetch(200, vide))
    assert src.collecter_source(SOURCE).statut == "degrade"


def test_304_rien_de_neuf_n_est_pas_une_panne(monkeypatch):
    monkeypatch.setattr(src, "fetch_conditionnel", faux_fetch(304, etag='"v1"'))
    r = src.collecter_source(SOURCE)
    assert (r.code_http, r.statut, r.items, r.non_modifie) == (304, "ok", [], True)
    assert r.etag == '"v1"'


def test_collecter_source_envoie_etag_et_last_modified(monkeypatch):
    recus = []

    def espion(url, timeout, etag, last_modified):
        recus.append((etag, last_modified))
        return Reponse(304)

    monkeypatch.setattr(src, "fetch_conditionnel", espion)
    source = {**SOURCE, "etag": '"v1"', "last_modified": "Tue, 24 Nov 2026 07:00:00 GMT"}
    src.collecter_source(source)
    assert recus == [('"v1"', "Tue, 24 Nov 2026 07:00:00 GMT")]


def test_lire_sources_actives_seulement(tmp_path):
    chemin = tmp_path / "s.csv"
    chemin.write_text("nom,slug,url,actif\nA,a,https://a,oui\nB,b,https://b,non\n", encoding="utf-8")
    assert [s["slug"] for s in src.lire_sources(chemin)] == ["a"]


def test_fetch_statut_garde_le_code_http(monkeypatch):
    def refuse(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    assert collect.fetch_statut("https://exemple.test/") == (403, b"")


def test_fetch_conditionnel_envoie_les_en_tetes_et_accepte_304(monkeypatch):
    vus = {}

    def repond_304(req, timeout):
        vus["if-none-match"] = req.get_header("If-none-match")
        vus["if-modified-since"] = req.get_header("If-modified-since")
        raise urllib.error.HTTPError(req.full_url, 304, "Not Modified", {"ETag": '"v1"'}, None)

    monkeypatch.setattr(urllib.request, "urlopen", repond_304)
    r = collect.fetch_conditionnel(
        "https://exemple.test/", etag='"v1"', last_modified="Tue, 24 Nov 2026 07:00:00 GMT"
    )
    assert vus == {
        "if-none-match": '"v1"',
        "if-modified-since": "Tue, 24 Nov 2026 07:00:00 GMT",
    }
    assert (r.code, r.contenu, r.etag) == (304, b"", '"v1"')


def test_lire_sources_chemin_par_variable_d_environnement(tmp_path, monkeypatch):
    chemin = tmp_path / "autre.csv"
    chemin.write_text("nom,slug,url,actif\nA,a,https://a,oui\n", encoding="utf-8")
    monkeypatch.setenv("SOURCES_CSV", str(chemin))
    assert [s["slug"] for s in src.lire_sources()] == ["a"]