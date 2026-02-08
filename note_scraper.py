
import requests
from bs4 import BeautifulSoup
import time
import random
import datetime
import os
import re
import warnings
import html
import json
from bs4 import XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ==========================================
# 1. 設定エリア
# ==========================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

OUTPUT_FILENAME = "index.html"
MAX_ARTICLES_PER_FEED = 8

# Gemini API設定 (環境変数から取得)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

FEED_CONFIGS = {
    "朝の新聞": {
        "site_name": "ロイター通信 (テック)",
        "rss_url": "https://news.google.com/rss/search?q=site:jp.reuters.com%20technology&hl=ja&gl=JP&ceid=JP:ja",
        "icon": "📰"
    },
    "創作のネタ": {
        "site_name": "WIRED (サイエンス)",
        "rss_url": "https://news.google.com/rss/search?q=site:wired.jp%20science&hl=ja&gl=JP&ceid=JP:ja",
        "icon": "🧪"
    },
    "好奇心": {
        "site_name": "ナショナル ジオグラフィック",
        "rss_url": "https://news.google.com/rss/search?q=site:natgeo.nikkeibp.co.jp&hl=ja&gl=JP&ceid=JP:ja",
        "icon": "🦁"
    }
}

# ==========================================
# 2. AI & プロセッサ
# ==========================================

class AISummarizer:
    @staticmethod
    def summarize(text):
        if not GEMINI_API_KEY or not text or len(text) < 50:
            return text
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{
                    "parts": [{
                        "text": (
                            "あなたは優秀なニュース編集者です。以下のニュース（英語の場合は日本語に翻訳してください）を、"
                            "内容が正確に伝わるように簡潔な日本語の3つの重要ポイント（箇条書き）に要約してください。"
                            "出力は要約された箇条書きのみにしてください。：\n\n"
                            f"{text}"
                        )
                    }]
                }]
            }
            res = requests.post(url, json=payload, timeout=10)
            data = res.json()
            summary = data['candidates'][0]['content']['parts'][0]['text']
            return summary.replace('\n', '<br>')
        except:
            return text

class RSSScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_soup(self, url):
        try:
            response = self.session.get(url, timeout=25)
            response.raise_for_status()
            try:
                soup = BeautifulSoup(response.content, features="xml")
            except:
                soup = BeautifulSoup(response.content, "html.parser")
            return soup
        except Exception as e:
            print(f"   ⚠️ フィード取得失敗 ({url}): {e}")
            return None

    def _extract_image(self, item):
        # media:content, enclosure, もしくはdescription内のimgタグから抽出
        img_url = ""
        media = item.find('media:content') or item.find('enclosure', type=re.compile(r'image/.*'))
        if media and media.get('url'):
            img_url = media['url']
        
        if not img_url:
            desc = str(item.find('description'))
            img_match = re.search(r'<img[^>]+src="([^">]+)"', desc)
            if img_match:
                img_url = img_match.group(1)
        
        # Googleニュースのデフォルト画像（lh3.googleusercontent...）は避けるかランダム画像へ
        if not img_url or "googleusercontent" in img_url:
            return f"https://picsum.photos/seed/{random.random()}/600/400"
        return img_url

    def scrape_category(self, category, config):
        print(f"🔍 RSS取得中: {config['site_name']} ({category})")
        soup = self.get_soup(config['rss_url'])
        if not soup: return []

        articles = []
        items = soup.find_all('item')
        
        for item in items[:MAX_ARTICLES_PER_FEED]:
            try:
                title = item.find('title').text.strip()
                link = item.find('link').text.strip()
                if not link: link = item.link.next_sibling.strip()
                
                date_tag = (item.find('pubDate') or item.find('pubdate') or 
                            item.find('dc:date') or item.find('date'))
                pub_date = date_tag.text.strip() if date_tag else ""
                
                display_date = pub_date
                if pub_date:
                    match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', pub_date, re.I)
                    if match: display_date = f"{match.group(2)} {match.group(1)}"
                    else:
                        match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', pub_date)
                        if match: display_date = f"{match.group(2)}/{match.group(3)}"
                
                raw_desc = item.find('description').text.strip() if item.find('description') else ""
                clean_desc = re.sub(r'<[^>]+>', '', raw_desc).replace('\n', ' ').strip()
                
                # AI要約（オプション）
                summary = AISummarizer.summarize(clean_desc) if len(clean_desc) > 100 else clean_desc
                image = self._extract_image(item)

                articles.append({
                    "id": hashlib.md5(link.encode()).hexdigest(),
                    "title": html.escape(html.unescape(title)),
                    "url": html.escape(link),
                    "site": config['site_name'],
                    "icon": config['icon'],
                    "date": display_date,
                    "description": html.escape(html.unescape(summary[:300])),
                    "image": image
                })
            except: continue
        
        print(f"   ✨ {len(articles)}件の記事を取得しました。")
        return articles

# hashlibが必要になったので追加
import hashlib

# ==========================================
# 3. HTML生成クラス
# ==========================================

class HtmlGenerator:
    def __init__(self, data):
        self.data = data

    def generate(self):
        today = datetime.date.today().strftime('%Y年%m月%d日')
        
        html_template = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>News Patrol Pro</title>
    <link rel="manifest" href="manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#2563eb">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #f1f5f9;
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --safe-area-inset-bottom: env(safe-area-inset-bottom);
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg: #020617;
                --card-bg: #0f172a;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --border: #1e293b;
            }}
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
        body {{
            font-family: 'Outfit', 'Noto Sans JP', sans-serif;
            background: var(--bg);
            color: var(--text-main);
            line-height: 1.6;
            padding-bottom: calc(80px + var(--safe-area-inset-bottom));
        }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        header {{
            position: sticky; top: 0; z-index: 100;
            background: var(--bg);
            padding: 20px 0;
            margin-bottom: 20px;
        }}
        .header-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        h1 {{ font-size: 1.8rem; font-weight: 700; letter-spacing: -1px; }}
        .date {{ font-size: 0.9rem; color: var(--text-muted); }}

        .search-container {{
            margin-bottom: 20px;
        }}
        #searchInput {{
            width: 100%;
            padding: 14px 20px;
            border-radius: 16px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            color: var(--text-main);
            font-size: 1rem;
            outline: none;
            transition: 0.3s;
        }}
        #searchInput:focus {{ border-color: var(--primary); box-shadow: 0 0 0 4px rgba(37,99,235,0.1); }}

        .tabs {{
            display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px;
            scrollbar-width: none;
        }}
        .tabs::-webkit-scrollbar {{ display: none; }}
        .tab-btn {{
            padding: 10px 22px; border-radius: 99px; border: 1px solid var(--border);
            background: var(--card-bg); color: var(--text-main); font-weight: 700;
            cursor: pointer; white-space: nowrap; transition: 0.3s;
        }}
        .tab-btn.active {{ background: var(--primary); color: white; border-color: var(--primary); }}

        .news-list {{ display: flex; flex-direction: column; gap: 20px; }}
        .card {{
            background: var(--card-bg); border-radius: 24px; overflow: hidden;
            border: 1px solid var(--border); transition: 0.3s;
            text-decoration: none; color: inherit; display: block;
        }}
        .card.read {{ opacity: 0.6; }}
        .card-img {{ width: 100%; height: 200px; background-size: cover; background-position: center; }}
        .card-body {{ padding: 20px; }}
        .card-site {{ display: flex; align-items: center; gap: 6px; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px; }}
        .card h3 {{ font-size: 1.25rem; margin-bottom: 12px; line-height: 1.3; }}
        .description {{ font-size: 0.95rem; color: var(--text-muted); margin-bottom: 15px; }}
        .card-footer {{ display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; border-top: 1px solid var(--border); padding-top: 15px; }}

        /* PWA Float Menu */
        .bottom-nav {{
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
            background: rgba(37,99,235,0.9); backdrop-filter: blur(10px);
            padding: 12px 24px; border-radius: 50px; display: flex; gap: 30px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2); z-index: 1000;
        }}
        .nav-item {{ color: white; text-decoration: none; font-size: 1.2rem; cursor: pointer; }}

        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: flex; flex-direction: column; gap: 20px; animation: fadeIn 0.4s; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-top">
                <h1>News Patrol<span style="color:var(--primary)">.</span></h1>
                <span class="date">{today}</span>
            </div>
            <div class="search-container">
                <input type="text" id="searchInput" placeholder="ニュースを検索..." oninput="filterNews()">
            </div>
            <div class="tabs">
                <button class="tab-btn active" onclick="openTab(event, 'morning')">朝の新聞</button>
                <button class="tab-btn" onclick="openTab(event, 'creative')">創作のネタ</button>
                <button class="tab-btn" onclick="openTab(event, 'curiosity')">好奇心</button>
            </div>
        </header>

        <div id="morning" class="tab-content active">{self._gen_list(self.data.get('朝の新聞', []))}</div>
        <div id="creative" class="tab-content">{self._gen_list(self.data.get('創作のネタ', []))}</div>
        <div id="curiosity" class="tab-content">{self._gen_list(self.data.get('好奇心', []))}</div>

    </div>

    <div class="bottom-nav">
        <div class="nav-item" onclick="window.scrollTo({{top:0, behavior:'smooth'}})">👆</div>
        <div class="nav-item" onclick="clearRead()">🧹</div>
        <div class="nav-item" onclick="location.reload()">🔄</div>
    </div>

    <script>
        // 1. タブ切り替え
        function openTab(e, id) {{
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            e.currentTarget.classList.add('active');
            window.scrollTo(0, 0);
        }}

        // 2. 検索・フィルタリング
        function filterNews() {{
            const q = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('.card').forEach(card => {{
                const text = card.innerText.toLowerCase();
                card.style.display = text.includes(q) ? 'block' : 'none';
            }});
        }}

        // 3. 既読管理
        function markAsRead(id) {{
            let readList = JSON.parse(localStorage.getItem('read_news') || '[]');
            if (!readList.includes(id)) readList.push(id);
            localStorage.setItem('read_news', JSON.stringify(readList));
            updateReadUI();
        }}

        function updateReadUI() {{
            const readList = JSON.parse(localStorage.getItem('read_news') || '[]');
            document.querySelectorAll('.card').forEach(card => {{
                if (readList.includes(card.dataset.id)) card.classList.add('read');
            }});
        }}

        function clearRead() {{
            if(confirm('既読をリセットしますか？')) {{
                localStorage.removeItem('read_news');
                location.reload();
            }}
        }}

        // 初期化
        document.addEventListener('DOMContentLoaded', updateReadUI);
    </script>
</body>
</html>
"""
        return html_template

    def _gen_list(self, articles):
        if not articles:
            return '<div style="text-align:center; padding:100px 0; color:var(--text-muted);">新しいニュースはありません</div>'
        
        html = ""
        for a in articles:
            html += f"""
            <a href="{a['url']}" target="_blank" rel="noopener" class="card" data-id="{a['id']}" onclick="markAsRead('{a['id']}')">
                <div class="card-img" style="background-image: url('{a['image']}')"></div>
                <div class="card-body">
                    <div class="card-site">{a['icon']} {a['site']}</div>
                    <h3>{a['title']}</h3>
                    <div class="description">{a['description']}</div>
                    <div class="card-footer">
                        <span>{a['date']}</span>
                        <span style="color:var(--primary)">Read More →</span>
                    </div>
                </div>
            </a>"""
        return html

def main():
    print("🚀 プレミアムニュース巡回を開始します...")
    scraper = RSSScraper()
    
    collected_data = {cat: scraper.scrape_category(cat, config) for cat, config in FEED_CONFIGS.items()}

    print("\n📝 プレミアムレポートを作成中...")
    html_content = HtmlGenerator(collected_data).generate()
    
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\n✅ 完了！結果を {OUTPUT_FILENAME} に保存しました。")

if __name__ == "__main__":
    main()