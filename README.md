# La gazette

Pipeline qui lit chaque matin la presse régionale (PQR) et nationale (PQN) via leurs flux RSS,
regroupe les articles par thèmes et publie avant 7 h une édition avec les sources et les liens.

> Projet d'étude M2Ops (EFREI). Métadonnées RSS uniquement (titre, extrait, lien, date),
> lien retour vers l'éditeur, édition non publique, purge sous 48 h. Voir `docs/cadrage.md`.

## Lancer le projet (2 commandes)

Prérequis : Git et Docker Desktop (démarré). Sous Windows, utiliser **Git Bash**.

```bash
git clone https://github.com/ni3ma-fer/Projet-OPS.git && cd Projet-OPS
./bin/dev
```

`bin/dev` crée `.env` depuis `.env.example` s'il n'existe pas, puis lance `docker compose up --build -d`.

| Service | Rôle | Accès |
|---|---|---|
| `postgres` | bases `gazette` (données) et `airflow` (métadonnées) | `localhost:5432` |
| `airflow` | orchestrateur (Airflow 3) | http://localhost:8080 — pas de login (**dev uniquement**), 1-2 min au 1er démarrage |
| `pipeline` | notre application (`python -m gazette`) | s'arrête après exécution (`Exited (0)`) |
| `prometheus` *(option)* | métriques | http://localhost:9090 |
| `grafana` *(option)* | tableaux de bord | http://localhost:3000 — identifiants dans `.env` |

Supervision : `./bin/dev --monitoring`. Arrêter : `docker compose --profile monitoring down`.

## Tester

```bash
./bin/test
```

Lance `ruff check .` puis `pytest -m "not network"`, exactement comme la CI.
Les tests du parseur tournent sur une fixture (`tests/fixtures/`), sans réseau.

Collecter une source à la main :

```bash
python -m gazette.collect --source "Libération" --url "https://www.liberation.fr/arc/outboundfeeds/rss-all/"
# -> data/raw/liberation_<horodatage>.json
```

## Arborescence

```
src/gazette/      code (collect.py : lecture RSS -> JSON)
tests/            tests pytest + fixtures/
docs/             cadrage, veille, CI/CD
infra/            config Postgres, Prometheus, Grafana
dags/             DAG Airflow (TD 3)
bin/              dev, test
```

## Contribuer

Voir [`CONTRIBUTING.md`](CONTRIBUTING.md) et la stratégie CI/CD dans [`docs/ci-cd.md`](docs/ci-cd.md).

## Dépannage

- `error during connect ... dockerDesktopLinuxEngine` : Docker Desktop n'est pas démarré.
- `bad interpreter: ^M` : fichier en fins de ligne Windows ; `.gitattributes` force LF, refaire un `git checkout` du fichier.
- `Permission denied` sur `./bin/dev` : lancer `bash bin/dev`.
