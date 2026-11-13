# Stratégie CI/CD

1. **Outil** : GitHub Actions (`.github/workflows/ci.yml`), registre ghcr.io.
2. **Déclencheurs** : push sur `dev` et `main`, Pull Requests vers `dev` et `main`.
3. **Job `lint-test`** : `ruff check .` puis `pytest -m "not network"` (Python 3.12) ; les tests réseau sont exclus pour une CI stable.
4. **Job `build-push`** : ne démarre que si `lint-test` est vert ; construit l'image depuis le `Dockerfile` (multi-étapes, non root).
5. **Publication** : uniquement sur push `main` → `ghcr.io/ni3ma-fer/projet-ops`, tags `YYYYMMDDHHMMSS-sha` (UTC + 7 car. du commit) et `latest`.
6. **Branches** : `main` toujours déployable, alimentée seulement par PR depuis `dev` ; `dev` = intégration.
7. **Garde-fou** : `main` protégée — PR obligatoire, CI verte obligatoire, une relecture ; une CI rouge bloque le merge.
8. **Reproductible en local** : `./bin/test` lance les mêmes commandes que la CI.
9. **Hors périmètre (bornage TD 2)** : pas de déploiement automatique, pas de matrice de versions, pas de cache.
10. **Suite** : déploiement au TD 7 (Terraform), qualité SonarCloud envisagée au TD 8-9.
