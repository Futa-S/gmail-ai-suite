from __future__ import annotations
import os
import json
import datetime as _dt
from typing import Any, Mapping

import psycopg2
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse, JSONResponse

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.cloud import secretmanager

#   ... 既存 import の下に追記 ------------------------------
ENC_KEY = os.getenv("ENCRYPTION_KEY")
if not ENC_KEY:
    raise RuntimeError("ENCRYPTION_KEY env var is missing")
cipher_suite = Fernet(ENC_KEY.encode())   # ← これが f になります
# -----------------------------------------------------------

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
SECRET_NAME = os.getenv("SECRET_NAME")
DB_SECRET_NAME = os.getenv("DB_SECRET_NAME")
KEY_SECRET_NAME = os.getenv("ENCRYPTION_KEY_SECRET_NAME")
REDIRECT_URI = os.getenv("REDIRECT_URI")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")

if not all([PROJECT_ID, SECRET_NAME, DB_SECRET_NAME, KEY_SECRET_NAME, REDIRECT_URI]):
    raise RuntimeError("Required env vars are missing. Check your .env file.")

#コメントアウト
#_sm_client = secretmanager.SecretManagerServiceClient()

#def _access_secret(name: str) -> bytes:
#    secret_path = f"projects/{PROJECT_ID}/secrets/{name}/versions/latest"
#    response = _sm_client.access_secret_version(name=secret_path)
#    return response.payload.data

# Cache secrets after first fetch
_client_config: dict[str, Any] | None = None
_db_cfg: dict[str, str] | None = None
_fernet: Fernet | None = None

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


#


# ---------------------------------------------------------------------------
# Database helpers (simple — one connection per request)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# FastAPI app + endpoints
# ---------------------------------------------------------------------------

app = FastAPI(title="Gmail OAuth Demo", version="0.1.0")


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

def build_flow() -> Flow:
    client_cfg = get_client_config()
    return Flow.from_client_config(
        client_cfg,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )


@app.get("/login", summary="Start OAuth flow")
async def login():
    flow = build_flow()
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes="true")
    return RedirectResponse(auth_url)


import requests

@app.get("/oauth2callback", summary="OAuth callback")
async def oauth2callback(request: Request, conn=Depends(db_conn)):
    flow = build_flow()
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

        # --- ここでメールアドレスを安全に取得 -------------------------
    email = None

    # ❶ id_token がある場合は tokeninfo でデコード
    if credentials.id_token:
        r = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": credentials.id_token},   # ★←ここを id_token に
            timeout=5,
        )
        if r.ok:
            email = r.json().get("email")

    # ❷ まだ email が取れなければ access_token で tokeninfo
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
    # ---------------------------------------------------------------
# ---------------------------------------------------------------

    # encrypt tokens
    enc_access = cipher_suite.encrypt(credentials.token.encode())
    enc_refresh = cipher_suite.encrypt(
        (credentials.refresh_token or "").encode()
    ) if credentials.refresh_token else None
    # upsert into DB
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

    return RedirectResponse(url="/emails", status_code=status.HTTP_302_FOUND)


@app.get("/emails", summary="Get latest 10 emails")
async def get_emails(conn=Depends(db_conn)):
    # fetch encrypted token
    with conn.cursor() as cur:
        cur.execute(
            "SELECT token, refresh_token FROM user_tokens ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="No stored tokens. Please /login first.")
    enc_token, enc_refresh = row
    access_token = cipher_suite.decrypt(bytes(enc_token)).decode()
    refresh_token = (
        cipher_suite.decrypt(bytes(enc_refresh)).decode() if enc_refresh else None
    )
    creds_dict: Mapping[str, Any] = {
        "token": access_token,
        "refresh_token": refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": get_client_config()["web"]["client_id"],
        "client_secret": get_client_config()["web"]["client_secret"],
        "scopes": SCOPES,
        "expiry": (_dt.datetime.utcnow() + _dt.timedelta(minutes=55)).isoformat() + "Z",
    }
    creds = Credentials.from_authorized_user_info(info=creds_dict, scopes=SCOPES)
    gmail = build("gmail", "v1", credentials=creds)
    resp = gmail.users().messages().list(
        userId="me", maxResults=10
    ).execute()

    result = []
    for m in resp.get("messages", []):
        full = gmail.users().messages().get(
            userId="me",
            id=m["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()
        hdrs = {h["name"]: h["value"] for h in full["payload"]["headers"]}
        result.append({
            "id":       m["id"],
            "from":     hdrs.get("From", ""),
            "subject":  hdrs.get("Subject", ""),
            "date":     hdrs.get("Date", ""),
            "snippet":  full.get("snippet", "")
        })
    return {"emails": result}
