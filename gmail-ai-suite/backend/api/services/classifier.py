# api/services/classifier.py
from openai import OpenAI
import json

client = OpenAI()

CATEGORIES = [
    "仕事/インターン", "授業/研究", "イベント/セミナー", "請求/支払い", "銀行/証券",
    "税金/保険", "航空券/旅行", "交通/モビリティ", "宿泊/ホテル", "E-コマース",
    "サブスク/更新", "SNS/通知", "ニュースレター", "広告/プロモーション",
    "趣味/コミュニティ", "健康/医療", "金融サービス", "不動産/住宅",
    "契約/署名", "法務/官公庁", "教材/学習", "ボランティア/寄付",
    "写真/動画共有", "IoT/スマートホーム", "その他"
]

SYSTEM = (
    "あなたはメールを 25 種類のカテゴリに分類し、重要度(1〜5)を判定するAIです。\n"
    f"カテゴリは次の一覧から 1 つ選び、日本語で出力してください:\n{', '.join(CATEGORIES)}\n"
    "JSON 形式で {\"category\": <カテゴリ>, \"priority\": <数値>} を必ず返してください。"
)

def classify(subject: str, snippet: str):
    prompt = f"件名: {subject}\n本文概要: {snippet[:1500]}"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",         # コスト抑制
        messages=[{"role":"system","content":SYSTEM},
                  {"role":"user","content":prompt}],
        response_format={"type": "json_object"},
        max_tokens=20,
        temperature=0.3,
    )
    js = json.loads(resp.choices[0].message.content)
    return js["category"], int(js["priority"])
