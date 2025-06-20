# -*- coding: utf-8 -*-
"""
Gmail API ラッパ
- DB に保存した OAuth トークンを読み出して Credentials を生成
- BatchHttpRequest で高速にメール詳細を取得
"""

from __future__ import annotations

import os
import json
import datetime as _dt
import threading
from typing import List, Dict, Any

import psycopg2
from cryptography.fernet import Fernet
from googleapiclient.discovery import build
from googleapiclient.http import BatchHttpRequest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
import logging
logger = logging.getLogger(__name__)
# ──────────────────────────────────────────
# 環境変数 & 暗号キー
# ──────────────────────────────────────────
ENC_KEY = os.getenv("ENCRYPTION_KEY")
if ENC_KEY is None:
    raise RuntimeError("ENCRYPTION_KEY env var is missing")
cipher_suite = Fernet(ENC_KEY.encode())

# DB 接続情報は json ファイルに置いてある想定
def _get_db_cfg() -> Dict[str, str]:
    with open("/app/db_credentials.json") as f:
        return json.load(f)

# ──────────────────────────────────────────
# Credentials 生成
# ──────────────────────────────────────────
def _load_credentials() -> Credentials:
    cfg = _get_db_cfg()
    with psycopg2.connect(**cfg) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT token, refresh_token FROM user_tokens ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("No OAuth tokens stored. Run /login first.")
        enc_token, enc_refresh = row

    access_token = cipher_suite.decrypt(bytes(enc_token)).decode()
    refresh_token = (
        cipher_suite.decrypt(bytes(enc_refresh)).decode() if enc_refresh else None
    )

    # client_id / client_secret は client_secret.json から読む
    with open("/app/client_secret.json") as f:
        secret = json.load(f)["web"]

    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=secret["client_id"],
        client_secret=secret["client_secret"],
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        expiry=_dt.datetime.utcnow() + _dt.timedelta(minutes=55),
    )

# ──────────────────────────────────────────
# Gmail Service シングルトン
# ──────────────────────────────────────────
_service_cache: Any | None = None


def get_gmail_service():
    global _service_cache
    if _service_cache is None:
        _service_cache = build("gmail", "v1", credentials=_load_credentials())
    return _service_cache


# ──────────────────────────────────────────
# Batch で詳細取得（高速化）
# ──────────────────────────────────────────
def fetch_messages_detail(ids: List[str]) -> List[Dict[str, Any]]:
    svc = get_gmail_service()
    results: List[Dict[str, Any]] = []
    lock = threading.Lock()

    def _cb(req_id, resp, exc):
        if exc is None:
            with lock:
                results.append(resp)
        else:
            logger.error(f"Batch error on {req_id}: {exc}")

    batch: BatchHttpRequest = svc.new_batch_http_request()
    for mid in ids:
        batch.add(
            svc.users()
            .messages()
            .get(
                userId="me",
                id=mid,
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
                fields="id,threadId,payload/headers,snippet",
            ),
            callback=_cb,
        )
    try:
        batch.execute()
    except RefreshError:
        # アクセス・リフレッシュ両方失効 → /login し直しを促す
        logger.error("OAuth tokens expired. Please re-authenticate via /login.")
        return []
    return results


# ──────────────────────────────────────────
# 外部公開: list_messages
# デフォルト 10 件だけ IDs を取り、一括で詳細に展開
# ──────────────────────────────────────────
def list_messages(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    svc = get_gmail_service()
    ids_resp = (
        svc.users()
        .messages()
        .list(
            userId="me",
            q=query,
            maxResults=max_results,
            includeSpamTrash=False,
            fields="messages/id",
        )
        .execute()
    )
    id_list = [m["id"] for m in ids_resp.get("messages", [])]
    if not id_list:
        return []
    return fetch_messages_detail(id_list)
