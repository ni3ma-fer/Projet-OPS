
# Collecte planifiée (TD 3)

## En bref

- **DAG Airflow `collecte_sources`** (`dags/collecte_sources.py`), toutes les heures (`@hourly`), une tâche par source (dynamic task mapping). La liste des sources vient de `sources.csv` (colonne `actif`).
- **Brut** : fichiers JSON Lines dans `data/raw/articles_bruts/dt=AAAA-MM-JJ/<slug>.jsonl`. Champs : `source`, `titre`, `extrait`, `lien`, `date_publication` (UTC), `source_slug`, `collecte_le`. Jamais le texte intégral.
- **État de chaque source** : `data/etat/<slug>.json`, assemblé dans `data/etat/etat_sources.csv` (la « table des sources »).

## Règles de collecte

- Seuls les articles de **moins de 24 h** sont gardés ; un article sans date est écarté.
- **Sans doublons** : un article déjà stocké pour la même source (même lien) n'est pas réécrit.
- **Purge sous 48 h** : les dossiers `dt=…` plus vieux que 48 h sont supprimés à chaque exécution.
- Timeout de 15 s par source, User-Agent déclaré (`LaGazette/0.1 (projet etudiant EFREI M2Ops)`), **aucun contournement** : un 403 ou une protection anti-robots reste un échec.
- Une source en panne **ne fait pas échouer** l'exécution : son état est enregistré et les autres sources continuent.

## Statuts d'une source

| Statut      | Signification                                                         |
| ----------- | --------------------------------------------------------------------- |
| `ok`      | HTTP 200 et au moins un article de moins de 24 h                      |
| `degrade` | HTTP 200 mais flux vide ou sans article de moins de 24 h              |
| `panne`   | erreur réseau, ou code HTTP différent de 200 (403, 302 en boucle…) |
| `inconnu` | jamais collectée                                                     |

Le CSV donne aussi le code HTTP, le nombre d'articles lus dans le flux, la date de la dernière collecte, du dernier succès, le nombre d'échecs consécutifs et le message d'erreur.

## Choix

- **JSON Lines plutôt que Parquet** : ajout en fin de fichier simple, lisible à l'œil, aucune dépendance en plus. Parquet ne s'ajoute pas ligne à ligne.
- **Brut en fichiers, pas en base** : décision du TD 1. PostgreSQL est réservé aux données nettoyées (TD suivants).
- **Un fichier par source** (brut et état) : les tâches Airflow tournent en parallèle sans jamais écrire dans le même fichier.
- **Image Airflow dédiée** (`infra/airflow/Dockerfile`) : l'image officielle plus le paquet `gazette` ; tout est décrit en code (Compose), rien n'est installé à la main.

## Lancer et arrêter

```bash
docker compose up -d postgres airflow     # Airflow : http://localhost:8080
docker compose exec airflow airflow dags trigger collecte_sources   # lancer une exécution tout de suite
docker compose stop                       # arrêter (la collecte s'arrête aussi)
```

Après une modification du code dans `src/`, reconstruire l'image : `docker compose up -d --build airflow`.

## Limites connues

- **Sud Ouest** : en `panne`. Le site redirige en boucle avec des cookies anti-robots (Imperva). Pas de contournement, conformément au cadrage ; la source reste active et sera retentée.
- La collecte ne tourne que lorsque Docker tourne ; les heures manquées ne sont pas rattrapées (`catchup=False`).
- Airflow est en mode `standalone`, sans connexion (dev uniquement) : à durcir au TD 7.
- Les titres d'un même groupe (EBRA) partagent des articles : le dédoublonnage entre sources relève du nettoyage.
