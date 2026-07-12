import os, requests, feedparser, json, hashlib
from datetime import datetime, timezone, timedelta

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

SEEN_FILE = "sent_news.json"

def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen)[-500:], f, ensure_ascii=False)

def title_id(title):
    return hashlib.md5(title.strip().lower().encode()).hexdigest()

seen = load_seen()

def fetch(urls, n=6):
    out = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:n]:
                tid = title_id(e.title)
                if tid in seen:
                    continue
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

if total_new == 0:
    save_seen(seen)
    print("ไม่มีข่าวใหม่ ไม่ส่ง")
    raise SystemExit(0)

now_th = datetime.now(timezone(timedelta(hours=7)))
date_str = now_th.strftime("%d/%m/%Y %H:%M")
now_et = now_th - timedelta(hours=11)  # DST (มี.ค.-พ.ย.) | หน้าหนาวเปลี่ยนเป็น 12
et_time = now_et.strftime("%H:%M")
et_hour, et_min = now_et.hour, now_et.minute
mins = et_hour * 60 + et_min
market_open, market_close = 9*60+30, 16*60

if mins < market_open:
    mode_header = "☀️ ก่อนตลาดสหรัฐเปิด (Pre-market)"
    mode_instruction = "โหมดก่อนตลาดเปิด: เน้นสิ่งที่ต้องจับตาก่อนตลาดเปิด, ทิศทาง futures, ตัวเลขเศรษฐกิจที่จะประกาศ"
elif mins < market_close:
    mode_header = "🔔 ระหว่างตลาดสหรัฐเปิด (Live)"
    mode_instruction = "โหมดระหว่างเทรด: เน้นความเคลื่อนไหวตลาดตอนนี้, หุ้นที่วิ่งแรง, ปัจจัยขับเคลื่อน"
else:
    mode_header = "🌙 ตลาดสหรัฐปิดแล้ว (Closing)"
    mode_instruction = "โหมดปิดตลาด: เน้นสรุปตลาดปิดยังไง, หุ้นเด่นวันนี้, after-hours"

prompt = f"""คุณเป็นนักวิเคราะห์การเงินระดับสถาบัน (sell-side analyst) สรุปและวิเคราะห์ข่าวต่อไปนี้เป็นภาษาไทยแบบเข้มข้น เจาะลึก มืออาชีพ

**กฎการเขียน (สำคัญ):**
- ห้ามใช้เครื่องหมาย Markdown เช่น ###, **, __ เด็ดขาด ใช้อีโมจีและข้อความล้วนเท่านั้น
- **ดึงตัวเลขทุกตัวที่ปรากฏในข่าวมาใส่** (% เปลี่ยนแปลง, ราคา, จุดดัชนี, มูลค่าดีล, EPS, รายได้) อย่าละเลยตัวเลข
- ทุกบริษัท/หุ้นใส่ ticker ในวงเล็บ เช่น Nvidia (NVDA), Apple (AAPL)
- ทุกดัชนีใส่ชื่อย่อ เช่น S&P 500 (SPX), Nasdaq (IXIC), Dow (DJI)
- ใส่ระดับความสำคัญนำหน้าข่าวเด่น: 🔴 กระทบแรง/ด่วน, 🟡 ปานกลาง, 🟢 ทั่วไป

**โครงสร้างข้อความ:**

บรรทัดแรก: "{mode_header}"
บรรทัดสอง: "🇹🇭 {date_str} น. | 🇺🇸 {et_time} ET"
{mode_instruction}

📈 หุ้น
วิเคราะห์แต่ละข่าวเข้มๆ: บริษัท+ticker, ตัวเลข %/ราคาที่มี, สาเหตุเชิงลึก, ผลต่อราคาหุ้นและ sector, มุมมองระยะสั้น

💰 เศรษฐกิจ
เจาะตัวเลขเศรษฐกิจ (เงินเฟ้อ ดอกเบี้ย GDP จ้างงาน) พร้อมนัยต่อนโยบาย Fed และตลาด

🌍 สถานการณ์โลก
เหตุการณ์ที่กระทบตลาด/เศรษฐกิจ พร้อมประเมินผลกระทบ

🔥 Sector วันนี้
sector ไหนร้อน (เงินไหลเข้า) / เย็น (เงินไหลออก) พร้อมเหตุผลสั้นๆ

👀 ปัจจัยต้องจับตา
ตัวเลขเศรษฐกิจ/งบบริษัท/เหตุการณ์ที่จะเกิดข้างหน้าและอาจกระทบตลาด

🎯 มุมมองการลงทุน
- โทนตลาด: Risk-on (กล้าเสี่ยง) หรือ Risk-off (หลบความเสี่ยง) พร้อมเหตุผล
- หุ้น/sector น่าจับตา (พร้อม ticker)
- ความเสี่ยงหลักที่ต้องระวัง
- สรุปภาพรวม 1-2 ประโยค

หมายเหตุ: หัวข้อไหนไม่มีข่าวใหม่ให้ข้ามไป แต่ 🎯 มุมมองการลงทุน ต้องมีเสมอ

=== ข่าวหุ้น ===
{chr(10).join(stock_items) if stock_items else "(ไม่มีข่าวใหม่)"}

=== ข่าวเศรษฐกิจ ===
{chr(10).join(econ_items) if econ_items else "(ไม่มีข่าวใหม่)"}

=== ข่าวสถานการณ์โลก ===
{chr(10).join(world_items) if world_items else "(ไม่มีข่าวใหม่)"}
"""

api = os.environ["GROQ_API_KEY"]
endpoint = "https://api.groq.com/openai/v1/chat/completions"
headers = {"Authorization": f"Bearer {api}", "Content-Type": "application/json"}

MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

text = None
for model in MODELS:
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.55, "max_tokens": 4000}
    r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    data = r.json()
    if "choices" in data:
        text = data["choices"][0]["message"]["content"]
        print(f"ใช้ model: {model} | {mode_header} | {et_time} ET")
        break
    else:
        print(f"model {model} ใช้ไม่ได้:", data.get("error", data))

if text is None:
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

save_seen(seen)
print("Done")
