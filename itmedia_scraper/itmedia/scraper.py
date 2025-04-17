"""
ITmedia AIスクレイパーのコアクラス
"""
import os
import time
import requests
from bs4 import BeautifulSoup
import logging
import json
import csv
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from urllib.parse import urljoin
from dotenv import load_dotenv

from itmedia.utils import (
    setup_logging, create_output_directory, limit_text, 
    extract_publication_date, get_recent_archive_months,
    save_progress, save_to_file
)
from itmedia.llm import summarize_with_llm, categorize_with_llm, extract_companies_with_llm
import openai

class ItmediaScraper:
    def __init__(self, base_url="https://www.itmedia.co.jp/aiplus/", delay=2, api_key=None, disable_llm=False, 
                 output_dir="output", log_level="INFO"):
        """Initialize the scraper with base URL and delay between requests"""
        self.base_url = base_url
        self.delay = delay  # Delay between requests in seconds
        self.scraped_urls = set()  # Track already scraped URLs
        self.disable_llm = disable_llm
        self.output_dir = output_dir
        
        # ログの設定
        self.logger = setup_logging(log_level)
        
        # 出力ディレクトリの作成
        self.output_dir, self.timestamp_dir = create_output_directory(output_dir)
        
        # ログファイル用のハンドラを追加
        log_file = os.path.join(self.timestamp_dir, "scraper.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        self.logger.info(f"Logging to file: {log_file}")
        
        # .envファイルからAPIキーを読み込む
        load_dotenv()
        
        # デフォルトのAPIキー（指定がない場合はこれを使用）
        self.api_key = api_key
        if not self.api_key and not self.disable_llm:
            # .envファイルからAPIキーを読み込む
            self.api_key = os.getenv("OPENAI_API_KEY")
            if self.api_key:
                self.logger.info("Using OpenAI API key from .env file")
            else:
                self.logger.warning("No OpenAI API key found in .env file. LLM features will be disabled.")
                self.disable_llm = True
        elif self.api_key:
            self.logger.info("Using provided OpenAI API key")
        else:
            self.logger.info("LLM summarization disabled")
        
        # カスタムカテゴリとキーワードの定義
        self.custom_categories = [
            "業務効率化・自動化", "研究動向", "市場・ビジネス動向", 
            "製品・サービス", "セキュリティ・倫理", "教育・人材育成",
            "AI技術基盤", "社会実装・応用", "政策・規制"
        ]
        
        # 各カテゴリのキーワード
        self.category_keywords = {
            "業務効率化・自動化": ["効率化", "自動化", "業務", "ワークフロー", "RPA", "生産性", "DX"],
            "研究動向": ["研究", "開発", "技術", "アルゴリズム", "論文", "モデル", "基盤モデル", "LLM"],
            "市場・ビジネス動向": ["市場", "ビジネス", "経済", "投資", "予測", "調査", "シェア", "売上"],
            "製品・サービス": ["製品", "サービス", "ツール", "アプリ", "リリース", "発表", "提供開始"],
            "セキュリティ・倫理": ["セキュリティ", "倫理", "プライバシー", "リスク", "規制", "ガイドライン"],
            "教育・人材育成": ["教育", "学習", "トレーニング", "スキル", "人材", "育成", "講座"],
            "AI技術基盤": ["GPU", "計算資源", "インフラ", "アーキテクチャ", "ハードウェア", "基盤技術"],
            "社会実装・応用": ["実装", "応用", "社会", "実用", "導入事例", "ユースケース", "活用事例"],
            "政策・規制": ["政策", "規制", "法律", "法令", "ガバナンス", "コンプライアンス", "国家戦略"]
        }
    
    def fetch_page(self, url):
        """Fetch a page and return its HTML content"""
        self.logger.debug(f"Fetching page: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers)
            response.encoding = 'shift_jis'  # Set encoding to Shift-JIS
            self.logger.debug(f"Successfully fetched page: {url} (Status: {response.status_code})")
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching page {url}: {e}")
            return None
    
    def parse_article_list(self, html_content):
        """Parse the article list page and extract article information"""
        if not html_content:
            self.logger.error("No HTML content to parse")
            return []
            
        self.logger.debug("Parsing article list page")
        soup = BeautifulSoup(html_content, 'lxml')
        articles = []
        
        # 記事要素を検索
        article_elements = soup.select('.colBoxIndex')
        self.logger.debug(f"Found {len(article_elements)} article elements")
        
        for article in article_elements:
            # タイトルとURLを抽出
            title_element = article.select_one('.colBoxTitle h3 a')
            if not title_element:
                self.logger.warning("Article element without title found, skipping")
                continue
                
            title = title_element.text.strip()
            url = title_element['href']
            if not url.startswith('http'):
                url = f"https://www.itmedia.co.jp{url}"
            
            # 既にスクレイピング済みのURLはスキップ
            if url in self.scraped_urls:
                self.logger.debug(f"Skipping already scraped URL: {url}")
                continue
                
            # スクレイピング済みURLセットに追加
            self.scraped_urls.add(url)
            
            # 記事オブジェクトを作成
            article_data = {
                'title': title,
                'url': url,
                'custom_category': self.determine_custom_category(title, "")
            }
            
            self.logger.debug(f"Added article: {title} ({url})")
            articles.append(article_data)
        
        self.logger.info(f"Parsed {len(articles)} unique articles from page")
        return articles
    
    def determine_custom_category(self, title, original_category, url=None):
        """
        記事のカテゴリを決定する
        
        Args:
            title: 記事のタイトル
            original_category: 元のカテゴリ（サイトから取得）
            url: 記事のURL（LLMによるカテゴリ分類に使用）
            
        Returns:
            カスタムカテゴリ
        """
        # LLMが有効で、URLが提供されている場合はLLMを使用してカテゴリを決定
        if not self.disable_llm and self.api_key and url:
            try:
                self.logger.info(f"Using LLM to categorize article: {title}")
                llm_category = categorize_with_llm(url, title, self.api_key, self.custom_categories)
                if llm_category:
                    self.logger.debug(f"LLM categorization result: {llm_category}")
                    return llm_category
            except Exception as e:
                self.logger.error(f"Error using LLM for categorization: {e}")
                self.logger.warning("Falling back to keyword-based categorization...")
        
        # LLMが無効または失敗した場合はキーワードベースの分類にフォールバック
        self.logger.debug("Using keyword-based categorization")
        title_lower = title.lower()
        
        # 各カテゴリのスコアを初期化
        scores = {category: 0 for category in self.custom_categories}
        
        # タイトル内のキーワードをチェック
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    scores[category] += 2  # タイトル一致はより重要
        
        # 最高スコアのカテゴリを取得
        max_score = max(scores.values())
        if max_score > 0:
            # 同点の場合、リスト内の最初のカテゴリを選択
            for category in self.custom_categories:
                if scores[category] == max_score:
                    return category
        
        # キーワードが一致しない場合のデフォルトカテゴリ
        return "研究動向"
    
    def fetch_article_content(self, url):
        """記事の全文を取得"""
        try:
            self.logger.info(f"Fetching content for: {url}")
            html_content = self.fetch_page(url)
            if not html_content:
                self.logger.error(f"Failed to fetch content for {url}")
                return {
                    'content': '',
                    'summary': '',
                    'companies': [],
                    'publication_date': ''
                }
                
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 記事本文を取得
            article_body = soup.find('div', class_='inner')
            if not article_body:
                self.logger.error(f"No article body found for {url}")
                return {
                    'content': '',
                    'summary': '',
                    'companies': [],
                    'publication_date': ''
                }
                
            # 不要な要素を削除
            for element in article_body.find_all(['script', 'style', 'iframe']):
                element.decompose()
                
            # テキストを抽出し、空白行を削除
            content_lines = [line.strip() for line in article_body.get_text().split('\n') if line.strip()]
            content = '\n'.join(content_lines)
            
            # 内容を要約（LLMが有効な場合）
            summary = ""
            companies = []
            if not self.disable_llm and self.api_key:
                title = soup.find('h1', class_='title').get_text().strip() if soup.find('h1', class_='title') else ""
                summary = summarize_with_llm(url, title, self.api_key)
                
                # 企業名を抽出
                companies = extract_companies_with_llm(content, title, self.api_key)
            
            # 投稿日時を抽出
            publication_date = extract_publication_date(soup, url)
            
            return {
                'content': content,
                'summary': summary,
                'companies': companies,
                'publication_date': publication_date
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching article content: {str(e)}")
            return {
                'content': '',
                'summary': '',
                'companies': [],
                'publication_date': ''
            }
    
    def scrape(self, num_pages=1, fetch_content=True, max_articles=0):
        """複数ページから記事をスクレイピング"""
        self.logger.info(f"Starting scraping of {num_pages} pages from {self.base_url}")
        all_articles = []
        
        for page in range(1, num_pages + 1):
            # ページURLを構築
            page_url = self.base_url if page == 1 else f"{self.base_url}?page={page}"
            self.logger.info(f"Scraping page {page}/{num_pages}: {page_url}")
            
            # ページを取得して解析
            html_content = self.fetch_page(page_url)
            if not html_content:
                self.logger.error(f"Failed to fetch page {page}, skipping")
                continue
                
            articles = self.parse_article_list(html_content)
            
            self.logger.info(f"Found {len(articles)} articles on page {page}")
            
            # 要求された場合、各記事の全文を取得
            if fetch_content:
                for i, article in enumerate(articles, 1):
                    self.logger.info(f"[{i}/{len(articles)}] Fetching content for: {article['title']}")
                    
                    # 記事コンテンツを取得
                    content_data = self.fetch_article_content(article['url'])
                    article.update(content_data)
                    
                    # 進行状況を表示
                    progress = (i / len(articles)) * 100
                    self.logger.info(f"Progress: {progress:.1f}% ({i}/{len(articles)})")
                    
                    # すべての記事に追加
                    all_articles.append(article)
                    
                    # リクエスト間の遅延（サーバーに配慮）
                    if i < len(articles):
                        self.logger.debug(f"Waiting {self.delay} seconds before next request")
                        time.sleep(self.delay)
            else:
                all_articles.extend(articles)
                
            # 最大記事数に達した場合、ループを終了
            if max_articles > 0 and len(all_articles) >= max_articles:
                self.logger.info(f"最大記事数 {max_articles} に達したため、スクレイピングを終了します")
                break
            
            # ページ間の遅延
            if page < num_pages:
                self.logger.debug(f"Waiting {self.delay} seconds before fetching next page")
                time.sleep(self.delay)
                
        self.logger.info(f"Total unique articles scraped: {len(all_articles)}")
        return all_articles
    
    def scrape_archive(self, archive_url, fetch_content=True, max_articles=0):
        """アーカイブページから記事をスクレイピング"""
        self.logger.info(f"Starting scraping of archive page: {archive_url}")
        all_articles = []
        
        # アーカイブページを取得して解析
        html_content = self.fetch_page(archive_url)
        if not html_content:
            self.logger.error(f"Failed to fetch archive page {archive_url}")
            return []
            
        # アーカイブページのHTMLを解析
        soup = BeautifulSoup(html_content, 'lxml')
        
        # ページが存在するか確認（エラーページの検出）
        error_title = soup.find('title')
        if error_title and "ページが見つかりませんでした" in error_title.text:
            self.logger.error(f"Archive page not found: {archive_url}")
            return []
        
        # アーカイブページでの記事要素を検索 - 日付ごとのセクションを探す
        date_sections = soup.select('div.colBoxSubhead h4')
        self.logger.debug(f"Found {len(date_sections)} date sections in archive")
        
        articles = []
        
        # 各日付セクションから記事を抽出
        for date_section in date_sections:
            date_text = date_section.text.strip()
            # 日付セクションの次の要素（記事リスト）を取得
            article_list_div = date_section.parent.find_next_sibling('div', class_='colBoxIndex')
            if not article_list_div:
                continue
                
            # 記事リストから各記事を抽出
            article_items = article_list_div.select('div.colBoxUlist ul li')
            self.logger.debug(f"Found {len(article_items)} articles for date {date_text}")
            
            for article_item in article_items:
                # 記事タイプを抽出（ニュース、解説など）
                article_type_elem = article_item.select_one('span.colBoxArticletype')
                article_type = article_type_elem.text.strip() if article_type_elem else ""
                
                # タイトルとURLを抽出
                title_elem = article_item.find('a')
                if not title_elem:
                    self.logger.warning(f"Article without title found in archive, skipping")
                    continue
                    
                title = title_elem.text.strip()
                url = title_elem['href']
                if not url.startswith('http'):
                    url = f"https://www.itmedia.co.jp{url}"
                
                # 著者情報を抽出
                author_elem = article_item.select_one('span.colBoxArticlewriter')
                author = author_elem.text.strip() if author_elem else ""
                
                # 公開日を抽出
                pub_date_elem = article_item.select_one('span.colBoxUlistDate')
                pub_date = pub_date_elem.text.strip() if pub_date_elem else date_text
                
                # 既にスクレイピング済みのURLはスキップ
                if url in self.scraped_urls:
                    self.logger.debug(f"Skipping already scraped URL: {url}")
                    continue
                    
                # スクレイピング済みURLセットに追加
                self.scraped_urls.add(url)
                
                # 記事オブジェクトを作成
                article_data = {
                    'title': title,
                    'url': url,
                    'article_type': article_type,
                    'author': author,
                    'publication_date_text': pub_date,
                    'archive_date_section': date_text,
                    'custom_category': self.determine_custom_category(title, ""),
                    'archive_source': archive_url
                }
                
                self.logger.debug(f"Added article from archive: {title} ({url})")
                articles.append(article_data)
                
                # 最大記事数に達した場合、ループを終了
                if max_articles > 0 and len(articles) >= max_articles:
                    self.logger.info(f"最大記事数 {max_articles} に達したため、スクレイピングを終了します")
                    break
            
            # 最大記事数に達した場合、ループを終了
            if max_articles > 0 and len(articles) >= max_articles:
                break
        
        self.logger.info(f"Parsed {len(articles)} unique articles from archive page")
        
        # 要求された場合、各記事の全文を取得
        if fetch_content and articles:
            for i, article in enumerate(articles, 1):
                self.logger.info(f"[{i}/{len(articles)}] Fetching content for archive article: {article['title']}")
                
                # 記事コンテンツを取得
                content_data = self.fetch_article_content(article['url'])
                article.update(content_data)
                
                # 進行状況を表示
                progress = (i / len(articles)) * 100
                self.logger.info(f"Progress: {progress:.1f}% ({i}/{len(articles)})")
                
                # すべての記事に追加
                all_articles.append(article)
                
                # リクエスト間の遅延（サーバーに配慮）
                if i < len(articles):
                    self.logger.debug(f"Waiting {self.delay} seconds before next request")
                    time.sleep(self.delay)
        else:
            all_articles.extend(articles)
            
        self.logger.info(f"Total unique articles scraped from archive: {len(all_articles)}")
        return all_articles
    
    def scrape_recent_archives(self, num_months=3, fetch_content=True, start_from_month=None, max_articles=0):
        """最近の複数月分のアーカイブページから記事をスクレイピング
        
        Args:
            num_months (int): スクレイピングする月数 (1〜12)
            fetch_content (bool): 記事の内容を取得するかどうか
            start_from_month (str): 特定の月から開始する場合、その月をYYMM形式で指定（例：2503）
            max_articles (int): 最大記事数
        """
        if num_months < 1:
            num_months = 1
        elif num_months > 12:
            num_months = 12
            self.logger.warning(f"Number of months limited to maximum of 12. Using num_months=12.")
            
        # start_from_monthが指定された場合、その月から始めて過去に向かってnum_months分取得
        if start_from_month:
            try:
                # start_from_monthの年月を解析
                year = 2000 + int(start_from_month[:2])
                month = int(start_from_month[2:])
                
                # 指定された月から生成
                archive_months = []
                current_date = datetime(year, month, 1)
                
                for i in range(num_months):
                    # 現在の月から過去i月分
                    past_date = current_date - relativedelta(months=i)
                    # YYMMフォーマットに変換
                    archive_month = past_date.strftime("%y%m")
                    archive_months.append(archive_month)
                
                self.logger.info(f"Generated {len(archive_months)} archive months starting from {start_from_month}: {', '.join(archive_months)}")
                self.logger.info(f"Starting from month {start_from_month}, processing {num_months} months")
            except (ValueError, IndexError):
                self.logger.warning(f"Invalid start_from_month format: {start_from_month}. Using current month instead.")
                archive_months = get_recent_archive_months(num_months)
        else:
            # 通常通り、現在の月から最近のnum_months分を取得
            self.logger.info(f"Starting to scrape the last {num_months} months of archives")
            archive_months = get_recent_archive_months(num_months)
        
        all_articles = []
        
        # 各月のアーカイブをスクレイピング
        for month in archive_months:
            try:
                archive_url = f"https://www.itmedia.co.jp/aiplus/subtop/archive/{month}.html"
                self.logger.info(f"Scraping archive for month {month}: {archive_url}")
                
                # アーカイブページをスクレイピング
                articles = self.scrape_archive(archive_url, fetch_content, max_articles)
                
                # 記事を全体のリストに追加
                all_articles.extend(articles)
                
                # 進捗状況を保存
                save_progress(self.timestamp_dir, month, len(all_articles))
                
            except Exception as e:
                self.logger.error(f"Error scraping month {month}: {str(e)}")
                self.logger.info(f"To resume from this point, use --start-from-month {month}")
                # エラーが発生しても続行
                continue
        
        self.logger.info(f"Total unique articles scraped from {len(archive_months)} recent archives: {len(all_articles)}")
        return all_articles
    
    def save_to_file(self, articles, output_file=None, format='json'):
        """記事データをJSONとCSVファイルに保存"""
        return save_to_file(articles, self.timestamp_dir, output_file, format)
