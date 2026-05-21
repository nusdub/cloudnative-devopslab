FROM python:3.11-slim AS runtime

ARG APP_VERSION=0.1.0
ARG GIT_SHA=local
ARG IMAGE_DIGEST=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=prod \
    APP_VERSION=${APP_VERSION} \
    GIT_SHA=${GIT_SHA} \
    IMAGE_DIGEST=${IMAGE_DIGEST}

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home /app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
