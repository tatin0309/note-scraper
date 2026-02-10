import feedparser
import re
import os
import sys
import time
import datetime
import socket

# ==========================================
# 0. タイムアウト設定
# ==========================================
# GitHub Actions等でのフリーズ防止のため、30秒でタイムアウト
socket.setdefaulttimeout(30)

# ==========================================
# 1. 設定
# ==========================================

# 取得するRSSフィードのリスト
FEED_CONFIGS = [
    {
        "name": "NHK主要ニュース (社会・総合)",
        "url": "https://www.nhk.or.jp/rss/news/cat0.xml"
    },
    {
        "name": "NHK科学・医療 (創作のネタ)",
        "url": "https://www.nhk.or.jp/rss/news/cat3.xml"
    },
    {
        "name": "NHK文化・エンタメ (創作のネタ)",
        "url": "https://www.nhk.or.jp/rss/news/cat2.xml"
    },
    {
        "name": "はてなブックマーク (世論・ホットエントリ)",
        "url": "https://b.hatena.ne.jp/hotentry.rss"
    },
    {
        "name": "ITmedia (好奇心・IT総合)",
        "url": "https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml"
    }
]

# フィルタリングルール
EXCLUDE_KEYWORDS = ["生成AI", "Generative AI", "ChatGPT", "LLM", "Gemini", "AIチャット"]
HIGHLIGHT_KEYWORDS = ["岩手", "一関"]

# 出力ファイル名
OUTPUT_FILENAME = "index.html"

# ==========================================
# 2. クラス定義
# ==========================================

class NewsFilter:
    """記事のフィルタリングと加工を行うクラス"""
    
    @staticmethod
    def should_exclude(title):
        """指定されたキーワードが含まれる記事を除外するか判定"""
        for keyword in EXCLUDE_KEYWORDS:
            if keyword.lower() in title.lower():
                return True
        return False

    @staticmethod
    def highlight_title(title):
        """特定のキーワードが含まれる場合に強調表示を追加"""
        for keyword in HIGHLIGHT_KEYWORDS:
            if keyword in title:
                return f"【地元】 {title}"
        return title

class NewsFetcher:
    """RSSフィードの取得とパースを行うクラス"""
    
    def fetch_all(self):
        """全ての設定済みフィードを取得して整形されたデータを返す"""
        all_news = {}
        
        for config in FEED_CONFIGS:
            print(f"Fetching: {config['name']}...")
            try:
                feed = feedparser.parse(config['url'])
                articles = []
                
                if feed.bozo:
                    print(f"  Warning: {config['name']} のパース中にエラーが発生した可能性があります。")

                for entry in feed.entries:
                    title = entry.title
                    link = entry.link
                    
                    # 1. 除外フィルタ
                    if NewsFilter.should_exclude(title):
                        continue
                    
                    # 2. 強調フィルタ
                    display_title = NewsFilter.highlight_title(title)
                    
                    articles.append({
                        "title": display_title,
                        "url": link
                    })
                
                all_news[config['name']] = articles
                
            except Exception as e:
                print(f"  Error fetching {config['name']}: {e}")
                all_news[config['name']] = []
                
        return all_news

class NewsFormatter:
    """ニュースデータの出力形式を整形するクラス"""
    
    @staticmethod
    def generate_html(all_news):
        """HTML形式のレポートを作成"""
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily News Report</title>
    <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #333; }}
        h1 {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
        .timestamp {{ color: #666; font-size: 0.9em; margin-bottom: 30px; }}
        .section {{ margin-bottom: 40px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }}
        .section-header {{ background: #f4f4f4; padding: 10px 15px; font-weight: bold; font-size: 1.2em; border-bottom: 1px solid #ddd; }}
        ul {{ list-style-type: none; padding: 0; margin: 0; }}
        li {{ border-bottom: 1px solid #eee; }}
        li:last-child {{ border-bottom: none; }}
        a {{ display: block; padding: 12px 15px; text-decoration: none; color: #0066cc; transition: background 0.2s; }}
        a:hover {{ background: #f9f9f9; text-decoration: underline; }}
        .highlight {{ color: #e60000; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Daily News Report</h1>
    <p class="timestamp">更新日時: {now_str}</p>
"""
        
        for site_name, articles in all_news.items():
            html += f"""
    <div class="section">
        <div class="section-header">{site_name}</div>
        <ul>
"""
            if not articles:
                 html += '            <li style="padding: 15px; color: #999;">(記事なし、または取得エラー)</li>'
            
            for article in articles:
                title_html = article['title'].replace("【地元】", '<span class="highlight">【地元】</span>')
                html += f'            <li><a href="{article["url"]}" target="_blank">{title_html}</a></li>\n'
                
            html += """
        </ul>
    </div>
"""

        html += """
</body>
</html>
"""
        return html

# ==========================================
# 3. メイン処理
# ==========================================

def job():
    print(f"\n⏰ 実行を開始します: {datetime.datetime.now()}")
    
    fetcher = NewsFetcher()
    all_news = fetcher.fetch_all()
    
    formatter = NewsFormatter()
    html_content = formatter.generate_html(all_news)
    
    # コンソールには簡易表示（オプション）
    print(f"HTML生成完了。サイズ: {len(html_content)} bytes")
    
    # ファイル出力
    try:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n✅ HTMLレポートを保存しました: {os.path.abspath(OUTPUT_FILENAME)}")
    except Exception as e:
        print(f"\n❌ ファイル保存エラー: {e}")

if __name__ == "__main__":
    job()