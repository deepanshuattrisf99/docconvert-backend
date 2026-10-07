FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libreoffice-writer libreoffice-core fonts-dejavu fonts-liberation && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser app.py .
USER appuser

ENV PYTHONUNBUFFERED=1
CMD gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 2 --timeout 120 --limit-request-line 4094 --limit-request-field_size 8190 app:app
