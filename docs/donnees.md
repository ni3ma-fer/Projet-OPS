
# Dictionnaire des données (TD 3)

Trois endroits portent des données : le **brut** (articles collectés), la table **`sources`** (catalogue et état de chaque journal) et les **journaux** (une ligne JSON par source et par passage).

## 1. Brut : `articles_bruts`

Fichiers JSON Lines : `data/raw/articles_bruts/dt=AAAA-MM-JJ/<slug>.jsonl`. Une ligne par article, un fichier par source et par jour (le dossier `dt=` est la date de récupération, en UTC).

| Champ           | Type                  | Exemple                                         | Description                                                                                                                           |
| --------------- | --------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `id`          | texte (16 car.)       | `cb3b66def4f73543`                            | Empreinte SHA-256 (tronquée) de `slug de la source` + `lien`. Stable : le même article d'une source a toujours le même `id`. |
| `source`      | texte                 | `Libération`                                 | Nom du journal, identique à la colonne `nom` de la table `sources`.                                                              |
| `lien`        | texte (URL)           | `https://www.liberation.fr/politique/…`      | Adresse de l'article chez l'éditeur. Avec `source`, c'est la clé de dédoublonnage.                                               |
| `titre`       | texte                 | `«En dix ans» : quand le Modem…`           | Titre du flux, entités HTML décodées. Jamais vide : un article sans titre est ignoré.                                             |
| `resume`      | texte                 | `Le site internet lancé par les députés…` | Extrait du flux, sans HTML, 300 caractères au plus (terminé par `…` si tronqué). Peut être vide.                               |
| `publie_le`   | texte (ISO 8601, UTC) | `2026-11-24T18:27:03+00:00`                   | Date de publication annoncée par le flux. Toujours renseignée dans le brut : un article sans date est écarté.                     |
| `recupere_le` | texte (ISO 8601, UTC) | `2026-11-24T18:38:44.274521+00:00`            | Moment où la collecte a écrit la ligne.                                                                                             |
| `rubrique`    | texte ou `null`     | `Politique`                                   | Première catégorie annoncée par le flux. `null` si le flux n'en donne pas (cas de Libération).                                  |
| `payload`     | objet                 | voir ci-dessous                                 | Métadonnées brutes du flux, **sans texte ni auteur**.                                                                         |

Contenu de `payload` :

| Clé            | Description                                                                          |
| --------------- | ------------------------------------------------------------------------------------ |
| `guid`        | Identifiant donné par l'éditeur dans le flux (souvent égal au lien), ou `null`. |
| `tags`        | Liste de toutes les catégories du flux (peut être vide).                           |
| `publie_brut` | Date de publication telle qu'écrite dans le flux, avant conversion en UTC.          |

### Règles du brut

- **Moins de 24 h** : seuls les articles publiés depuis moins de 24 h sont gardés.
- **Sans doublon** : un article déjà stocké pour la même source (même `lien`) n'est pas réécrit. Deux passages de suite ne créent aucune ligne en double.
- **Purge sous 48 h** : les dossiers `dt=` plus vieux que 48 h sont supprimés à chaque passage.
- **Pas de donnée personnelle, pas d'article entier** (cadrage) : on garde le titre, un extrait, le lien et la date. Le nom de l'auteur n'est pas conservé.

## 2. Table `sources` (PostgreSQL)

Créée par la migration `src/gazette/migrations/001_sources.sql`. L'identité de chaque source vient de `sources.csv` (copiée à chaque passage, sans toucher à l'état) ; l'état est écrit par la collecte.

| Colonne                | Type          | Description                                                                             |
| ---------------------- | ------------- | --------------------------------------------------------------------------------------- |
| `slug`               | texte, clé   | Identifiant court (`le-monde`). Nom des fichiers du brut.                             |
| `nom`                | texte, unique | Nom du journal (`Le Monde`).                                                          |
| `type`               | texte         | `PQN` (presse nationale) ou `PQR` (presse régionale).                              |
| `url_flux`           | texte         | Adresse du flux RSS/Atom.                                                               |
| `actif`              | booléen      | `false` : la source n'est jamais collectée.                                          |
| `statut`             | texte         | `inconnu`, `ok`, `degrade`, `panne` ou `sommeil` (voir `docs/collecte.md`). |
| `derniere_tentative` | horodatage    | Dernier passage, réussi ou non.                                                        |
| `derniere_reussite`  | horodatage    | Dernier passage au statut `ok`.                                                       |
| `echecs_consecutifs` | entier        | Nombre de pannes de suite. Remis à 0 au premier passage qui n'est pas une panne.       |
| `code_http`          | entier        | Code HTTP de la dernière réponse (`null` si erreur réseau).                        |
| `erreur`             | texte         | Message de la dernière erreur (`null` si tout va bien).                              |
| `etag`               | texte         | En-tête `ETag` de la dernière réponse, renvoyé en `If-None-Match`.              |
| `last_modified`      | texte         | En-tête `Last-Modified`, renvoyé en `If-Modified-Since`.                          |

Le fichier `schema_migrations` (même base) garde la liste des migrations déjà appliquées.

## 3. Journaux

Une ligne JSON par événement, sur la sortie standard (visible dans les journaux des tâches Airflow). Tous les événements portent un `horodatage` (UTC).

`source_collectee` : une ligne par source et par passage.

| Champ          | Description                                                                        |
| -------------- | ---------------------------------------------------------------------------------- |
| `source`     | Slug de la source.                                                                 |
| `statut`     | `ok`, `degrade` ou `panne`.                                                  |
| `code_http`  | Code HTTP final (`null` si erreur réseau). `304` = rien de neuf.              |
| `tentatives` | Nombre d'essais effectués (1 à 3).                                               |
| `recus`      | Articles lus dans le flux.                                                         |
| `ecrits`     | Nouveaux articles ajoutés au brut.                                                |
| `ignores`    | `recus` − `ecrits` : articles de plus de 24 h, sans date, ou déjà stockés. |
| `duree_s`    | Durée de la collecte de cette source, en secondes.                                |
| `erreur`     | Message d'erreur, ou `null`.                                                     |

`passage_termine` : une ligne par passage, avec les compteurs : `sources` (nombre collectées), `par_statut`, `recus`, `ecrits`, `ignores`, `dossiers_purges`. Une source en `sommeil` n'est pas collectée : elle n'est pas comptée dans `sources`.

## 4. Fichiers d'état (secondaires)

`data/etat/<slug>.json` et `data/etat/etat_sources.csv` : copie de l'état de chaque source, écrite à chaque passage. La table `sources` fait référence ; ces fichiers sont conservés pour un rapport lisible sans base.
