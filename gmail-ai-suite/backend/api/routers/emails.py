# -*- coding: utf-8 -*-
"""
直近 N 日 ＋ 迷惑メール／ゴミ箱除外で Gmail を取得するルータ
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List
from googleapiclient.errors import HttpError

from ..services.gmail import list_messages          # ← DB→Credentials→Gmail API を隠蔽したラッパ
from ..services.dto import build_email_dto, EmailDTO

router = APIRouter(prefix="/emails", tags=["Emails"])


@router.get(
    "/", summary="期間指定メール取得", response_model=List[EmailDTO]
)
def get_emails(
    days: int = Query(3, ge=1, le=30, description="直近 N 日 (1–30)"),
    max_results: int = Query(10, ge=1, le=50),
):
    """
    ・`newer_than:{days}d` で期間を絞る  
    ・`-in:spam -in:trash` で迷惑メール／ゴミ箱を除外
    """
    query = f"newer_than:{days}d -in:spam -in:trash"
    try:
        msgs = list_messages(query=query, max_results=max_results)
    except HttpError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Gmail API の message リソースを DTO に変換して返す
    return [build_email_dto(m) for m in msgs]
