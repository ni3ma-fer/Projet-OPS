
# Note de cadrage — La gazette

**Équipe :** Ervin, Arnaud, Naim · **Module :** M2Ops (M2-DE2, EFREI) · **Version :** TD 1 — 13/11/2026

## 1. Le besoin

Chaque matin, savoir **de quoi parle la presse française** : quels sujets occupent les rédactions régionales (PQR) et nationales (PQN) aujourd'hui, quels journaux en parlent, et où lire la suite. La gazette lit automatiquement les flux que les éditeurs publient, regroupe les articles par thème et publie **avant 7 h** une édition du jour : une liste de thèmes, chacun avec ses sources et ses liens.

## 2. Périmètre

| Dedans                                                           | Dehors                                                    |
| ---------------------------------------------------------------- | --------------------------------------------------------- |
| Collecte des flux RSS/Atom de 10 PQN et 14 PQR (`sources.csv`) | Scraping des pages HTML ou du texte intégral             |
| Stockage du brut, nettoyage et contrôle qualité                | Résumés des articles par LLM                            |
| Regroupement automatique par thèmes                             | Front soigné (l'édition est une page HTML simple)       |
| Publication quotidienne d'une édition HTML                      | Commentaires, profils, toute donnée personnelle          |
| Ordonnancement, supervision, alertes                             | Archive historique de la presse                           |
| Déploiement reproductible (conteneurs, IaC, CI/CD)              | Sources hors presse quotidienne (blogs, réseaux sociaux) |

## 3. Contraintes

- **Délai :** édition publiée chaque jour à **7 h** (Europe/Paris).
- **Fraîcheur :** uniquement des articles publiés depuis **moins de 24 h**.
- **Données conservées :** titre, extrait, lien et date. **Jamais l'article entier.**
- **Éditeurs :** respect des CGU et du `robots.txt`, User-Agent identifié, une requête par flux et par passage, lien vers la source dans l'édition.
- **Cadre d'usage validé par l'encadrant (13/11/2026) :** les CGU des 24 sources ont été lues (`sources.csv`, colonne `conditions`) ; la plupart limitent à un usage personnel et 16 s'opposent à la fouille de textes (réserve TDM). L'usage est accepté **dans le cadre pédagogique du module**, avec ces garde-fous :
  - uniquement les métadonnées du flux RSS officiel (titre, extrait court, date, lien), jamais l'article ;
  - lien retour vers l'article source pour chaque entrée de l'édition ;
  - édition non publique, non commerciale, réservée au module ;
  - purge des données collectées sous 48 h (clause la plus stricte relevée : La Tribune) ;
  - aucun contournement de blocage (403, robots.txt) : la source est alors retirée.
- **Données personnelles :** aucune.
- **Budget zéro :** nos machines, puis l'infrastructure fournie (TD 4 ou 6), et des outils open source ou gratuits.
- **Infrastructure as code dès le TD 2 :** rien d'installé ni de configuré à la main.
- **Priorité :** le temps en trop va dans la robustesse et l'observabilité, pas dans les fonctionnalités.

## 4. Architecture et stack retenue

Six boîtes, orchestrées par un DAG Airflow quotidien (schéma : `docs/architecture.png`) :

| Boîte                   | Outil retenu                                                                                                                                                          | Pourquoi                                                                                                                                                                       |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1. Collecte              | Python + `feedparser` (RSS/Atom)                                                                                                                                    | Canal ouvert par les éditeurs aux machines, contient exactement ce qu'on a le droit de garder                                                                                 |
| 2. Stockage brut         | Fichiers sur volume Docker (`data/raw/AAAA-MM-JJ/`, JSON Lines privilégié, Parquet possible)                                                                      | Brut immuable et rejouable, format standard, hors base                                                                                                                         |
| 3. Nettoyage et qualité | Python, puis **PostgreSQL**                                                                                                                                     | Dates en UTC, HTML retiré, doublons (URL unique), fenêtre < 24 h, rejets tracés                                                                                             |
| 4. Thèmes               | **BERTopic** (embeddings multilingues + HDBSCAN)                                                                                                                | Rapproche des titres de même sens avec des mots différents, mots-clés automatiques, sans modèle génératif                                                                |
| 5. Livraison             | Page HTML générée (Jinja2) servie en statique                                                                                                                      | Simple, suffisant (le front est hors sujet)                                                                                                                                    |
| 6. Supervision           | **Prometheus / Grafana** (métriques et alertes) + **interface Airflow** (état des tâches et logs, écrits en JSON structuré pour pouvoir les filtrer) | Grafana dit *combien* (une source à 0 article), Airflow dit *quoi* (quelle tâche a échoué), les logs disent *pourquoi* (HTTP 404, flux déplacé) ; alerte avant 7 h |
| Ordonnancement           | **Apache Airflow**                                                                                                                                              | Standard du marché, collecte en parallèle par source, reprises, historique                                                                                                   |
| Conteneurs / IaC         | **Docker Compose**, puis **Terraform + cloud-init**                                                                                                       | Tout démarre avec `docker compose up` ; infra fournie créée en code                                                                                                       |
| CI/CD                    | **GitHub Actions** → images sur **ghcr.io** (tag `YYYYMMDDHHMMSS-sha`)                                                                                 | Intégré au dépôt, gratuit                                                                                                                                                  |

## 5. Alternatives écartées

Le détail est dans `docs/veille.md`.

- **Scraping HTML :** fragile, souvent contraire aux CGU, risque de texte intégral et de données personnelles.
- **Prefect / cron :** Prefect plus léger mais moins répandu ; cron sans reprise ni suivi, et cron GitHub Actions pouvant être retardé.
- **Brut dans PostgreSQL / MongoDB :** on garde le brut immuable hors base ; MongoDB ajouterait une seconde base.
- **MinIO :** n'est plus maintenu (dépôt archivé en 2026). **Garage :** crédible mais inutile pour quelques Mo par jour, à réévaluer avec l'infra fournie.
- **CSV pour les articles :** casse sur les virgules et retours à la ligne, pas de types.
- **TF-IDF + clustering :** ne rapproche pas les synonymes sur des textes courts, gardé en **solution de repli**. **LLM :** hors sujet.
- **Ansible :** surdimensionné pour une seule VM (cloud-init suffit). **Kubernetes :** surdimensionné.
- **GitLab CI :** équivalent, mais nous éloignerait de la stack du module (GitHub Actions + ghcr.io).

## 6. Risques

| Risque                                                          | Impact                                       | Parade                                                                                                                                                                                                                |
| --------------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Un flux meurt ou change d'URL                                   | Source manquante dans l'édition             | Alerte « 0 article », plusieurs sources par région, `sources.csv` versionné                                                                                                                                     |
| Fenêtre RSS courte (20 à 50 derniers articles)                | Articles de la veille manqués               | Collecte toutes les heures + dédoublonnage, ou limite assumée et documentée                                                                                                                                        |
| CGU restrictives (usage personnel, réserve TDM sur 16 sources) | Usage hors du cadre autorisé par l'éditeur | Usage pédagogique validé par l'encadrant ; métadonnées RSS + lien retour uniquement ; édition non publique ; purge 48 h. Hors du module : autorisation de l'éditeur (syndication) ou licence de panorama du CFC |
| Un éditeur bloque la collecte (403)                            | Source perdue                                | Pas de contournement : retrait de la source, alerte, remplacement si besoin (cas du Télégramme)                                                                                                                     |
| Pipeline en échec ou en retard à 7 h                          | Pas d'édition                               | Reprises Airflow, marge horaire (démarrage 05:30), alerte Grafana                                                                                                                                                    |
| BERTopic trop lourd ou instable                                 | Thèmes incohérents, image trop grosse      | Modèle téléchargé au build, graine fixée, repli TF-IDF                                                                                                                                                           |
| Données hétérogènes (dates, encodage, HTML)                 | Articles faux ou rejetés                    | Contrôle qualité, table de rejets, tests sur des flux réels                                                                                                                                                        |
| Machine de l'équipe éteinte (avant l'infra fournie)           | Pas d'édition                               | Accepté jusqu'au déploiement sur l'infra fournie                                                                                                                                                                    |

## 7. Rôles dans l'équipe

| Membre      | Rôle principal                                    | Binôme / suppléant |
| ----------- | -------------------------------------------------- | -------------------- |
| _Prénom_ | Collecte et sources (boîtes 1–2)                 | _Prénom_          |
| _Prénom_ | Nettoyage, qualité, PostgreSQL (boîte 3)         | _Prénom_          |
| _Prénom_ | Thèmes et édition (boîtes 4–5)                 | _Prénom_          |
| _Prénom_ | Ordonnancement, supervision, CI/CD, IaC (boîte 6) | _Prénom_          |

Tout le monde relit les pull requests des autres : aucune fusion sur `main` sans relecture et sans CI verte.

## 8. Prochaines étapes

- **TD 2, le socle :** dépôt structuré, Dockerfile non root, `docker-compose.yml` (Airflow, PostgreSQL), première CI GitHub Actions avec publication sur ghcr.io.
- **TD 3, la collecte :** DAG de collecte planifié qui lit `sources.csv` et écrit le brut dans `data/raw/`.
