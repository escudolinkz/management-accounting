# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1     POETRY_VIRTUALENVS_CREATE=false     PORT=8000

# System deps for pdf/tabula and build
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     curl     tini     openjdk-21-jre-headless     libjpeg62-turbo     libpng16-16     tzdata &&     rm -rf /var/lib/apt/lists/*

# Non-root user with uid:gid 1000
RUN id -u 1000 >/dev/null 2>&1 || useradd -m -u 1000 appuser

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# App code
COPY . /app

# Create runtime dirs
RUN mkdir -p /srv/finance/uploads /var/log/finance &&     chown -R 1000:1000 /srv/finance /var/log/finance

USER 1000:1000
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
