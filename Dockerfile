FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# Production wheels only: this avoids a compiler layer and keeps the final
# image free of test, lint, and type-checking dependencies.
COPY requirements-prod.txt .
RUN pip install --no-compile --only-binary=:all: -r requirements-prod.txt \
    && groupadd --system pubmediq \
    && useradd --system --gid pubmediq --create-home pubmediq

COPY --chown=pubmediq:pubmediq app ./app
COPY --chown=pubmediq:pubmediq alembic.ini ./

USER pubmediq

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://localhost:8000/api/v1/health', timeout=3)"

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
