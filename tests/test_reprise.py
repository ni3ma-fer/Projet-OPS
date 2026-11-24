"""Reprise sur erreur : serveur HTTP local qui renvoie 503, puis deux passages sans doublon."""

import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from gazette.sources import collecter_source
from gazette.stockage import traiter_resultat

FIXTURE = Path(__file__).parent / "fixtures" / "liberation.xml"


@contextmanager
def serveur_local(codes, corps=b""):
    """Serveur sur 127.0.0.1 : repond les codes dans l'ordre, puis repete le dernier."""
    appels = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            code = codes[min(len(appels), len(codes) - 1)]
            appels.append(code)
            envoi = corps if code == 200 else b""
            self.send_response(code)
            self.send_header("Content-Length", str(len(envoi)))
            self.end_headers()
            self.wfile.write(envoi)

        def log_message(self, *args):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/rss", appels
    finally:
        httpd.shutdown()
        httpd.server_close()


def flux_du_jour(liens):
    """Flux RSS dont les articles sont publies maintenant (donc de moins de 24 h)."""
    date = format_datetime(datetime.now(timezone.utc))
    items = "".join(
        f"<item><title>T{lien}</title><link>https://exemple.test/{lien}</link>"
        f"<pubDate>{date}</pubDate><description>x</description></item>"
        for lien in liens
    )
    xml = f'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>{items}</channel></rss>'
    return xml.encode()


def test_source_en_panne_503_backoff_puis_echec():
    pauses = []
    with serveur_local([503]) as (url, appels):
        source = {"slug": "x", "nom": "X", "url": url}
        r = collecter_source(source, tentatives=3, pause=pauses.append)
    assert (r.statut, r.erreur, r.tentatives) == ("panne", "HTTP 503", 3)
    assert appels == [503, 503, 503]
    assert pauses == [1.0, 2.0]  # le delai double a chaque essai


def test_503_passager_puis_succes():
    with serveur_local([503, 503, 200], FIXTURE.read_bytes()) as (url, appels):
        source = {"slug": "x", "nom": "X", "url": url}
        r = collecter_source(source, pause=lambda secondes: None)
    assert (r.statut, r.tentatives, len(r.items)) == ("ok", 3, 5)
    assert appels == [503, 503, 200]


def test_403_n_est_pas_reessaye():
    with serveur_local([403]) as (url, appels):
        source = {"slug": "x", "nom": "X", "url": url}
        r = collecter_source(source, pause=lambda secondes: None)
    assert (r.statut, r.tentatives, appels) == ("panne", 1, [403])


def test_deux_passages_de_suite_zero_doublon(tmp_path):
    brut, etat = tmp_path / "brut", tmp_path / "etat"
    with serveur_local([200], flux_du_jour(["a", "b", "c"])) as (url, _):
        source = {"slug": "x", "nom": "X", "url": url}
        premier = traiter_resultat(collecter_source(source), brut, etat)
        second = traiter_resultat(collecter_source(source), brut, etat)
    assert (premier["nouveaux"], second["nouveaux"]) == (3, 0)
    fichier = next(brut.glob("dt=*/x.jsonl"))
    assert len(fichier.read_text(encoding="utf-8").splitlines()) == 3