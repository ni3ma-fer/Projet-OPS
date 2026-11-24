import csv
import json
from datetime import datetime, timedelta, timezone

from gazette.sources import Resultat
from gazette.stockage import (
    ecrire_rapport,
    enregistrer_articles,
    filtrer_recents,
    lire_etat,
    purger_anciens,
    traiter_resultat,
)

MAINTENANT = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)


def item(lien: str, il_y_a_h: float = 1) -> dict:
    date = datetime.now(timezone.utc) - timedelta(hours=il_y_a_h)
    return {
        "source": "Test", "titre": f"Titre {lien}", "extrait": "",
        "lien": lien, "date_publication": date.isoformat(),
    }


# ---- Brut ----
def test_filtrer_recents():
    items = [
        {"lien": "recent", "date_publication": "2026-11-16T09:00:00+00:00"},
        {"lien": "vieux", "date_publication": "2026-11-15T03:00:00+00:00"},
        {"lien": "sans-date", "date_publication": None},
    ]
    assert [i["lien"] for i in filtrer_recents(items, MAINTENANT)] == ["recent"]


def test_pas_de_doublons(tmp_path):
    items = [item("a"), item("b")]
    assert enregistrer_articles(tmp_path, "src", items, MAINTENANT) == 2
    assert enregistrer_articles(tmp_path, "src", items, MAINTENANT) == 0
    fichier = tmp_path / "dt=2026-11-16" / "src.jsonl"
    lignes = [json.loads(ligne) for ligne in fichier.read_text(encoding="utf-8").splitlines()]
    assert [ligne["lien"] for ligne in lignes] == ["a", "b"]
    assert lignes[0]["source_slug"] == "src"
    assert lignes[0]["collecte_le"] == MAINTENANT.isoformat()


def test_doublon_dans_le_meme_lot(tmp_path):
    assert enregistrer_articles(tmp_path, "src", [item("a"), item("a")], MAINTENANT) == 1


def test_purge_48h(tmp_path):
    for jour in ("2026-11-10", "2026-11-15", "2026-11-16"):
        (tmp_path / f"dt={jour}").mkdir()
        (tmp_path / f"dt={jour}" / "src.jsonl").write_text("{}\n", encoding="utf-8")
    assert purger_anciens(tmp_path, MAINTENANT) == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dt=2026-11-15", "dt=2026-11-16"]


# ---- Etat des sources ----
def test_etat_panne_puis_retour_a_ok(tmp_path):
    brut, etat = tmp_path / "brut", tmp_path / "etat"
    panne = Resultat(slug="src", code_http=403, erreur="HTTP 403")
    traiter_resultat(panne, brut, etat)
    traiter_resultat(panne, brut, etat)
    assert (lire_etat(etat, "src")["statut"], lire_etat(etat, "src")["echecs_consecutifs"]) == (
        "panne",
        2,
    )

    ok = Resultat(slug="src", code_http=200, items=[item("c")])
    assert traiter_resultat(ok, brut, etat)["nouveaux"] == 1
    apres = lire_etat(etat, "src")
    assert (apres["statut"], apres["echecs_consecutifs"]) == ("ok", 0)
    assert apres["dernier_succes"] is not None


def test_flux_sans_article_recent_est_degrade(tmp_path):
    resultat = Resultat(slug="src", code_http=200, items=[item("vieux", 48)])
    bilan = traiter_resultat(resultat, tmp_path / "brut", tmp_path / "etat")
    assert (bilan["statut"], bilan["nouveaux"]) == ("degrade", 0)


def test_rapport_csv(tmp_path):
    etat = tmp_path / "etat"
    traiter_resultat(Resultat(slug="a", code_http=403, erreur="HTTP 403"), tmp_path / "b", etat)
    sources = [
        {"slug": "a", "nom": "A", "actif": "oui"},
        {"slug": "b", "nom": "B", "actif": "oui"},
    ]
    chemin = ecrire_rapport(etat, sources)
    with chemin.open(encoding="utf-8", newline="") as f:
        lignes = {ligne["slug"]: ligne for ligne in csv.DictReader(f)}
    assert (lignes["a"]["statut"], lignes["a"]["erreur"]) == ("panne", "HTTP 403")
    assert lignes["b"]["statut"] == "inconnu"

def test_304_reste_ok_et_non_degrade(tmp_path):
    bilan = traiter_resultat(
        Resultat(slug="src", code_http=304), tmp_path / "brut", tmp_path / "etat"
    )
    assert (bilan["statut"], bilan["nouveaux"]) == ("ok", 0)