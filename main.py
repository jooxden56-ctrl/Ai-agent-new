import os, requests, feedparser

# ---- แหล่งข่าว ----
# หุ้นสหรัฐเน้นเยอะ + AI + คริปโต
RSS_STOCK_US = [
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",   # MarketWatch top stories
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",        # CNBC top news
    "https://finance.yahoo.com/news/rssindex",                      # Yahoo Finance
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",                # WSJ Markets
]
RSS_AI = [
    "https://feeds.feedburner.com/oreilly/radar",
]
RSS_CRYPTO = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]

def fetch(urls, n=6):
    out = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:n]:
                out.append(f"- {e.title}\n  {getattr(e,'link','')}")
        except Exception as ex:
            print("RSS error:", url, ex)
    return out

stock_items = fetch(RSS_STOCK_US, n=8)   # หุ้นดึงเยอะกว่า
ai_items = fetch(RSS_AI, n=5)
crypto_items = fetch(RSS_CRYPTO, n=5)

if not (stock_items or ai_items or crypto_items):
    raise SystemExit("ดึงข่าวไม่ได้เลยสักอัน")

prompt = f"""คุณเป็นนักวิเคราะห์การเงิน สรุปข่าวต่อไปนี้เป็นภาษาไทย แบ่งเป็น 3 หัวข้อ: AI, หุ้นสหรัฐ, คริปโต

**เน้นหัวข้อหุ้นสหรัฐเป็นพิเศษ** โดยแต่ละข่าวหุ้นให้ลงรายละเอียด:
- ชื่อหุ้น/ดัชนีที่เกี่ยวข้อง (เช่น S&P 500, Nasdaq, Dow, ชื่อบริษัท)
- ตัวเลขสำคัญ เช่น % การเปลี่ยนแปลง ราคา ถ้ามีในข่าว
- สาเหตุ/ปัจจัยที่ทำให้เกิดข่าวนั้น
- ผลกระทบต่อนักลงทุนและแนวโน้มระยะสั้น

ส่วน AI และคริปโต สรุปสั้นกระชับพอ

ปิดท้ายด้วยหัวข้อ "สรุปภาพรวมการลงทุนวันนี้" 2-3 บรรทัด

=== ข่าวหุ้นสหรัฐ ===
{chr(10).join(stock_items)}

=== ข่าว AI ===
{chr(10).join(ai_items)}

=== ข่าวคริปโต ===
{chr(10).join(crypto_items)}
"""

# ---- Groq API (OpenAI-compatible) ----
api = os.environ["GROQ_API_KEY"]
endpoint = "https://api.groq.com/openai/v1/chat/completions"
headers = {"Authorization": f"Bearer {api}", "Content-Type": "application/json"}

# ใช้ตัวใหญ่ก่อนเพื่อรายละเอียดดีกว่า ถ้าไม่ได้ค่อย fallback ตัวเล็ก
MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

text = None
for model in MODELS:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 3000,
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=90)
    data = r.json()
    if "choices" in data:
        text = data["choices"][0]["message"]["content"]
        print(f"ใช้ model: {model}")
        break
    else:
        print(f"model {model} ใช้ไม่ได้:", data.get("error", data))

if text is None:
    raise SystemExit("ลองทุก model แล้วใช้ไม่ได้เลย ดู error ด้านบน")

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
