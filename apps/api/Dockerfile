FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /srv

COPY packages/py-shared /srv/packages/py-shared
COPY apps/api/pyproject.toml /srv/apps/api/pyproject.toml
COPY apps/api/app /srv/apps/api/app
COPY apps/api/alembic.ini /srv/apps/api/alembic.ini

RUN pip install --no-cache-dir -e /srv/packages/py-shared \
    && pip install --no-cache-dir -e /srv/apps/api

WORKDIR /srv/apps/api

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
