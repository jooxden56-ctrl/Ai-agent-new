import os, requests, feedparser

RSS = [
    "https://feeds.feedburner.com/oreilly/radar",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://finance.yahoo.com/news/rssindex"
]

items = []
for url in RSS:
    try:
        feed = feedparser.parse(url)
        for e in feed.entries[:5]:
            items.append(f"- {e.title}\n  {getattr(e,'link','')}")
    except Exception as ex:
        print("RSS error:", url, ex)

if not items:
    raise SystemExit("ดึงข่าวไม่ได้เลยสักอัน")

prompt = "สรุปข่าวต่อไปนี้เป็นภาษาไทย แบ่งหัวข้อ AI, หุ้น, คริปโต พร้อมผลกระทบต่อการลงทุน\n\n" + "\n".join(items[:15])

# ---- Groq API (OpenAI-compatible) ----
api = os.environ["GROQ_API_KEY"]
endpoint = "https://api.groq.com/openai/v1/chat/completions"
headers = {"Authorization": f"Bearer {api}", "Content-Type": "application/json"}

# ใช้เฉพาะ model ที่อยู่ใน Allowed Models ของ project
MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "groq/compound",
]

text = None
for model in MODELS:
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    r = requests.post(endpoint, headers=headers, json=payload, timeout=60)
    data = r.json()
    if "choices" in data:
        text = data["choices"][0]["message"]["content"]
        print(f"ใช้ model: {model}")
        break
    else:
        print(f"model {model} ใช้ไม่ได้:", data.get("error", data))

if text is None:
    raise SystemExit("ลองทุก model แล้วใช้ไม่ได้เลย ไปที่ console.groq.com/settings/project/limits แล้วกด Clear ที่ Allowed Models")

# Telegram จำกัด 4096 ตัวอักษร แบ่งส่งเป็นก้อน
def send_telegram(msg):
    resp = requests.post(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
        json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": msg}
    )
    if not resp.ok:
        print("Telegram error:", resp.text)
    return resp.ok

for i in range(0, len(text), 4000):
    send_telegram(text[i:i+4000])

print("Done")
