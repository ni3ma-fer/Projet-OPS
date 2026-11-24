import json

from gazette.journal import journaliser, ligne_source, resume_passage
from gazette.sources import Resultat


def test_ligne_source_compte_recus_ecrits_ignores():
    resultat = Resultat(slug="a", code_http=200, tentatives=1, duree_s=0.4)
    bilan = {"statut": "ok", "lus": 5, "recents": 3, "nouveaux": 2, "erreur": None}
    ligne = ligne_source(resultat, bilan)
    assert (ligne["recus"], ligne["ecrits"], ligne["ignores"]) == (5, 2, 3)
    assert (ligne["source"], ligne["statut"], ligne["duree_s"]) == ("a", "ok", 0.4)


def test_ligne_source_en_panne():
    resultat = Resultat(slug="b", code_http=503, erreur="HTTP 503", tentatives=3)
    bilan = {"statut": "panne", "lus": 0, "recents": 0, "nouveaux": 0, "erreur": "HTTP 503"}
    ligne = ligne_source(resultat, bilan)
    assert (ligne["recus"], ligne["ecrits"], ligne["ignores"]) == (0, 0, 0)
    assert (ligne["statut"], ligne["code_http"], ligne["tentatives"]) == ("panne", 503, 3)
    assert ligne["erreur"] == "HTTP 503"


def test_journaliser_ecrit_une_ligne_json_horodatee(capsys):
    journaliser({"evenement": "test", "titre": "été", "n": 1})
    sortie = capsys.readouterr().out
    assert sortie.count("\n") == 1
    ligne = json.loads(sortie)
    assert (ligne["evenement"], ligne["titre"], ligne["n"]) == ("test", "été", 1)
    assert "horodatage" in ligne


def test_resume_passage_compteurs():
    bilans = [
        {"slug": "a", "statut": "ok", "lus": 10, "nouveaux": 4},
        {"slug": "b", "statut": "ok", "lus": 6, "nouveaux": 0},
        {"slug": "c", "statut": "panne", "lus": 0, "nouveaux": 0},
    ]
    resume = resume_passage(bilans)
    assert resume["sources"] == 3
    assert resume["par_statut"] == {"ok": 2, "panne": 1}
    assert (resume["recus"], resume["ecrits"], resume["ignores"]) == (16, 4, 12)