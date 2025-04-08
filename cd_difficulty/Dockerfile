FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# APIコードをコピー（← apiディレクトリが見つからない原因を防ぐ）
COPY ./api ./api

# 起動コマンド
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
