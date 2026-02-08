
import requests
from bs4 import BeautifulSoup
import time
import random
import datetime
import os
import re
import warnings
import html
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ==========================================
# 1. 設定エリア
# ==========================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

OUTPUT_FILENAME = "index.html"
MAX_ARTICLES_PER_FEED = 10

# RSSフィード設定（HTML構造に依存しないXML方式）
FEED_CONFIGS = {
    "朝の新聞": {
        "site_name": "ロイター通信 (テック)",
        "rss_url": "https://news.google.com/rss/search?q=site:jp.reuters.com%20technology&hl=ja&gl=JP&ceid=JP:ja",
    },
    "創作のネタ": {
        "site_name": "WIRED (サイエンス)",
        "rss_url": "https://news.google.com/rss/search?q=site:wired.jp%20science&hl=ja&gl=JP&ceid=JP:ja",
    },
    "好奇心": {
        "site_name": "ナショナル ジオグラフィック",
        "rss_url": "https://news.google.com/rss/search?q=site:natgeo.nikkeibp.co.jp&hl=ja&gl=JP&ceid=JP:ja",
    }
}

# ==========================================
# 2. RSS取得用クラス
# ==========================================

class RSSScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_soup(self, url):
        """URLからBeautifulSoupオブジェクトを取得 (可能な限りXMLとして解析)"""
        try:
            response = self.session.get(url, timeout=25)
            response.raise_for_status()
            
            # features="xml" を試みる (lxmlが必要)
            # もしlxmlがない場合は自動的に html.parser にフォールバックされるが明示的に書く
            try:
                soup = BeautifulSoup(response.content, features="xml")
            except Exception:
                # 失敗した場合は標準の html.parser を使用 (タグ名が小文字になる点に注意)
                soup = BeautifulSoup(response.content, features="html.parser")
            return soup
        except Exception as e:
            print(f"   ⚠️ フィード取得失敗 ({url}): {e}")
            return None

    def scrape_category(self, category, config):
        """RSSフィードから記事情報を抽出"""
        print(f"🔍 RSS取得中: {config['site_name']} ({category})")
        soup = self.get_soup(config['rss_url'])
        if not soup: return []

        articles = []
        # RSS 1.0/2.0 両方の item タグに対応
        items = soup.find_all('item')
        
        count = 0
        for item in items:
            if count >= MAX_ARTICLES_PER_FEED: break
            try:
                # タイトルの取得
                title_tag = item.find('title')
                if not title_tag: continue
                title = title_tag.text.strip()
                
                # リンクの取得
                link_tag = item.find('link')
                if not link_tag: continue
                link = link_tag.text.strip()
                
                # linkタグが空でも item の next_sibling 等にある場合があるため補完（BS4のXMLパース挙動対策）
                if not link:
                    link = item.link.next_sibling.strip() if item.link and item.link.next_sibling else ""
                
                if not link: continue
                
                # 公開日時の取得 (pubDate, dc:date, date などに対応)
                # html.parser の場合はタグ名が小文字になるため両方チェック
                date_tag = (item.find('pubDate') or item.find('pubdate') or 
                            item.find('dc:date') or item.find('date'))
                pub_date = date_tag.text.strip() if date_tag else ""
                
                # 日付表示の整形 (RSSの多様な形式に対応)
                display_date = pub_date
                if pub_date:
                    # 簡易的な抽出: RFC822形式(ロイター)やISO形式(ナショジオ)から月/日を推測
                    match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', pub_date, re.I)
                    if match:
                        display_date = f"{match.group(2)} {match.group(1)}"
                    else:
                        match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', pub_date)
                        if match:
                            display_date = f"{match.group(2)}/{match.group(3)}"
                
                # 概要の取得
                desc_tag = item.find('description')
                description = desc_tag.text.strip() if desc_tag else ""
                # HTMLタグの除去と文字数制限
                if description:
                    description = re.sub(r'<[^>]+>', '', description)
                    description = description.replace('\n', ' ').strip()
                    if len(description) > 100:
                        description = description[:100] + "..."

                # 重複回避
                if any(art['url'] == link for art in articles): continue

                # エスケープ処理（特殊文字によるHTML崩れや警告を防止）
                safe_title = html.escape(html.unescape(title))
                safe_link = html.escape(link)
                safe_description = html.escape(html.unescape(description))

                articles.append({
                    "title": safe_title,
                    "url": safe_link,
                    "site": config['site_name'],
                    "date": display_date,
                    "description": safe_description
                })
                count += 1
            except Exception:
                continue
        
        print(f"   ✨ {len(articles)}件の記事を取得しました。")
        return articles

# ==========================================
# 3. HTML生成クラス (タブ切り替え + 概要表示)
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
    <title>RSS News Patrol</title>
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
            padding: 50px 20px;
            background: linear-gradient(135deg, #1e3a8a, #3b82f6);
            color: white;
            border-radius: 32px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }}
        header h1 {{ font-size: 3rem; margin-bottom: 10px; font-weight: 700; letter-spacing: -0.05em; }}
        header p {{ font-size: 1.1rem; opacity: 0.9; }}

        .tabs {{
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-bottom: 30px;
            overflow-x: auto;
            padding: 10px;
            scrollbar-width: none;
        }}
        .tabs::-webkit-scrollbar {{ display: none; }}
        
        .tab-btn {{
            padding: 12px 28px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            color: var(--text-main);
            border-radius: 99px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            white-space: nowrap;
        }}
        .tab-btn.active {{
            background: var(--primary);
            color: white;
            border-color: var(--primary);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }}

        .tab-content {{ display: none; animation: fadeIn 0.5s ease; }}
        .tab-content.active {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 25px; }}

        .card {{
            background: var(--card-bg);
            border-radius: 20px;
            padding: 25px;
            display: flex;
            flex-direction: column;
            transition: transform 0.3s, box-shadow 0.3s;
            text-decoration: none;
            color: inherit;
            border: 1px solid var(--border);
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            border-color: var(--primary);
        }}
        .card h3 {{
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 12px;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .description {{
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-bottom: 15px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            flex-grow: 1;
        }}
        .card-footer {{
            margin-top: auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            padding-top: 15px;
            border-top: 1px solid var(--border);
        }}
        .badge {{
            background: #eff6ff;
            color: #2563eb;
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.75rem;
        }}
        @media (prefers-color-scheme: dark) {{
            .badge {{ background: #1e293b; color: #60a5fa; }}
        }}

        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        footer {{ text-align: center; margin-top: 80px; padding: 40px; color: var(--text-muted); border-top: 1px solid var(--border); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>News Patrol</h1>
            <p>{today} | 厳選された最新トピック (RSSフィード)</p>
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
            <p>&copy; 2026 RSS Scraper Pro. Modern News Delivery.</p>
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
            html += '<div style="grid-column: 1/-1; text-align: center; padding: 60px; color: var(--text-muted);">新しいニュースは見つかりませんでした。</div>'
        else:
            for a in articles:
                desc_html = f'<p class="description">{a["description"]}</p>' if a.get('description') else ""
                html += f"""
                <a href="{a['url']}" target="_blank" rel="noopener" class="card">
                    <h3>{a['title']}</h3>
                    {desc_html}
                    <div class="card-footer">
                        <span class="badge">{a['site']}</span>
                        <span>{a['date']}</span>
                    </div>
                </a>"""
        
        html += '</div>'
        return html

# ==========================================
# 4. メイン処理
# ==========================================

def main():
    print("🚀 RSSフィード巡回を開始します...")
    scraper = RSSScraper()
    
    # カテゴリデータの初期化 (構文エラー防止のためシンプルに)
    collected_data = {}
    collected_data["朝の新聞"] = []
    collected_data["創作のネタ"] = []
    collected_data["好奇心"] = []

    # 各カテゴリのフィードからデータを収集
    for category, config in FEED_CONFIGS.items():
        try:
            # フィードごとに独立して処理し、一カ所のエラーが全体に影響しないようにする
            articles = scraper.scrape_category(category, config)
            collected_data[category] = articles
        except Exception as e:
            print(f"   🔥 カテゴリ「{category}」で予期せぬエラーが発生しましたが、続行します: {e}")

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

if __name__ == "__main__":
    main()