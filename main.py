import os, requests, feedparser

# ---- แหล่งข่าว: หุ้น + เศรษฐกิจ + สถานการณ์โลก ----
RSS_STOCK = [
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",   # MarketWatch
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",        # CNBC top news
    "https://finance.yahoo.com/news/rssindex",                      # Yahoo Finance
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",                # WSJ Markets
]
RSS_ECON = [
    "https://www.cnbc.com/id/20910258/device/rss/rss.html",         # CNBC Economy
    "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",    # WSJ / Dow Jones World
]
RSS_WORLD = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",                  # BBC World
    "https://www.aljazeera.com/xml/rss/all.xml",                    # Al Jazeera
    "http://rss.cnn.com/rss/edition_world.rss",                     # CNN World
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

stock_items = fetch(RSS_STOCK, n=8)
econ_items = fetch(RSS_ECON, n=6)
world_items = fetch(RSS_WORLD, n=6)

if not (stock_items or econ_items or world_items):
    raise SystemExit("ดึงข่าวไม่ได้เลยสักอัน")

prompt = f"""คุณเป็นนักวิเคราะห์การเงินและข่าวต่างประเทศ สรุปข่าวต่อไปนี้เป็นภาษาไทย แบ่งเป็น 3 หัวข้อ: หุ้น, เศรษฐกิจ, สถานการณ์โลก

**หัวข้อหุ้น** ให้ลงรายละเอียดแต่ละข่าว:
- ชื่อหุ้น/ดัชนีที่เกี่ยวข้อง (S&P 500, Nasdaq, Dow, ชื่อบริษัท)
- ตัวเลขสำคัญ เช่น % การเปลี่ยนแปลง ราคา ถ้ามีในข่าว
- สาเหตุ/ปัจจัย และผลกระทบต่อนักลงทุน

**หัวข้อเศรษฐกิจ** เน้นตัวเลข/นโยบายสำคัญ เช่น เงินเฟ้อ ดอกเบี้ย GDP การจ้างงาน พร้อมผลต่อตลาด

**หัวข้อสถานการณ์โลก** สรุปเหตุการณ์สำคัญที่อาจกระทบเศรษฐกิจ/ตลาด

ปิดท้ายด้วยหัวข้อ "สรุปภาพรวมและผลต่อการลงทุน" 2-3 บรรทัด

=== ข่าวหุ้น ===
{chr(10).join(stock_items)}

=== ข่าวเศรษฐกิจ ===
{chr(10).join(econ_items)}

=== ข่าวสถานการณ์โลก ===
{chr(10).join(world_items)}
"""

# ---- Groq API ----
api = os.environ["GROQ_API_KEY"]
endpoint = "https://api.groq.com/openai/v1/chat/completions"
headers = {"Authorization": f"Bearer {api}", "Content-Type": "application/json"}

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
