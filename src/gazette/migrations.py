"""Migrations SQL versionnees : applique dans l'ordre les fichiers NNN_nom.sql
pas encore enregistres dans la table `schema_migrations`.

    python -m gazette.migrations
"""

from __future__ import annotations

import re
from pathlib import Path

from gazette.db import connexion

DOSSIER = Path(__file__).parent / "migrations"
VERROU = 727001  # verrou applicatif : deux runs en parallele ne s'executent pas ensemble
_NOM = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")


def lister(dossier: Path = DOSSIER) -> list[tuple[str, Path]]:
    """Renvoie [(version, fichier)] triees. Refuse un nom invalide ou un numero en double."""
    trouvees: list[tuple[str, Path]] = []
    numeros: set[str] = set()
    for fichier in sorted(dossier.glob("*.sql")):
        m = _NOM.match(fichier.name)
        if not m:
            raise ValueError(f"nom de migration invalide : {fichier.name} (attendu NNN_nom.sql)")
        if m.group(1) in numeros:
            raise ValueError(f"numero de migration en double : {m.group(1)}")
        numeros.add(m.group(1))
        trouvees.append((fichier.stem, fichier))
    return trouvees


def appliquer(conn, dossier: Path = DOSSIER) -> list[str]:
    """Applique les migrations en attente (une transaction chacune). Renvoie leurs versions.

    `conn` doit etre en autocommit : chaque migration ouvre sa propre transaction.
    """
    conn.execute("SELECT pg_advisory_lock(%s)", (VERROU,))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version TEXT PRIMARY KEY,"
            " applique_le TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        deja = {ligne[0] for ligne in conn.execute("SELECT version FROM schema_migrations")}
        appliquees = []
        for version, fichier in lister(dossier):
            if version in deja:
                continue
            with conn.transaction():
                conn.execute(fichier.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            appliquees.append(version)
        return appliquees
    finally:
        conn.execute("SELECT pg_advisory_unlock(%s)", (VERROU,))


def main() -> None:
    with connexion(autocommit=True) as conn:
        appliquees = appliquer(conn)
    if appliquees:
        for version in appliquees:
            print(f"migration appliquee : {version}")
    else:
        print("base a jour : rien a appliquer")


if __name__ == "__main__":
    main()
