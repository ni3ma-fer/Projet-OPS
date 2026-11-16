import urllib.error
import urllib.request
from pathlib import Path

from gazette import collect
from gazette import sources as src

FIXTURE = Path(__file__).parent / "fixtures" / "liberation.xml"
SOURCE = {"slug": "liberation", "nom": "Libération", "url": "https://exemple.test/rss"}


def test_source_ok(monkeypatch):
    monkeypatch.setattr(src, "fetch_statut", lambda url, timeout: (200, FIXTURE.read_bytes()))
    r = src.collecter_source(SOURCE)
    assert (r.code_http, len(r.items), r.statut) == (200, 5, "ok")


def test_source_en_panne_403(monkeypatch):
    monkeypatch.setattr(src, "fetch_statut", lambda url, timeout: (403, b""))
    r = src.collecter_source(SOURCE)
    assert (r.statut, r.erreur, r.items) == ("panne", "HTTP 403", [])


def test_source_en_panne_reseau(monkeypatch):
    def boom(url, timeout):
        raise TimeoutError("timed out")

    monkeypatch.setattr(src, "fetch_statut", boom)
    r = src.collecter_source(SOURCE)
    assert r.statut == "panne"
    assert "TimeoutError" in r.erreur


def test_source_degradee_flux_vide(monkeypatch):
    vide = b'<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
    monkeypatch.setattr(src, "fetch_statut", lambda url, timeout: (200, vide))
    assert src.collecter_source(SOURCE).statut == "degrade"


def test_lire_sources_actives_seulement(tmp_path):
    chemin = tmp_path / "s.csv"
    chemin.write_text("nom,slug,url,actif\nA,a,https://a,oui\nB,b,https://b,non\n", encoding="utf-8")
    assert [s["slug"] for s in src.lire_sources(chemin)] == ["a"]


def test_fetch_statut_garde_le_code_http(monkeypatch):
    def refuse(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    assert collect.fetch_statut("https://exemple.test/") == (403, b"")


def test_lire_sources_chemin_par_variable_d_environnement(tmp_path, monkeypatch):
    chemin = tmp_path / "autre.csv"
    chemin.write_text("nom,slug,url,actif\nA,a,https://a,oui\n", encoding="utf-8")
    monkeypatch.setenv("SOURCES_CSV", str(chemin))
    assert [s["slug"] for s in src.lire_sources()] == ["a"]