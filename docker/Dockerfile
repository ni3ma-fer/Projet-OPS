FROM python:3.11-slim

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installation des librairies data & NLP
RUN pip install --no-cache-dir \
    feedparser \
    psycopg2-binary \
    pandas \
    bertopic \
    sentence-transformers

# Pré-téléchargement du modèle d'embeddings léger (CPU, sans LLM externe)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

COPY src/ /app/src/
COPY sources.csv /app/sources.csv

CMD ["python", "src/gazette/healthcheck.py"]