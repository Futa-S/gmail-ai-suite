import os
import openai
from fastapi import FastAPI
from pydantic import BaseModel

openai.api_key = os.getenv("OPENAI_API_KEY")

# 👇 確認用ログ
if openai.api_key:
    print("✅ OpenAI API key loaded successfully.")
else:
    print("❌ OpenAI API key NOT loaded.")

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
