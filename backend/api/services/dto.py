# -*- coding: utf-8 -*-
"""
Gmail message(dict) → EmailDTO 変換
+ GPT-4o によるカテゴリ分類＆優先度スコア付け
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# GPT 分類器
from ..services.classifier import classify


# ─────────────────────────────────────────
# DTO 定義
# ─────────────────────────────────────────
class AttachmentInfo(BaseModel):
    filename: str
    mime_type: str


class EmailDTO(BaseModel):
    id: str
    thread_id: str
    subject: str
    sender: str
    snippet: str
    date: str
    has_attachment: bool
    attachment_info: List[AttachmentInfo] = []

    # ↓ ここが今回追加・使用するフィールド
    category_pred: Optional[str] = None
    priority_score: Optional[int] = None


# ─────────────────────────────────────────
# 変換関数
# ─────────────────────────────────────────
def build_email_dto(message: Dict[str, Any]) -> EmailDTO:
    """
    Gmail API の message（metadata 付き）→ EmailDTO へ変換。
    変換後に GPT でカテゴリ／優先度を付与する。
    """
    headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}
    subject = headers.get("Subject", "(No Subject)")
    sender = headers.get("From", "")
    snippet = message.get("snippet", "")
    date = headers.get("Date", "")

    # GPT で分類 & スコアリング
    category, score = classify(subject, snippet)

    return EmailDTO(
        id=message["id"],
        thread_id=message.get("threadId", ""),
        subject=subject,
        sender=sender,
        snippet=snippet,
        date=date,
        has_attachment=False,
        attachment_info=[],
        category_pred=category,
        priority_score=score,
    )
