FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libffi-dev \
        libgdk-pixbuf-2.0-0 \
        libjpeg62-turbo \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpq-dev \
        libxml2 \
        libxslt1.1 \
        shared-mime-info \
        zlib1g \
        fonts-dejavu \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --system --create-home --home-dir /home/app --shell /usr/sbin/nologin app

COPY requirements.txt .

RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

COPY --chown=app:app . .

RUN mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app/staticfiles /app/media

USER app

EXPOSE 8000