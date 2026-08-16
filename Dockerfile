FROM python:3.11-slim AS builder

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN python -m venv "$VIRTUAL_ENV"

WORKDIR /build

# Keep compilers out of the runtime image while allowing any native Python
# dependencies to build when a wheel is unavailable.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system pubmediq \
    && useradd --system --gid pubmediq --create-home pubmediq

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=pubmediq:pubmediq app ./app
COPY --chown=pubmediq:pubmediq alembic.ini start.sh ./

RUN chmod 0555 /app/start.sh

USER pubmediq

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["/app/start.sh"]
