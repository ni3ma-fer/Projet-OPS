"""Vérifie que le socle répond : stockage, PostgreSQL, Airflow."""

import os
import sys
import time
import urllib.request
from pathlib import Path

import psycopg


def retry(fn, attempts: int = 30, delay: float = 5.0) -> None:
    for i in range(1, attempts + 1):
        try:
            fn()
            return
        except Exception as exc:
            if i == attempts:
                raise
            print(f"[..] {fn.__name__} pas prêt ({exc}), essai {i}/{attempts}")
            time.sleep(delay)


def check_storage() -> None:
    for var, default in (("RAW_DATA_DIR", "/app/data/raw"), ("OUTPUT_DIR", "/app/data/editions")):
        directory = Path(os.getenv(var, default))
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".healthcheck"
        probe.write_text("ok", encoding="utf-8")
        if probe.read_text(encoding="utf-8") != "ok":
            raise RuntimeError(f"écriture impossible dans {directory}")
        probe.unlink()
    print("[OK] Stockage accessible en écriture")


def check_postgres() -> None:
    db_url = os.environ["DATABASE_URL"]  # pas de valeur par défaut : aucun secret dans le code
    with psycopg.connect(db_url, connect_timeout=5) as conn:
        if conn.execute("SELECT 1").fetchone() != (1,):
            raise RuntimeError("SELECT 1 inattendu")
    print("[OK] PostgreSQL opérationnel")


def check_airflow() -> None:
    base = os.getenv("AIRFLOW_URL", "http://airflow:8080").rstrip("/")
    path = os.getenv("AIRFLOW_HEALTH_PATH", "/api/v2/monitor/health")  # Airflow 2 : /health
    with urllib.request.urlopen(f"{base}{path}", timeout=10) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
    print("[OK] Airflow joignable")


def main() -> None:
    print("=== Healthcheck La Gazette ===")
    try:
        check_storage()
        retry(check_postgres)
        retry(check_airflow)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERREUR] {exc}", file=sys.stderr)
        sys.exit(1)
    print("=== Socle opérationnel ===")


if __name__ == "__main__":
    main()