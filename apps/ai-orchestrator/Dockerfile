FROM python:3.11-slim

WORKDIR /srv

COPY packages/py-shared /srv/packages/py-shared
COPY apps/ai-orchestrator/pyproject.toml /srv/apps/ai-orchestrator/pyproject.toml
COPY apps/ai-orchestrator/app /srv/apps/ai-orchestrator/app

RUN pip install --no-cache-dir -e /srv/packages/py-shared \
    && pip install --no-cache-dir -e /srv/apps/ai-orchestrator

WORKDIR /srv/apps/ai-orchestrator

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
