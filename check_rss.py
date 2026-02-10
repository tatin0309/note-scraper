import feedparser

base_url = "https://www.nhk.or.jp/rss/news/cat{}.xml"

print("=== NHK RSS Category Check ===")
for i in range(9):
    url = base_url.format(i)
    try:
        feed = feedparser.parse(url)
        if feed.feed.get('title'):
            print(f"[cat{i}.xml] : {feed.feed.title}")
        else:
            print(f"[cat{i}.xml] : (取得不可 - titleなし)")
    except Exception as e:
        print(f"[cat{i}.xml] : Error ({e})")
