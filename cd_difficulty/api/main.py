from fastapi import FastAPI, Depends
from pydantic import BaseModel
import os
from openai import OpenAI
from sqlalchemy.orm import Session

from api import models, database

# OpenAI クライアント
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# DB初期化
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# リクエスト用モデル
class SentenceRequest(BaseModel):
    sentence: str

# DBセッション取得用依存関数
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/predict")
async def predict_difficulty(req: SentenceRequest, db: Session = Depends(get_db)):
    prompt = (
        f"以下の英文の難易度をTOEICスコアで推定してください。\n"
        f"例：TOEIC 600相当など。\n\n英文: {req.sentence}"
    )

    # OpenAI API 呼び出し
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    difficulty = response.choices[0].message.content.strip()

    # DBに保存
    prediction = models.Prediction(sentence=req.sentence, difficulty=difficulty)
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return {"id": prediction.id, "difficulty": prediction.difficulty}
from typing import List
from fastapi.responses import JSONResponse

@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    predictions = db.query(models.Prediction).all()
    return JSONResponse([
        {"id": p.id, "sentence": p.sentence, "difficulty": p.difficulty}
        for p in predictions
    ])
