import os
import sys
from pathlib import Path
import urllib.request
import psycopg2
from sentence_transformers import SentenceTransformer


def check_storage() -> None:
    raw_dir = Path(os.getenv("RAW_DATA_DIR", "/app/data/raw"))
    out_dir = Path(os.getenv("OUTPUT_DIR", "/app/data/editions"))

    for directory in (raw_dir, out_dir):
        directory.mkdir(parents=True, exist_ok=True)
        test_file = directory / ".healthcheck"
        test_file.write_text("ok", encoding="utf-8")
        assert test_file.read_text(encoding="utf-8") == "ok"
        test_file.unlink()

    print(f"[OK] Stockage volumes montés : {raw_dir} et {out_dir}")


def check_postgres() -> None:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        conn = psycopg2.connect(db_url, connect_timeout=5)
    else:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            user=os.getenv("POSTGRES_USER", "gazette"),
            password=os.getenv("POSTGRES_PASSWORD", "gazette_secret"),
            dbname=os.getenv("POSTGRES_DB", "gazette"),
            connect_timeout=5,
        )
    with conn.cursor() as cur:
        cur.execute("SELECT 1;")
        result = cur.fetchone()
    conn.close()

    assert result == (1,)
    print("[OK] Connexion PostgreSQL opérationnelle")


def check_orchestrator() -> None:
    airflow_url = os.getenv("AIRFLOW_URL", "http://airflow:8080")
    health_url = f"{airflow_url.rstrip('/')}/health"
    with urllib.request.urlopen(health_url, timeout=10) as response:
        assert response.status == 200
    print(f"[OK] Orchestrateur Airflow joignable ({health_url})")


def check_nlp_model() -> None:
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    vec = model.encode(["Test santé pipeline La Gazette"])
    assert vec.shape[0] == 1
    print("[OK] Modèle d'embeddings BERTopic chargé en local")


def main() -> None:
    print("=== Démarrage du healthcheck La Gazette ===")
    try:
        check_storage()
        check_postgres()
        check_orchestrator()
        check_nlp_model()
    except Exception as exc:
        print(f"[ERREUR] Échec du healthcheck : {exc}", file=sys.stderr)
        sys.exit(1)

    print("=== Socle Docker 100 % opérationnel ===")


if __name__ == "__main__":
    main()