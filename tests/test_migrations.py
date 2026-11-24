"""Tests des migrations, sans base de donnees (la CI n'a pas de PostgreSQL)."""

import pytest

from gazette.migrations import DOSSIER, lister

COLONNES_ENONCE = [
    "nom", "type", "url_flux", "actif", "derniere_reussite",
    "echecs_consecutifs", "etag", "last_modified",
]


def test_migrations_triees_et_001_presente():
    versions = [v for v, _ in lister()]
    assert versions == sorted(versions)
    assert versions[0] == "001_sources"


def test_001_contient_les_colonnes_de_l_enonce():
    sql = (DOSSIER / "001_sources.sql").read_text(encoding="utf-8")
    for colonne in COLONNES_ENONCE:
        assert colonne in sql, colonne


def test_nom_invalide_refuse(tmp_path):
    (tmp_path / "sources.sql").write_text("SELECT 1;")
    with pytest.raises(ValueError, match="invalide"):
        lister(tmp_path)


def test_numero_en_double_refuse(tmp_path):
    (tmp_path / "001_a.sql").write_text("SELECT 1;")
    (tmp_path / "001_b.sql").write_text("SELECT 1;")
    with pytest.raises(ValueError, match="double"):
        lister(tmp_path)
