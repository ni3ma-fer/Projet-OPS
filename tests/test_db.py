import os

import pytest

from gazette.db import connexion, initialiser_schema

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL non defini"
)


def test_schema_idempotent():
    with connexion(os.environ["TEST_DATABASE_URL"]) as conn:
        initialiser_schema(conn)
        initialiser_schema(conn)  # relance sans erreur
        tables = {
            ligne[0]
            for ligne in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
        }
    assert {"sources", "articles_bruts"} <= tables