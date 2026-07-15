import os, requests, feedparser, json, hashlib
from datetime import datetime, timezone, timedelta, date

RSS_STOCK = [
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",     # MarketWatch top
    "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",    # MarketWatch pulse
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",          # CNBC top
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",           # CNBC markets
    "https://www.cnbc.com/id/15839135/device/rss/rss.html",           # CNBC finance
    "https://finance.yahoo.com/news/rssindex",                        # Yahoo Finance
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",                  # WSJ Markets
    "https://www.investing.com/rss/news_25.rss",                      # Investing.com stock
    "https://seekingalpha.com/market_currents.xml",                   # Seeking Alpha
]
RSS_ECON = [
    "https://www.cnbc.com/id/20910258/device/rss/rss.html",           # CNBC Economy
    "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",      # WSJ/DJ World
    "https://www.investing.com/rss/news_14.rss",                      # Investing economy
    "https://feeds.a.dj.com/rss/RSSEconomy.xml",                      # WSJ Economy
]
RSS_WORLD = [
    "https://feeds.bbci.co.uk/news/business/rss.xml",                 # BBC Business
    "https://feeds.bbci.co.uk/news/world/rss.xml",                    # BBC World
    "https://www.aljazeera.com/xml/rss/all.xml",                      # Al Jazeera
    "http://rss.cnn.com/rss/money_news_international.rss",             # CNN Money Intl
    "https://feeds.content.dowjones.io/public/rss/RSSWSJD",           # WSJ Tech
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
    """ดึงข่าวใหม่ พร้อมเก็บ (หัวข้อ, ลิงก์) แยกกัน"""
    out = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:n]:
                tid = title_id(e.title)
                if tid in seen:
                    continue
                seen.add(tid)
                link = getattr(e, 'link', '')
                out.append({"title": e.title, "link": link})
        except Exception as ex:
            print("RSS error:", url, ex)
    return out

stock_items = fetch(RSS_STOCK, n=6)
econ_items = fetch(RSS_ECON, n=5)
world_items = fetch(RSS_WORLD, n=5)

total_new = len(stock_items) + len(econ_items) + len(world_items)
print(f"ข่าวใหม่ที่เจอ: {total_new}")

if total_new == 0:
    save_seen(seen)
    print("ไม่มีข่าวใหม่ ไม่ส่ง")
    raise SystemExit(0)

# ---- คำนวณ DST อัตโนมัติ (US Eastern) ----
# DST สหรัฐ: อาทิตย์ที่ 2 ของ มี.ค. ถึง อาทิตย์ที่ 1 ของ พ.ย.
def is_us_dst(dt_utc):
    year = dt_utc.year
    # อาทิตย์ที่ 2 ของมีนาคม
    march = date(year, 3, 8)
    dst_start = march + timedelta(days=(6 - march.weekday()) % 7)  # อาทิตย์แรก >= 8 มี.ค.
    # อาทิตย์ที่ 1 ของพฤศจิกายน
    nov = date(year, 11, 1)
    dst_end = nov + timedelta(days=(6 - nov.weekday()) % 7)
    today = dt_utc.date()
    return dst_start <= today < dst_end

now_utc = datetime.now(timezone.utc)
et_offset = -4 if is_us_dst(now_utc) else -5   # EDT=-4 (ร้อน), EST=-5 (หนาว)
now_et = now_utc + timedelta(hours=et_offset)
now_th = now_utc + timedelta(hours=7)

date_str = now_th.strftime("%d/%m/%Y %H:%M")
et_time = now_et.strftime("%H:%M")
et_hour, et_min = now_et.hour, now_et.minute
et_weekday = now_et.weekday()
mins = et_hour * 60 + et_min
market_open, market_close = 9*60+30, 16*60

# ---- วันหยุดตลาดสหรัฐ (NYSE) ----
US_HOLIDAYS_2026 = {
    "2026-01-01",  # New Year
    "2026-01-19",  # MLK Day
    "2026-02-16",  # Presidents Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day (obs)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Christmas
}
et_date_str = now_et.strftime("%Y-%m-%d")
is_holiday = et_date_str in US_HOLIDAYS_2026

if is_holiday:
    mode_header = "🎌 ตลาดสหรัฐหยุด (วันหยุดพิเศษ)"
    mode_instruction = "โหมดวันหยุดตลาด (ตลาดหุ้นสหรัฐปิดวันนี้): สรุปข่าวสำคัญ, ประเด็นที่อาจกระทบตลาดเมื่อกลับมาเปิด, ไม่ต้องรายงานราคาเรียลไทม์"
elif et_weekday >= 5:
    mode_header = "🛌 ตลาดสหรัฐปิดทำการ (สุดสัปดาห์)"
    mode_instruction = "โหมดสุดสัปดาห์ (ตลาดหุ้นสหรัฐปิด เสาร์-อาทิตย์): สรุปข่าวสำคัญช่วงสุดสัปดาห์, ประเด็นที่อาจกระทบตลาดเมื่อเปิดวันจันทร์, ไม่ต้องรายงานราคาเรียลไทม์"
elif mins < market_open:
    mode_header = "☀️ ก่อนตลาดสหรัฐเปิด (Pre-market)"
    mode_instruction = "โหมดก่อนตลาดเปิด: เน้นสิ่งที่ต้องจับตาก่อนตลาดเปิด, ทิศทาง futures, ตัวเลขเศรษฐกิจที่จะประกาศ"
elif mins < market_close:
    mode_header = "🔔 ระหว่างตลาดสหรัฐเปิด (Live)"
    mode_instruction = "โหมดระหว่างเทรด: เน้นความเคลื่อนไหวตลาดตอนนี้, หุ้นที่วิ่งแรง, ปัจจัยขับเคลื่อน"
else:
    mode_header = "🌙 ตลาดสหรัฐปิดแล้ว (Closing)"
    mode_instruction = "โหมดปิดตลาด: เน้นสรุปตลาดปิดยังไง, หุ้นเด่นวันนี้, after-hours"

def fmt(items):
    return "\n".join(f"- {it['title']}" for it in items) if items else "(ไม่มีข่าวใหม่)"

prompt = f"""คุณเป็นนักวิเคราะห์การเงินมืออาชีพ เขียนรายงานสรุปข่าวเป็นภาษาไทย โดยยึด "กฎการเขียนรายงาน" อย่างเคร่งครัด ห้ามละเมิด

=== กฎการเขียนรายงาน (ห้ามละเมิด) ===

1. ห้ามแต่งหรือคาดเดาข้อมูล
- สรุปเฉพาะสิ่งที่อยู่ในข่าวจริงเท่านั้น
- หากไม่มีข้อมูล ให้เขียนว่า "ไม่มีข้อมูลสำคัญ"
- ห้ามใส่ตัวเลข % หรือราคา ที่ไม่ได้ปรากฏในข่าวจริง

2. ข่าวหุ้น
- เลือกเฉพาะข่าวที่มีผลต่อราคาหุ้น
- สรุปสั้น 1-3 ประโยคต่อข่าว
- ห้ามใช้คำว่า "หุ้นที่ดีที่สุด" หรือ "น่าซื้อ" เว้นแต่เป็นคำพูดของนักวิเคราะห์ และต้องระบุว่า "นักวิเคราะห์มองว่า..."

3. ข่าวเศรษฐกิจ
- รายงานเฉพาะตัวเลขเศรษฐกิจที่ประกาศ หรือมีกำหนดประกาศ
- หากไม่มี ให้เขียนว่า "วันนี้ไม่มีตัวเลขเศรษฐกิจสำคัญ"

4. ข่าวโลก
- เฉพาะข่าวที่อาจส่งผลต่อตลาดการเงิน เช่น สงคราม นโยบายการค้า ธนาคารกลาง ราคาน้ำมัน ภัยธรรมชาติขนาดใหญ่

5. Sector วันนี้
- วิเคราะห์จากภาพรวมข่าวทั้งหมด
- ห้ามสรุปว่า Sector ใดร้อนแรงเพียงเพราะมีข่าวหุ้น 1-2 ตัว
- หากข้อมูลไม่พอ ให้เขียนว่า "ยังไม่มี Sector เด่นชัด"

6. Market Sentiment
- ห้ามใช้คำว่า Risk-on หรือ Risk-off หากไม่มีข้อมูลสนับสนุน (เช่น S&P 500 Futures, Nasdaq Futures, VIX, US Treasury Yield, Dollar Index)
- ข้อมูลข่าว RSS ที่ให้มามักไม่มีตัวเลขเหล่านี้ ดังนั้นโดยปกติให้ใช้คำว่า "Sentiment ยังเป็นกลาง" เว้นแต่ในข่าวระบุตัวเลขเหล่านี้ชัดเจน

7. ปัจจัยต้องจับตา
- ระบุเฉพาะเหตุการณ์ที่จะเกิดขึ้นจริงและมีชื่อชัดเจน เช่น CPI, PPI, FOMC, Earnings, GDP, Jobless Claims
- ห้ามเขียนข้อความทั่วไปลอยๆ เช่น "จับตาเศรษฐกิจ" หรือ "ติดตามตลาด"
- หากในข่าวไม่ได้ระบุเหตุการณ์ที่กำหนดไว้ ให้เขียนว่า "ไม่มีปัจจัยที่ระบุชัดในวันนี้"

8. ตรวจสอบก่อนส่ง
- ไม่มีข้อความขัดแย้งกันเอง
- ไม่มีตัวอักษรแปลกหรือภาษาต่างชาติปน (จีน ญี่ปุ่น เกาหลี เวียดนาม) — แปลเป็นไทยให้หมด ยกเว้นชื่อบริษัท/ticker อังกฤษ
- ชื่อบริษัทและตัวย่อหุ้น (ticker) ต้องถูกต้อง
- หากข้อมูลไม่แน่ชัด ให้ระบุว่า "ยังไม่มีข้อมูลยืนยัน"

เป้าหมาย: รายงานที่ถูกต้อง กระชับ ไม่สรุปเกินหลักฐานในข่าว

=== รูปแบบการเขียน ===
- ห้ามใช้ Markdown (###, **, __) ใช้อีโมจีและข้อความล้วน
- ทุกบริษัท/หุ้นใส่ ticker เช่น Nvidia (NVDA); ทุกดัชนีใส่ชื่อย่อ เช่น S&P 500 (SPX)
- ระดับความสำคัญนำหน้าข่าวเด่น: 🔴 กระทบแรง, 🟡 ปานกลาง, 🟢 ทั่วไป

=== โครงสร้างข้อความ ===

บรรทัดแรก: "{mode_header}"
บรรทัดสอง: "🇹🇭 {date_str} น. | 🇺🇸 {et_time} ET"
{mode_instruction}

📈 หุ้น
(ตามกฎข้อ 2)

💰 เศรษฐกิจ
(ตามกฎข้อ 3)

🌍 สถานการณ์โลก
(ตามกฎข้อ 4)

🔥 Sector วันนี้
(ตามกฎข้อ 5)

👀 ปัจจัยต้องจับตา
(ตามกฎข้อ 7)

🎯 มุมมองการลงทุน / Market Sentiment
(ตามกฎข้อ 6 — ระบุ Sentiment, หุ้น/sector น่าจับตาถ้ามีในข่าว, ความเสี่ยง, สรุป 1-2 ประโยค)

=== ข่าวหุ้น ===
{fmt(stock_items)}

=== ข่าวเศรษฐกิจ ===
{fmt(econ_items)}

=== ข่าวสถานการณ์โลก ===
{fmt(world_items)}
"""

# ระบบหลายผู้ให้บริการ: ลองไล่ Groq ก่อน (เร็ว) ถ้าหมดโควตาค่อยไป Cerebras (token เยอะ)
PROVIDERS = [
    {
        "name": "Groq-8b",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model": "llama-3.1-8b-instant",
    },
    {
        "name": "Groq-70b",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
    },
    {
        "name": "Cerebras-120b",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key_env": "CEREBRAS_API_KEY",
        "model": "gpt-oss-120b",
    },
]

text = None
for p in PROVIDERS:
    key = os.environ.get(p["key_env"])
    if not key:
        print(f"ข้าม {p['name']}: ไม่มี {p['key_env']}")
        continue
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": p["model"], "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.55, "max_tokens": 3500}
    try:
        r = requests.post(p["url"], headers=headers, json=payload, timeout=120)
        data = r.json()
    except Exception as ex:
        print(f"{p['name']} error:", ex)
        continue
    if "choices" in data:
        text = data["choices"][0]["message"]["content"]
        print(f"ใช้ {p['name']} ({p['model']}) | {mode_header} | {et_time} ET (offset {et_offset})")
        break
    else:
        print(f"{p['name']} ใช้ไม่ได้:", data.get("error", data))

if text is None:
    raise SystemExit("ลองทุก provider แล้วใช้ไม่ได้เลย")

def send_telegram(msg):
    resp = requests.post(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
        json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": msg,
              "disable_web_page_preview": True}
    )
    if not resp.ok:
        print("Telegram error:", resp.text)
    return resp.ok

for i in range(0, len(text), 4000):
    send_telegram(text[i:i+4000])

save_seen(seen)
print("Done")
