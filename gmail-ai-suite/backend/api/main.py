from __future__ import annotations

import os
import json
import datetime as _dt
import requests
import openai
from openai import OpenAI
import psycopg2
import logging
from typing import Any, Mapping, Dict

from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse, JSONResponse

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# ─────────────────────────────────────────────────────────────
# 環境変数・初期設定
# ─────────────────────────────────────────────────────────────
ENC_KEY = os.getenv("ENCRYPTION_KEY")
if ENC_KEY is None:
    raise RuntimeError("ENCRYPTION_KEY env var is missing")
cipher_suite = Fernet(ENC_KEY.encode())

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
SECRET_NAME = os.getenv("SECRET_NAME")
DB_SECRET_NAME = os.getenv("DB_SECRET_NAME")
KEY_SECRET_NAME = os.getenv("ENCRYPTION_KEY_SECRET_NAME")
REDIRECT_URI = os.getenv("REDIRECT_URI")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")

if not all([PROJECT_ID, SECRET_NAME, DB_SECRET_NAME, KEY_SECRET_NAME, REDIRECT_URI]):
    raise RuntimeError("Required env vars are missing. Check your .env file.")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ─────────────────────────────────────────────────────────────
# キャッシュ用グローバル変数
# ─────────────────────────────────────────────────────────────
_client_config: dict[str, Any] | None = None
_db_cfg: dict[str, str] | None = None

# ─────────────────────────────────────────────────────────────
# ヘルパー関数
# ─────────────────────────────────────────────────────────────
def get_client_config() -> dict[str, Any]:
    global _client_config
    if _client_config is None:
        with open("/app/client_secret.json") as f:
            _client_config = json.load(f)
    return _client_config


def get_db_cfg() -> dict[str, str]:
    global _db_cfg
    if _db_cfg is None:
        with open("/app/db_credentials.json") as f:
            _db_cfg = json.load(f)
    return _db_cfg


def db_conn():
    cfg = get_db_cfg()
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["database"],
        user=cfg["user"],
        password=cfg["password"],
    )
    try:
        yield conn
    finally:
        conn.close()


def build_flow() -> Flow:
    client_cfg = get_client_config()
    return Flow.from_client_config(
        client_cfg,
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        redirect_uri=REDIRECT_URI,
    )


def score_email_with_openai(subject: str, sender: str, snippet: str) -> Dict[str, Any]:
    prompt = f"""
あなたはメールを要約してカテゴリと重要度を判定するAIです。
以下の情報をもとに、「カテゴリ」と「優先度（1〜5）」を出力してください：

- 件名: {subject}
- 送信者: {sender}
- メールの概要: {snippet}

フォーマットは以下のようにしてください：
カテゴリ: <カテゴリ名>
優先度: <1〜5の数値>
    """.strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        lines = content.splitlines()
        category = next(
            (line.split(":", 1)[1].strip() for line in lines if "カテゴリ" in line),
            "未分類",
        )
        score_str = next(
            (line.split(":", 1)[1].strip() for line in lines if "優先度" in line), "3"
        )
        score = int(score_str) if score_str.isdigit() else 3
        return {"category": category, "priority_score": score}
    except Exception as e:
        logger.error(f"OpenAI API エラー: {e}")
        return {"category": "分類失敗", "priority_score": 3}


# ─────────────────────────────────────────────────────────────
# FastAPI アプリケーション
# ─────────────────────────────────────────────────────────────
app = FastAPI(title="Gmail OAuth Demo", version="0.1.0")

# ① 新しい /emails ルータを登録
from .routers.emails import router as emails_router

app.include_router(emails_router)

# ── OAuth 関連ルートはそのまま ────────────────────────────
@app.get("/login", summary="Start OAuth flow")
async def login():
    flow = build_flow()
    auth_url, _ = flow.authorization_url(
        prompt="consent", access_type="offline", include_granted_scopes="true"
    )
    return RedirectResponse(auth_url)


@app.get("/oauth2callback", summary="OAuth callback")
async def oauth2callback(request: Request, conn=Depends(db_conn)):
    flow = build_flow()
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    email = None
    if credentials.id_token:
        r = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": credentials.id_token},
            timeout=5,
        )
        if r.ok:
            email = r.json().get("email")
    if not email:
        r = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": credentials.token},
            timeout=5,
        )
        if r.ok:
            email = r.json().get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Failed to get user email")

    enc_access = cipher_suite.encrypt(credentials.token.encode())
    enc_refresh = (
        cipher_suite.encrypt((credentials.refresh_token or "").encode())
        if credentials.refresh_token
        else None
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_tokens (user_email, token, refresh_token, expiry)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_email) DO UPDATE SET
              token = EXCLUDED.token,
              refresh_token = EXCLUDED.refresh_token,
              expiry = EXCLUDED.expiry,
              created_at = CURRENT_TIMESTAMP
            """,
            (
                email,
                psycopg2.Binary(enc_access),
                psycopg2.Binary(enc_refresh) if enc_refresh else None,
                credentials.expiry,
            ),
        )
        conn.commit()

    # 認証後はフロントが使う /emails へリダイレクト
    return RedirectResponse(url="/emails", status_code=status.HTTP_302_FOUND)


# 旧 /emails ルートは削除済み（router 側が担当）


# ─────────────────────────────────────────────────────────────
# CORS 設定
# ─────────────────────────────────────────────────────────────
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
