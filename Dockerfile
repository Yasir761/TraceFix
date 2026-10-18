FROM falkordb/falkordb-server:latest

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY tracefix ./tracefix
COPY start.sh ./start.sh

RUN sed -i 's/\r$//' /app/start.sh

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    FALKORDB_HOST=127.0.0.1 \
    FALKORDB_PORT=6379 \
    FALKORDB_GRAPH=tracefix

EXPOSE 10000

ENTRYPOINT ["/bin/sh", "/app/start.sh"]
