from fastapi import FastAPI
from pydantic import BaseModel
import openai
import os

# 環境変数から取得（入力待ちなし）
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": req.message}]
    )
    return {"reply": response.choices[0].message["content"]}
