"""Connexion PostgreSQL (DATABASE_URL, jamais de mot de passe en dur)."""

from __future__ import annotations

import os

import psycopg


def connexion(url: str | None = None, **options) -> psycopg.Connection:
    """Ouvre une connexion avec un timeout de 5 s."""
    return psycopg.connect(url or os.environ["DATABASE_URL"], connect_timeout=5, **options)
