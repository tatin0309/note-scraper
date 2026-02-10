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
        "name": "NHK科学・文化 (創作のネタ)",
        "url": "https://www.nhk.or.jp/rss/news/cat7.xml"
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
OUTPUT_FILENAME = "news_report.txt"

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
    def format_text(all_news):
        """テキスト形式のレポートを作成"""
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = []
        lines.append("==================================================")
        lines.append(f"              Daily News Report                   ")
        lines.append(f"          {now_str}                       ")
        lines.append("==================================================")
        lines.append("")
        
        for site_name, articles in all_news.items():
            lines.append("--------------------------------------------------")
            lines.append(f"【{site_name}】")
            lines.append("--------------------------------------------------")
            
            if not articles:
                lines.append("  (記事なし、またはエラー)")
            
            for article in articles:
                lines.append(f"・{article['title']}")
                lines.append(f"  {article['url']}")
            
            lines.append("") # 空行
            
        return "\n".join(lines)

# ==========================================
# 3. メイン処理
# ==========================================

def job():
    print(f"\n⏰ 定時実行を開始します: {datetime.datetime.now()}")
    
    fetcher = NewsFetcher()
    all_news = fetcher.fetch_all()
    
    formatter = NewsFormatter()
    report_text = formatter.format_text(all_news)
    
    # コンソール出力
    print("\n" + report_text)
    
    # ファイル出力 (追記モードではなく上書きモードで最新の状態を保持)
    # 必要であればファイル名に日時を含めることも可能
    try:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"\n✅ レポートを保存しました: {os.path.abspath(OUTPUT_FILENAME)}")
    except Exception as e:
        print(f"\n❌ ファイル保存エラー: {e}")

if __name__ == "__main__":
    job()