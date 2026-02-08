
import requests
from bs4 import BeautifulSoup
import time
import random
import datetime
import os

# ==========================================
# 1. 設定エリア
# ==========================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

OUTPUT_FILENAME = "index.html"
WAIT_TIME_MIN = 1.0
WAIT_TIME_MAX = 2.0
MAX_ARTICLES_PER_SITE = 8

# スクレイピング設定の集中管理（メンテナンス性向上）
# 各サイトのHTML構造に合わせたセレクタを定義
SITE_CONFIGS = {
    "朝の新聞": {
        "site_name": "ロイター通信 (テック)",
        "url": "https://jp.reuters.com/business/technology/",
        "base_url": "https://jp.reuters.com",
        "selectors": {
            "items": "div[data-testid^='StoryCard'], article",
            "title": "[data-testid='Heading']",
            "link": "a"
        }
    },
    "創作のネタ": {
        "site_name": "WIRED (サイエンス)",
        "url": "https://wired.jp/category/science/",
        "base_url": "https://wired.jp",
        "selectors": {
            "items": "div.c-card, article.c-card",
            "title": "h2.c-card__heading",
            "link": "a.c-card__link"
        }
    },
    "好奇心": {
        "site_name": "ナショナル ジオグラフィック",
        "url": "https://natgeo.nikkeibp.co.jp/atcl/news/",
        "base_url": "https://natgeo.nikkeibp.co.jp",
        "selectors": {
            "items": "ul.list_news > li",
            "title": "h3, .title",
            "link": "a"
        }
    }
}

# ==========================================
# 2. スクレイピング用クラス
# ==========================================

class NewsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def polite_sleep(self):
        """サイトへの負荷を抑えるための待機"""
        time.sleep(random.uniform(WAIT_TIME_MIN, WAIT_TIME_MAX))

    def get_soup(self, url):
        """URLからBeautifulSoupオブジェクトを取得"""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"   ⚠️ 取得失敗 ({url}): {e}")
            return None

    def scrape_category(self, category, config):
        """特定のサイトから記事情報を抽出"""
        print(f"🔍 記事取得中: {config['site_name']} ({category})")
        soup = self.get_soup(config['url'])
        if not soup: return []

        articles = []
        sel = config['selectors']
        # 設定されたセレクタに基づいて要素を抽出
        items = soup.select(sel['items'])
        
        count = 0
        for item in items:
            if count >= MAX_ARTICLES_PER_SITE: break
            try:
                # タイトルの取得
                title_tag = item.select_one(sel['title'])
                if not title_tag: continue
                title = title_tag.text.strip()
                
                # リンクの取得（見つからない場合は項目内の最初のaタグを探す）
                link_tag = item.select_one(sel['link']) or item.find('a')
                if not link_tag: continue
                link = link_tag.get('href', '')
                
                if not link: continue
                
                # 相対パスを絶対パスへ変換
                if not link.startswith('http'):
                    link = config['base_url'] + link

                # 重複回避
                if any(a['url'] == link for a in articles): continue

                articles.append({
                    "title": title,
                    "url": link,
                    "site": config['site_name'],
                    "date": datetime.date.today().strftime('%m/%d')
                })
                count += 1
            except Exception:
                continue
        
        print(f"   ✨ {len(articles)}件の記事を取得しました。")
        self.polite_sleep()
        return articles

# ==========================================
# 3. HTML生成クラス (Premium Design)
# ==========================================

class HtmlGenerator:
    def __init__(self, data):
        self.data = data

    def generate(self):
        """収集したデータからHTMLレポートを生成"""
        today = datetime.date.today().strftime('%Y年%m月%d日')
        
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily News Patrol</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #f8fafc;
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --accent: #f59e0b;
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
            font-family: 'Outfit', 'Noto Sans JP', sans-serif;
            background: var(--bg);
            color: var(--text-main);
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 60px 20px;
            background: linear-gradient(135deg, #1e3a8a, #3b82f6);
            color: white;
            border-radius: 32px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            position: relative;
            overflow: hidden;
        }}
        header::after {{
            content: '';
            position: absolute;
            top: -50%; left: -50%; width: 200%; height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
            pointer-events: none;
        }}
        header h1 {{ font-size: 3.5rem; margin-bottom: 15px; font-weight: 700; letter-spacing: -0.05em; }}
        header p {{ font-size: 1.2rem; opacity: 0.9; font-weight: 500; }}

        .tabs {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-bottom: 40px;
            overflow-x: auto;
            padding: 10px;
            scrollbar-width: none;
        }}
        .tabs::-webkit-scrollbar {{ display: none; }}
        
        .tab-btn {{
            padding: 14px 32px;
            border: none;
            background: var(--card-bg);
            color: var(--text-main);
            border-radius: 20px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            white-space: nowrap;
            border: 1px solid var(--border);
        }}
        .tab-btn.active {{
            background: var(--primary);
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
            border-color: var(--primary);
        }}
        .tab-btn:hover:not(.active) {{
            border-color: var(--primary);
            color: var(--primary);
        }}

        .tab-content {{ display: none; animation: slideUp 0.6s cubic-bezier(0.23, 1, 0.32, 1); }}
        .tab-content.active {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 30px; }}

        .card {{
            background: var(--card-bg);
            border-radius: 24px;
            padding: 30px;
            display: flex;
            flex-direction: column;
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            text-decoration: none;
            color: inherit;
            border: 1px solid var(--border);
            position: relative;
        }}
        .card:hover {{
            transform: translateY(-10px);
            box-shadow: 0 25px 30px -10px rgba(0, 0, 0, 0.1);
            border-color: var(--primary);
        }}
        .card h3 {{
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 20px;
            line-height: 1.5;
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
            font-size: 0.9rem;
            color: var(--text-muted);
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }}
        .site-badge {{
            background: #eff6ff;
            color: #2563eb;
            padding: 6px 14px;
            border-radius: 10px;
            font-weight: 800;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        @media (prefers-color-scheme: dark) {{
            .site-badge {{ background: #1e293b; color: #60a5fa; }}
        }}

        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        footer {{
            text-align: center;
            margin-top: 100px;
            padding: 60px;
            color: var(--text-muted);
            border-top: 1px solid var(--border);
            font-weight: 500;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>News Patrol</h1>
            <p>{today} | 厳選された最新トピック</p>
        </header>

        <div class="tabs">
            <button class="tab-btn active" onclick="openTab(event, 'morning')">朝の新聞</button>
            <button class="tab-btn" onclick="openTab(event, 'creative')">創作のネタ</button>
            <button class="tab-btn" onclick="openTab(event, 'curiosity')">好奇心</button>
        </div>

        {self._gen_section('morning', self.data.get('朝の新聞', []), True)}
        {self._gen_section('creative', self.data.get('創作のネタ', []))}
        {self._gen_section('curiosity', self.data.get('好奇心', []))}

        <footer>
            <p>&copy; 2026 News Scraper Pro. Modern News Delivery System.</p>
        </footer>
    </div>

    <script>
        function openTab(e, id) {{
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            const target = document.getElementById(id);
            if (target) target.classList.add('active');
            if (e && e.currentTarget) e.currentTarget.classList.add('active');
        }}
    </script>
</body>
</html>
"""
        return html

    def _gen_section(self, section_id, articles, active=False):
        """セクションごとのHTML要素を生成"""
        status_class = "tab-content active" if active else "tab-content"
        html = f'<div id="{section_id}" class="{status_class}">'
        
        if not articles:
            html += '<div style="grid-column: 1/-1; text-align: center; padding: 80px; color: var(--text-muted); font-size: 1.1rem;">新しいニュースは見つかりませんでした。</div>'
        else:
            for a in articles:
                html += f"""
                <a href="{a['url']}" target="_blank" class="card">
                    <h3>{a['title']}</h3>
                    <div class="card-footer">
                        <span class="site-badge">{a['site']}</span>
                        <span>{a['date']}</span>
                    </div>
                </a>"""
        
        html += '</div>'
        return html

# ==========================================
# 4. メイン処理
# ==========================================

def main():
    print("🚀 ニュース巡回（ロイター / WIRED / ナショジオ）を開始します...")
    scraper = NewsScraper()
    collected_data = {}

    # 各カテゴリのサイトからデータを収集
    for category, config in SITE_CONFIGS.items():
        try:
            # 各サイトの処理を try-except で囲み、一つが失敗しても他を続行できるようにする
            collected_data[category] = scraper.scrape_category(category, config)
        except Exception as e:
            print(f"   🔥 カテゴリ「{category}」でエラーが発生しましたが、続行します: {e}")
            collected_data[category] = []

    # HTML生成と保存
    print("\n📝 レポートを作成中...")
    generator = HtmlGenerator(collected_data)
    html_content = generator.generate()
    
    try:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n✅ 完了！結果を {OUTPUT_FILENAME} に保存しました。")
    except Exception as e:
        print(f"   ❌ ファイル保存に失敗しました: {e}")

    # GitHub Actions等のCI環境で実行する場合を考慮し、ブラウザ起動は無効化
    # import webbrowser
    # webbrowser.open("file://" + os.path.abspath(OUTPUT_FILENAME))

if __name__ == "__main__":
    main()