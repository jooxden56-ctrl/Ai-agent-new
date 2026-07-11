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

api = os.environ["GEMINI_API_KEY"]
endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api}"
payload = {"contents": [{"parts": [{"text": prompt}]}]}

r = requests.post(endpoint, json=payload, timeout=60)
data = r.json()

# เช็ค error ก่อนดึง candidates
if "candidates" not in data:
    print("Gemini API response:", data)
    raise SystemExit("Gemini ไม่ได้ส่ง candidates กลับมา ดู error ด้านบน")

text = data["candidates"][0]["content"]["parts"][0]["text"]

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
