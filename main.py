import os, requests, feedparser, json, hashlib
from datetime import datetime, timezone, timedelta

# ---- แหล่งข่าว: หุ้น + เศรษฐกิจ + สถานการณ์โลก ----
RSS_STOCK = [
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://finance.yahoo.com/news/rssindex",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
]
RSS_ECON = [
    "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
]
RSS_WORLD = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "http://rss.cnn.com/rss/edition_world.rss",
]

# ---- ระบบกันข่าวซ้ำ ----
SEEN_FILE = "sent_news.json"

def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_seen(seen):
    # เก็บแค่ 500 หัวข้อล่าสุด กันไฟล์โตเกินไป
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen)[-500:], f, ensure_ascii=False)

def title_id(title):
    # สร้าง id จากหัวข้อข่าว (กันซ้ำแม้ลิงก์ต่างกัน)
    return hashlib.md5(title.strip().lower().encode()).hexdigest()

seen = load_seen()

def fetch(urls, n=6):
    """ดึงข่าว เฉพาะที่ยังไม่เคยส่ง"""
    out = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:n]:
                tid = title_id(e.title)
                if tid in seen:
                    continue  # ข่าวเก่า ข้าม
                seen.add(tid)
                out.append(f"- {e.title}\n  {getattr(e,'link','')}")
        except Exception as ex:
            print("RSS error:", url, ex)
    return out

stock_items = fetch(RSS_STOCK, n=8)
econ_items = fetch(RSS_ECON, n=6)
world_items = fetch(RSS_WORLD, n=6)

total_new = len(stock_items) + len(econ_items) + len(world_items)
print(f"ข่าวใหม่ที่เจอ: {total_new}")

# ไม่มีข่าวใหม่เลย → ไม่ส่ง (กันสแปมข่าวเดิม)
if total_new == 0:
    save_seen(seen)
    print("ไม่มีข่าวใหม่ ไม่ส่ง")
    raise SystemExit(0)

now_th = datetime.now(timezone(timedelta(hours=7)))
date_str = now_th.strftime("%d/%m/%Y %H:%M")

prompt = f"""คุณเป็นนักวิเคราะห์การเงินและข่าวต่างประเทศมืออาชีพ สรุปข่าวต่อไปนี้เป็นภาษาไทย

**รูปแบบที่ต้องการ:**
- ขึ้นต้นด้วยหัวข้อใหญ่ "📊 สรุปข่าวการเงิน {date_str} น."
- แบ่งเป็น 3 หัวข้อหลัก ใช้อีโมจีนำ: "📈 หุ้น", "💰 เศรษฐกิจ", "🌍 สถานการณ์โลก"
- **ทุกครั้งที่พูดถึงบริษัท/หุ้น ต้องใส่ตัวย่อ (ticker) ในวงเล็บ** เช่น Nvidia (NVDA), Apple (AAPL), Tesla (TSLA)
- **ทุกครั้งที่พูดถึงดัชนี ใส่ชื่อย่อ** เช่น S&P 500 (SPX), Nasdaq (IXIC), Dow Jones (DJI)
- ใช้อีโมจีประกอบ: 📈 ขึ้น, 📉 ลง, ⚠️ ความเสี่ยง, 🔥 ข่าวเด่น, 💵 เงิน/ดอกเบี้ย

**หัวข้อ 📈 หุ้น** ลงรายละเอียด: ชื่อบริษัท+ticker, ดัชนีที่เกี่ยวข้อง, ตัวเลข %/ราคา, สาเหตุ, ผลกระทบต่อนักลงทุน
**หัวข้อ 💰 เศรษฐกิจ** เน้นตัวเลข/นโยบาย เงินเฟ้อ ดอกเบี้ย GDP การจ้างงาน
**หัวข้อ 🌍 สถานการณ์โลก** เหตุการณ์สำคัญที่กระทบเศรษฐกิจ/ตลาด

**ปิดท้ายด้วย "🎯 มุมมองการลงทุน"** 3-4 บรรทัด: หุ้น/sector น่าจับตา (พร้อม ticker), ความเสี่ยง, ภาพรวมตลาด

หมายเหตุ: หากบางหัวข้อไม่มีข่าวใหม่ ให้ข้ามหัวข้อนั้นไป

=== ข่าวหุ้น ===
{chr(10).join(stock_items) if stock_items else "(ไม่มีข่าวใหม่)"}

=== ข่าวเศรษฐกิจ ===
{chr(10).join(econ_items) if econ_items else "(ไม่มีข่าวใหม่)"}

=== ข่าวสถานการณ์โลก ===
{chr(10).join(world_items) if world_items else "(ไม่มีข่าวใหม่)"}
"""

# ---- Groq API ----
api = os.environ["GROQ_API_KEY"]
endpoint = "https://api.groq.com/openai/v1/chat/completions"
headers = {"Authorization": f"Bearer {api}", "Content-Type": "application/json"}

MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

text = None
for model in MODELS:
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.6, "max_tokens": 3500}
    r = requests.post(endpoint, headers=headers, json=payload, timeout=90)
    data = r.json()
    if "choices" in data:
        text = data["choices"][0]["message"]["content"]
        print(f"ใช้ model: {model}")
        break
    else:
        print(f"model {model} ใช้ไม่ได้:", data.get("error", data))

if text is None:
    # ส่งไม่สำเร็จ ไม่บันทึก seen เพื่อให้ลองใหม่รอบหน้า
    raise SystemExit("ลองทุก model แล้วใช้ไม่ได้เลย")

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

# บันทึกหัวข้อที่ส่งแล้ว (หลังส่งสำเร็จ)
save_seen(seen)
print("Done")
