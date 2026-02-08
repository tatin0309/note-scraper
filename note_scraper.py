
import requests
from bs4 import BeautifulSoup
import time
import random
import datetime
import webbrowser
import os
import urllib.parse

# ==========================================
# 1. 設定エリア
# ==========================================

SEARCH_RULES = {
    "朝の新聞": ["日本経済", "最新技術", "AIトレンド"],
    "創作のネタ": ["SF設定", "歴史 ミステリー", "ファンタジー"],
    "好奇心": ["深海生物", "珍スポット", "都市伝説"]
}

BOOKMARK_USERS = [
    "info",      # note公式
    "notes",     # note公式マガジン
    "note_pr",   # note広報
]

BASE_URL = "https://note.com"
OUTPUT_FILENAME = "index.html"
MAX_ARTICLES_PER_KEYWORD = 3 
WAIT_TIME_MIN = 1.5
WAIT_TIME_MAX = 3.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

# ==========================================
# 2. スクレイピング用クラス
# ==========================================

class NoteScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def polite_sleep(self):
        sleep_time = random.uniform(WAIT_TIME_MIN, WAIT_TIME_MAX)
        time.sleep(sleep_time)

    def get_soup(self, url):
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            # Noteは外部からのアクセスに厳しい場合があるため、エンコーディングを明示
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"   ⚠️ リクエスト失敗: {e}")
            return None

    def search_keyword(self, keyword):
        print(f"🔍 キーワード検索中: {keyword}")
        encoded_kw = urllib.parse.quote(keyword)
        # 本日の人気順に近い結果を得るために context=note を指定
        url = f"{BASE_URL}/search?q={encoded_kw}&context=note&mode=search"
        
        soup = self.get_soup(url)
        if not soup: return []

        articles = []
        # 全ての a タグを走査し、記事リンク (/n/n...) を探すのが最も確実
        all_links = soup.find_all('a', href=lambda x: x and '/n/n' in x)
        
        count = 0
        for a in all_links:
            if count >= MAX_ARTICLES_PER_KEYWORD: break
            
            try:
                link = a.get('href')
                if link.startswith('/'): link = BASE_URL + link
                
                # 重複回避
                if any(art['url'] == link for art in articles): continue

                # タイトルの取得
                # aタグの中に h3 がある場合や、aタグ自体がテキストを持つ場合がある
                title = ""
                h3 = a.find('h3') or a.find_parent('h3')
                if h3:
                    title = h3.text.strip()
                if not title:
                    title = a.text.strip()
                
                # タイトルが空、または短すぎる（ユーザー名など）場合はスキップ
                if not title or len(title) < 2: 
                    # 親要素から h3 を探す
                    container = a.find_parent('div', class_=lambda x: x and ('item' in x.lower() or 'note' in x.lower()))
                    if container:
                        h3_alt = container.find('h3')
                        if h3_alt: title = h3_alt.text.strip()
                
                if not title: continue

                # 著者の取得
                author = "Unknown"
                container = a.find_parent('div', class_=lambda x: x and ('item' in x.lower() or 'note' in x.lower()))
                if container:
                    author_tag = container.find('a', href=lambda x: x and x.startswith('/') and '/n/' not in x and len(x) > 1)
                    if author_tag: author = author_tag.text.strip()
                
                # クリエイターカード（タイトルと著者が同じ）を除外
                if title == author: continue

                articles.append({
                    "title": title,
                    "url": link,
                    "author": author,
                    "summary": f"キーワード「{keyword}」の結果",
                    "date": datetime.date.today().strftime('%Y-%m-%d')
                })
                count += 1
            except:
                continue
                
        if not articles:
            print(f"   🈚 「{keyword}」の結果がありませんでした。")
        else:
            print(f"   ✨ {len(articles)}件の記事を取得しました。")
                
        self.polite_sleep()
        return articles

    def get_user_articles(self, user_id):
        print(f"👤 クリエイター確認中: {user_id}")
        rss_url = f"{BASE_URL}/{user_id}/rss"
        soup = self.get_soup(rss_url)
        if not soup: return []

        articles = []
        items = soup.find_all('item')
        for item in items[:MAX_ARTICLES_PER_KEYWORD]:
            try:
                articles.append({
                    "title": item.title.text.strip(),
                    "url": item.link.text.strip(),
                    "author": user_id,
                    "summary": "ブックマークの新着",
                    "date": item.pubdate.text[:16] if item.pubdate else ""
                })
            except:
                continue
        self.polite_sleep()
        return articles

# ==========================================
# 3. HTML生成クラス (Premium Design)
# ==========================================

class HtmlGenerator:
    def __init__(self, data):
        self.data = data

    def generate(self):
        today = datetime.date.today().strftime('%Y-%m-%d')
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Note Insight Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #f8fafc;
            --primary: #10b981;
            --primary-dark: #059669;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --card-bg: #ffffff;
            --border: #e2e8f0;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg: #0f172a;
                --card-bg: #1e293b;
                --text-main: #f1f5f9;
                --text-muted: #94a3b8;
                --border: #334155;
            }}
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', 'Noto Sans JP', sans-serif;
            background: var(--bg);
            color: var(--text-main);
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 0;
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            border-radius: 24px;
            box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.3);
        }}
        header h1 {{ font-size: 2.5rem; margin-bottom: 8px; letter-spacing: -0.025em; }}
        header p {{ opacity: 0.9; font-weight: 500; }}

        .tabs {{
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-bottom: 32px;
            overflow-x: auto;
            padding-bottom: 8px;
        }}
        .tab-btn {{
            padding: 10px 24px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            color: var(--text-main);
            border-radius: 99px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;
        }}
        .tab-btn.active {{
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }}
        .tab-btn:hover:not(.active) {{
            border-color: var(--primary);
            color: var(--primary);
        }}

        .tab-content {{ display: none; animation: fadeIn 0.4s ease-out; }}
        .tab-content.active {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}

        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
            color: inherit;
        }}
        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 20px -8px rgba(0,0,0,0.15);
            border-color: var(--primary);
        }}
        .card h3 {{
            font-size: 1.125rem;
            font-weight: 700;
            margin-bottom: 12px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .card-footer {{
            margin-top: auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.875rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border);
            padding-top: 12px;
        }}
        .author {{ font-weight: 600; color: var(--primary); }}
        .tag {{ background: var(--bg); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}

        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        footer {{ text-align: center; margin-top: 60px; color: var(--text-muted); padding: 40px; border-top: 1px solid var(--border); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Note Insight</h1>
            <p>Generated on {today}</p>
        </header>

        <div class="tabs">
            <button class="tab-btn active" onclick="openTab(event, 'news')">朝の新聞</button>
            <button class="tab-btn" onclick="openTab(event, 'creative')">創作のネタ</button>
            <button class="tab-btn" onclick="openTab(event, 'curiosity')">好奇心</button>
            <button class="tab-btn" onclick="openTab(event, 'bookmarks')">ブックマーク</button>
        </div>

        {self._gen_section('news', self.data['朝の新聞'], True)}
        {self._gen_section('creative', self.data['創作のネタ'])}
        {self._gen_section('curiosity', self.data['好奇心'])}
        {self._gen_section('bookmarks', self.data['ブックマーク'])}

        <footer>
            <p>&copy; 2026 Note Scraper Pro. Inspired by your curiosity.</p>
        </footer>
    </div>

    <script>
        function openTab(e, id) {{
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            e.currentTarget.classList.add('active');
        }}
    </script>
</body>
</html>
"""
        return html

    def _gen_section(self, id, articles, active=False):
        cls = "tab-content active" if active else "tab-content"
        content = f'<div id="{id}" class="{cls}">'
        if not articles:
            content += '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">新しい記事は見つかりませんでした。</div>'
        else:
            for a in articles:
                content += f"""
                <a href="{a['url']}" target="_blank" class="card">
                    <h3>{a['title']}</h3>
                    <div class="card-footer">
                        <span class="author">@{a['author']}</span>
                        <span class="tag">{a['summary'][:15]}</span>
                    </div>
                </a>
                """
        content += '</div>'
        return content

# ==========================================
# 4. メイン処理
# ==========================================

def main():
    print("🚀 スクレイピングを開始します（動かない場合は User-Agent を調整してください）...")
    scraper = NoteScraper()
    collected_data = {{k: [] for k in ["朝の新聞", "創作のネタ", "好奇心", "ブックマーク"]}}

    # 1. キーワード検索
    for category, keywords in SEARCH_RULES.items():
        print(f"\n📂 カテゴリ「{category}」")
        for kw in keywords:
            articles = scraper.search_keyword(kw)
            collected_data[category].extend(articles)

    # 2. ブックマーク
    print(f"\n📂 ブックマーク")
    for user_id in BOOKMARK_USERS:
        articles = scraper.get_user_articles(user_id)
        if articles:
            collected_data["ブックマーク"].extend(articles)
            print(f"   ✨ {user_id}: {len(articles)}件取得")

    # 3. 保存
    print("\n📝 レポートを作成中...")
    html = HtmlGenerator(collected_data).generate()
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 完了！ '{OUTPUT_FILENAME}' をブラウザで開きます。")
    webbrowser.open("file://" + os.path.abspath(OUTPUT_FILENAME))

if __name__ == "__main__":
    main()