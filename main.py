import os, requests, feedparser

RSS = [
    "https://feeds.feedburner.com/oreilly/radar",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://finance.yahoo.com/news/rssindex"
]

items=[]
for url in RSS:
    try:
        feed=feedparser.parse(url)
        for e in feed.entries[:5]:
            items.append(f"- {e.title}\n  {getattr(e,'link','')}")
    except Exception:
        pass

prompt="สรุปข่าวต่อไปนี้เป็นภาษาไทย แบ่งหัวข้อ AI, หุ้น, คริปโต พร้อมผลกระทบต่อการลงทุน\n\n"+"\n".join(items[:15])

api=os.environ["GEMINI_API_KEY"]
endpoint=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api}"
payload={"contents":[{"parts":[{"text":prompt}]}]}
r=requests.post(endpoint,json=payload,timeout=60)
text=r.json()["candidates"][0]["content"]["parts"][0]["text"]

requests.post(
    f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
    json={"chat_id":os.environ["TELEGRAM_CHAT_ID"],"text":text}
)
print("Done")
