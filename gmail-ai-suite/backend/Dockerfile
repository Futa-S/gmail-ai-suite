# ---- ベースイメージ（Python 3.13 slim）----
FROM python:3.13-slim

# ---- 必要なシステムパッケージ（任意）----
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

# ---- 作業ディレクトリを /app に ----
WORKDIR /app

# ---- Poetry で依存を入れる ----
# 先に pyproject.toml, poetry.lock だけコピーしてキャッシュを効かせる
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

# ---- アプリのソースをコピー ----
COPY . .
# client_secret.json を明示的にコピーして一番上書きさせる（Optional、安全策）
COPY client_secret.json /app/client_secret.json

COPY db_credentials.json /app/db_credentials.json


# ---- ポート 8000 で FastAPI を起動 ----
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
