FROM apache/airflow:3.4.0-python3.12

COPY --chown=airflow:0 pyproject.toml README.md /opt/gazette/
COPY --chown=airflow:0 src /opt/gazette/src
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" /opt/gazette