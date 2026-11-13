# Contribuer à La gazette

## Branches

- `main` : toujours déployable. Chaque push sur `main` publie une image sur ghcr.io. **Jamais de commit direct.**
- `dev` : branche d'intégration de l'équipe. On y travaille au quotidien.
- Branches de sujet (facultatives, pour les gros changements) : créées depuis `dev`, nommées
  `feat/<sujet>`, `fix/<sujet>`, `chore/<sujet>`, `docs/<sujet>` — ex. `feat/collecte-libe`.

## Commits

Format : `type: message court à l'infinitif ou au présent`

| type | pour |
|---|---|
| `feat` | nouvelle fonctionnalité |
| `fix` | correction de bug |
| `test` | ajout ou modification de tests |
| `docs` | documentation |
| `build` | Dockerfile, compose, dépendances |
| `ci` | GitHub Actions |
| `chore` | rangement, configuration |

Exemples : `feat: parseur RSS Libération`, `ci: push de l'image sur ghcr`.

## Avant de pousser

```bash
./bin/test        # doit être vert : la CI lance exactement la même chose
```

Ne jamais commiter `.env` (secrets) ni `data/` (articles collectés, purgés sous 48 h).

## Passer en production (`dev` → `main`)

1. Ouvrir une Pull Request `dev` → `main`.
2. La CI doit être **verte** (lint, tests, build) : une CI rouge bloque le merge.
3. **Une relecture** par un autre membre de l'équipe (même rapide).
4. Le relecteur merge. Le push sur `main` publie l'image `ghcr.io/ni3ma-fer/projet-ops:<YYYYMMDDHHMMSS-sha>`.
