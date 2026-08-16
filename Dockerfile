# ============================================================
# PubMedIQ Backend — Dockerfile (Multi-stage)
# ============================================================

# --- Stage 1: Builder ---
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim as runtime

WORKDIR /app

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r pubmediq \
    && useradd -r -g pubmediq pubmediq

# Copy installed packages from builder
COPY --from=builder --chown=pubmediq:pubmediq /root/.local /home/pubmediq/.local

# Copy application code
COPY --chown=pubmediq:pubmediq app/ ./app/
COPY --chown=pubmediq:pubmediq alembic.ini .
COPY --chown=pubmediq:pubmediq pyproject.toml .

# Set ownership of /app directory
RUN chown -R pubmediq:pubmediq /app

# Switch to non-root user
USER pubmediq

# Add local packages to PATH
ENV PATH=/home/pubmediq/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]