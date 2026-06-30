FROM apache/superset:6.1.0

USER root

RUN /app/.venv/bin/python -m ensurepip
RUN /app/.venv/bin/python -m pip install psycopg2-binary

COPY superset_config.py /app/pythonpath/

ENV SUPERSET_CONFIG_PATH=/app/pythonpath/superset_config.py

USER superset