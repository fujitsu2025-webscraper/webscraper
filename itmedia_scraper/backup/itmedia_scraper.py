import requests
from bs4 import BeautifulSoup
import json
import csv
import os
import time
import re
from datetime import datetime
import argparse
import openai
import logging
import sys
from dateutil.relativedelta import relativedelta
from urllib.parse import urljoin
from dotenv import load_dotenv

# .envファイルをロード
load_dotenv()

class ItmediaScraper:
    def __init__(self, base_url="https://www.itmedia.co.jp/aiplus/", delay=2, api_key=None, disable_llm=False, 
                 output_dir="output", log_level="INFO"):
        """Initialize the scraper with base URL and delay between requests"""
        self.base_url = base_url
        self.delay = delay  # Delay between requests in seconds
        self.scraped_urls = set()  # Track already scraped URLs
        self.disable_llm = disable_llm
        self.output_dir = output_dir
        self.timestamp_dir = os.path.join(output_dir, datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(self.timestamp_dir, exist_ok=True)
        
        # ログの設定
        self.setup_logging(log_level)
        
        # 出力ディレクトリの作成
        self.create_output_directory()
        
        # APIキーの設定 (環境変数から取得)
        self.api_key = api_key if api_key else os.getenv("OPENAI_API_KEY")

        if not self.disable_llm:
            if self.api_key:
                self.logger.info("OpenAI APIキーを環境変数から読み込みました。")
                # ここでOpenAIクライアントの初期化などを行う場合は self.api_key を使う
                try:
                    openai.api_key = self.api_key
                    # 必要であればここでクライアントを初期化
                    # self.openai_client = openai.OpenAI() # 例
                    self.logger.info("OpenAIクライアントを初期化しました。")
                except Exception as e:
                    self.logger.error(f"OpenAIクライアントの初期化中にエラー: {e}")
                    self.api_key = None # 初期化失敗時はキーをNoneに
            else:
                self.logger.warning("OPENAI_API_KEYが環境変数に設定されていません。LLM機能は無効になります。")
                self.disable_llm = True # APIキーがない場合はLLMを無効化
        else:
            self.logger.info("LLM機能は無効化されています。")
        
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
    
    def setup_logging(self, log_level="INFO"):
        """ロギングの設定"""
        # ログレベルの設定
        log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        level = log_levels.get(log_level.upper(), logging.INFO)
        
        # ロガーの設定
        self.logger = logging.getLogger("ItmediaScraper")
        self.logger.setLevel(level)
        
        # 既存のハンドラをクリア
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # コンソール出力用ハンドラ
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # フォーマットの設定
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # ハンドラの追加
        self.logger.addHandler(console_handler)
        
        self.logger.debug("Logging initialized at level: %s", log_level)
    
    def create_output_directory(self):
        """出力ディレクトリの作成"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"Created output directory: {self.output_dir}")
        else:
            self.logger.debug(f"Output directory already exists: {self.output_dir}")
        
        # 現在の日時でタイムスタンプディレクトリを作成
        self.logger.info(f"Created timestamp directory: {self.timestamp_dir}")
        
        # ログファイル用のハンドラを追加
        log_file = os.path.join(self.timestamp_dir, "scraper.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        self.logger.info(f"Logging to file: {log_file}")
    
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
                llm_category = self.categorize_with_llm(url, title)
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
        self.logger.info(f"Fetching content for: {url}")
        html_content = self.fetch_page(url)
        
        if not html_content:
            self.logger.error(f"Failed to fetch content for {url}")
            return {
                'publication_date': '',
                'content': ''
            }
            
        soup = BeautifulSoup(html_content, 'lxml')
        
        # LLM要約用のタイトルを取得
        title_element = soup.select_one('h1.title')
        title = title_element.text.strip() if title_element else ""
        
        # 公開日を抽出（HTMLから常に必要）
        publication_date = self._extract_publication_date(soup, url)
        self.logger.debug(f"Extracted publication date: {publication_date}")
        
        # APIキーが利用可能でLLMが無効化されていない場合、URLベースでLLMを使用して要約
        if self.api_key and not self.disable_llm:
            try:
                self.logger.info(f"Using LLM to summarize URL: {url}")
                llm_result = self.summarize_with_llm(url, title)
                if llm_result:
                    self.logger.debug("LLM summarization successful")
                    return {
                        'publication_date': publication_date,
                        'content': llm_result['content'],
                        'companies': llm_result['companies']
                    }
            except Exception as e:
                self.logger.error(f"Error using OpenAI API: {e}")
                self.logger.warning("Falling back to basic text extraction...")
        
        # LLM要約が失敗した場合や無効の場合は基本的なテキスト抽出にフォールバック
        self.logger.info("Using basic text extraction for content")
        content_element = soup.select_one('#cmsBody')
        full_content = content_element.text.strip() if content_element else ""
        
        # コンテンツを約500文字に制限
        content = self._limit_text(full_content, 500)
        
        self.logger.debug(f"Extracted content length: {len(content)}")
        return {
            'publication_date': publication_date,
            'content': content,
            'companies': ""
        }
    
    def _limit_text(self, text, max_length):
        """テキストを指定された最大長に制限"""
        if not text:
            return ""
            
        result = ""
        sentences = re.split(r'(?<=[。！？])', text)
        for sentence in sentences:
            if len(result) + len(sentence) <= max_length:
                result += sentence
            else:
                # 制限に近い場合、部分的な文を省略記号付きで追加
                remaining_chars = max_length - len(result)
                if remaining_chars > 30:  # 意味のあるチャンクを取得できる場合のみ部分追加
                    result += sentence[:remaining_chars] + "..."
                break
        return result
        
    def _extract_publication_date(self, soup, url):
        """記事ページから公開日を抽出"""
        # 標準の公開日要素を探す
        date_element = soup.select_one('.publish')
        if date_element:
            date_text = date_element.text.strip()
            match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
            if match:
                year, month, day = match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # メタタグを確認
        meta_time = soup.select_one('meta[property="article:published_time"]')
        if meta_time and meta_time.get('content'):
            date_str = meta_time.get('content')
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
            if match:
                return match.group(0)
        
        # URLから抽出を試みる
        match = re.search(r'/(\d{2})(\d{2})/(\d{2})/', url)
        if match:
            yy, mm, dd = match.groups()
            year = f"20{yy}"  # 21世紀と仮定
            return f"{year}-{mm}-{dd}"
                
        return ""
    
    def summarize_with_llm(self, url, title):
        """
        OpenAIのAPIを使用してURLから内容を要約し、企業名を抽出
        LLMは直接URLにアクセスして内容を読み取り要約する
        """
        if not self.api_key or self.disable_llm:
            return None
            
        try:
            # LLM用のプロンプトを作成
            prompt = f"""
            以下のURLにアクセスして、記事を要約し、言及されている企業名を抽出してください:
            
            タイトル: {title}
            URL: {url}
            
            URLにアクセスして記事を読んでください。
            記事が日本語の場合は、日本語で要約してください。
            
            次の2つの情報を提供してください:
            
            1. 要約: 500文字程度の詳細な要約
            
            2. 企業名: 記事内で言及されているすべての企業名を抽出してください
               - 企業名とは、法人企業、組織、団体、スタートアップ、テクノロジー企業、政府機関などを指します
               - 製品名やサービス名だけでなく、それを提供している企業名を抽出してください
               - 例えば「ChatGPT」ではなく「OpenAI」、「Windows」ではなく「Microsoft」のように
               - 日本企業の場合は正式名称を使用してください（例：「トヨタ自動車」「ソニーグループ」「KDDI」など）
               - 企業の略称と正式名称の両方が記事に出てくる場合は、正式名称を優先してください
               - 企業名が記事内に明示されていない場合は「該当なし」と記入してください
               - 企業名の前に記号や番号は付けないでください
               - 各企業名は改行で区切ってください
               - 同じ企業名は1回だけ記載してください（重複しないように）
            
            出力形式:
            要約: [要約内容]
            
            企業名:
            [企業名1]
            [企業名2]
            ...
            
            企業名が存在しない場合は:
            企業名:
            該当なし
            """
            
            # OpenAI APIを呼び出し
            client = openai.OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは日本のAIとテクノロジーに関するニュース記事を要約し、企業名を抽出する専門家です。URLにアクセスして記事を読み、要約と企業名抽出ができます。企業名は正確に抽出し、余分な記号や説明は付けないでください。日本企業と外国企業の両方を認識できます。企業名は必ず抽出し、「該当なし」と判断するのは企業名が本当に存在しない場合のみにしてください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # レスポンステキストを抽出
            response_text = response.choices[0].message.content.strip()
            
            # 要約と企業名を分離
            content = ""
            companies = ""
            
            # 要約部分を抽出
            summary_match = re.search(r'要約:(.*?)(?=企業名:|$)', response_text, re.DOTALL)
            if summary_match:
                content = summary_match.group(1).strip()
            
            # 企業名部分を抽出
            companies_match = re.search(r'企業名:(.*?)$', response_text, re.DOTALL)
            if companies_match:
                companies_text = companies_match.group(1).strip()
                
                # 企業名の後処理
                if companies_text and companies_text.lower() != "該当なし":
                    # 行ごとに分割
                    company_lines = companies_text.split('\n')
                    
                    # 各行を処理
                    cleaned_companies = []
                    for line in company_lines:
                        # 空行をスキップ
                        if not line.strip():
                            continue
                            
                        # 先頭の記号や番号を削除（例: "- ", "1. ", "• "など）
                        cleaned_line = re.sub(r'^[-•*#\d\s\.]+\s*', '', line.strip())
                        
                        # 空でなければリストに追加
                        if cleaned_line:
                            cleaned_companies.append(cleaned_line)
                    
                    # 改行で結合
                    companies = '\n'.join(cleaned_companies) if cleaned_companies else ""
            
            self.logger.debug(f"Extracted content length: {len(content)}")
            self.logger.debug(f"Extracted companies: {companies}")
                
            return {
                'content': content,
                'companies': companies
            }
            
        except Exception as e:
            self.logger.error(f"Error using OpenAI API: {e}")
            return None
    
    def categorize_with_llm(self, url, title):
        """
        OpenAIのAPIを使用してURLから記事のカテゴリを決定する
        
        Args:
            url: 記事のURL
            title: 記事のタイトル
            
        Returns:
            カスタムカテゴリ
        """
        if not self.api_key or self.disable_llm:
            return None
            
        try:
            # LLM用のプロンプトを作成
            prompt = f"""
            以下のURLにアクセスして、記事を読み、最も適切なカテゴリを1つだけ選んでください:
            
            タイトル: {title}
            URL: {url}
            
            選択肢:
            1. 業務効率化・自動化 (Business Efficiency/Automation): 企業や組織におけるAI活用、業務プロセスの効率化、自動化に関する内容
            2. 研究動向 (Research Trends): AI研究、論文、新しいアルゴリズム、モデル開発などの学術的・技術的進展
            3. 市場・ビジネス動向 (Market/Business Trends): AI市場の動向、企業戦略、投資、経済的影響に関する内容
            4. 製品・サービス (Products/Services): 新しいAI製品やサービスの発表、リリース、機能に関する内容
            5. セキュリティ・倫理 (Security/Ethics): AIのセキュリティリスク、倫理的問題、プライバシー、バイアスなどに関する内容
            6. 教育・人材育成 (Education/Human Resources): AI教育、スキル開発、人材育成、トレーニングに関する内容
            7. AI技術基盤 (AI Infrastructure): GPU、計算資源、ハードウェア、基盤技術、アーキテクチャに関する内容
            8. 社会実装・応用 (Social Implementation): AIの実社会での応用事例、導入事例、ユースケースに関する内容
            9. 政策・規制 (Policy/Regulation): AI関連の政策、法規制、ガバナンス、国家戦略に関する内容
            
            URLにアクセスして記事を読み、上記のカテゴリから最も適切なものを1つだけ選んでください。
            回答は選択したカテゴリの日本語名のみをお願いします。例: 「業務効率化・自動化」
            """
            
            # OpenAI APIを呼び出し
            client = openai.OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは日本のAIとテクノロジーに関するニュース記事を分類する専門家です。URLにアクセスして記事を読み、最適なカテゴリを選択することができます。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.2
            )
            
            # レスポンステキストを抽出
            category = response.choices[0].message.content.strip()
            
            # カテゴリが有効かどうかを確認
            for valid_category in self.custom_categories:
                if valid_category in category:
                    return valid_category
            
            # 有効なカテゴリが見つからない場合はデフォルトを返す
            self.logger.warning(f"LLM returned invalid category: {category}. Using default.")
            return "研究動向"
            
        except Exception as e:
            self.logger.error(f"Error in LLM categorization: {str(e)}")
            return None
    
    def scrape(self, num_pages=1, fetch_content=True):
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
                
            # ページ間の遅延
            if page < num_pages:
                self.logger.debug(f"Waiting {self.delay} seconds before fetching next page")
                time.sleep(self.delay)
                
        self.logger.info(f"Total unique articles scraped: {len(all_articles)}")
        return all_articles
    
    def scrape_archive(self, archive_url, fetch_content=True):
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
                    self.logger.warning(f"Article without title found in date section {date_text}, skipping")
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
    
    def get_recent_archive_months(self, num_months=3):
        """最近の月のアーカイブURLを生成する（現在の月を含む）"""
        if num_months < 1:
            num_months = 1
        elif num_months > 12:
            num_months = 12
            self.logger.warning(f"Number of months limited to maximum of 12. Using num_months=12.")
            
        current_date = datetime.now()
        archive_months = []
        
        for i in range(num_months):
            # i ヶ月前の日付を計算
            past_date = current_date - relativedelta(months=i)
            # YYMMフォーマットに変換
            archive_month = past_date.strftime("%y%m")
            archive_months.append(archive_month)
            
        self.logger.info(f"Generated {len(archive_months)} recent archive months: {', '.join(archive_months)}")
        return archive_months
    
    def scrape_recent_archives(self, num_months=3, fetch_content=True, start_from_month=None):
        """最近の複数月分のアーカイブページから記事をスクレイピング
        
        Args:
            num_months (int): スクレイピングする月数 (1〜12)
            fetch_content (bool): 記事の内容を取得するかどうか
            start_from_month (str): 特定の月から開始する場合、その月をYYMM形式で指定（例：2503）
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
                archive_months = self.get_recent_archive_months(num_months)
        else:
            # 通常通り、現在の月から最近のnum_months分を取得
            self.logger.info(f"Starting to scrape the last {num_months} months of archives")
            archive_months = self.get_recent_archive_months(num_months)
        
        all_articles = []
        
        # 各月のアーカイブをスクレイピング
        for month in archive_months:
            try:
                archive_url = f"https://www.itmedia.co.jp/aiplus/subtop/archive/{month}.html"
                self.logger.info(f"Scraping archive for month {month}: {archive_url}")
                
                # アーカイブページをスクレイピング
                articles = self.scrape_archive(archive_url, fetch_content)
                
                # 記事を全体のリストに追加
                all_articles.extend(articles)
                
                # 進捗状況を保存
                self._save_progress(month, len(all_articles))
                
            except Exception as e:
                self.logger.error(f"Error scraping month {month}: {str(e)}")
                self.logger.info(f"To resume from this point, use --start-from-month {month}")
                # エラーが発生しても続行
                continue
        
        self.logger.info(f"Total unique articles scraped from {len(archive_months)} recent archives: {len(all_articles)}")
        return all_articles
    
    def _save_progress(self, current_month, num_articles):
        """スクレイピングの進捗状況を保存"""
        progress_file = os.path.join(self.timestamp_dir, "scraping_progress.json")
        progress_data = {
            "last_month_scraped": current_month,
            "articles_scraped": num_articles,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
        self.logger.debug(f"Saved progress: Month {current_month}, {num_articles} articles scraped")
    
    def save_to_file(self, articles, output_file=None, format='json'):
        """記事データをJSONとCSVファイルに保存"""
        if not articles:
            self.logger.warning("No articles to save.")
            return None
        
        # タイムスタンプ付きのデフォルトファイル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 出力ファイル名の設定
        if not output_file:
            json_filename = f"itmedia_articles_{timestamp}.json"
            csv_filename = f"itmedia_articles_{timestamp}.csv"
            json_output_file = os.path.join(self.timestamp_dir, json_filename)
            csv_output_file = os.path.join(self.timestamp_dir, csv_filename)
        else:
            # 拡張子を取り除いたベース名を取得
            base_name = os.path.splitext(output_file)[0]
            # 絶対パスでない場合は出力ディレクトリに配置
            if not os.path.isabs(output_file):
                json_output_file = os.path.join(self.timestamp_dir, f"{base_name}.json")
                csv_output_file = os.path.join(self.timestamp_dir, f"{base_name}.csv")
            else:
                output_dir = os.path.dirname(output_file)
                base_filename = os.path.basename(base_name)
                json_output_file = os.path.join(output_dir, f"{base_filename}.json")
                csv_output_file = os.path.join(output_dir, f"{base_filename}.csv")
                
        # 出力ディレクトリが存在することを確認
        output_dir = os.path.dirname(json_output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            self.logger.debug(f"Created directory for output file: {output_dir}")
            
        saved_files = []
        
        # JSONファイルに保存
        self.logger.info(f"Saving {len(articles)} articles to {json_output_file}")
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"Saved JSON data to {json_output_file}")
        saved_files.append(json_output_file)
        
        # CSVファイルに保存
        self.logger.info(f"Saving {len(articles)} articles to {csv_output_file}")
        # 読みやすさのための列の順序を定義
        fieldnames = [
            'title', 'url', 'custom_category', 'content', 'companies'
        ]
        
        # CSV用に記事データをコピーして加工
        csv_articles = []
        for article in articles:
            # 記事データをコピー
            csv_article = article.copy()
            
            # 不要なフィールドを削除（指定された要件）
            fields_to_remove = ['publication_date', 'publication_date_text', 
                               'archive_date_section', 'author', 'archive_source',
                               'article_type']
            for field in fields_to_remove:
                if field in csv_article:
                    del csv_article[field]
                    
            # すべてのフィールドがあることを確認
            for field in fieldnames:
                if field not in csv_article:
                    csv_article[field] = ""
                    
            csv_articles.append(csv_article)
        
        with open(csv_output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_articles)
            self.logger.debug(f"Saved CSV data to {csv_output_file}")
        saved_files.append(csv_output_file)
        
        self.logger.info(f"Successfully saved {len(articles)} articles to JSON and CSV formats")
        return saved_files

def main():
    parser = argparse.ArgumentParser(description='Scrape articles from ITmedia AI')
    parser.add_argument('--pages', type=int, default=1, help='Number of pages to scrape')
    parser.add_argument('--delay', type=int, default=2, help='Delay between requests in seconds')
    parser.add_argument('--output', type=str, help='Output file path (without extension, both .json and .csv will be added)')
    parser.add_argument('--metadata-only', action='store_true', help='Only scrape metadata, not full content')
    parser.add_argument('--keyword', type=str, help='Filter articles by keyword')
    parser.add_argument('--category', type=str, help='Filter articles by category')
    parser.add_argument('--openai-api-key', type=str, help='OpenAI API key for content summarization (optional, default key is embedded)')
    parser.add_argument('--disable-llm', action='store_true', help='Disable LLM summarization and use basic text extraction')
    parser.add_argument('--output-dir', type=str, default='output', help='Directory to save output files')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                        default='INFO', help='Logging level')
    parser.add_argument('--archive', type=str, help='Scrape a specific archive page (e.g., https://www.itmedia.co.jp/aiplus/subtop/archive/2503.html)')
    parser.add_argument('--archive-month', type=str, help='Scrape a specific month archive (format: YYMM e.g., 2503 for March 2025)')
    parser.add_argument('--recent-archives', type=int, help='Scrape the last N months of archives (default: 3, max: 12)')
    parser.add_argument('--start-from-month', type=str, help='Resume scraping from a specific month (format: YYMM e.g., 2503 for March 2025)')

    args = parser.parse_args()
    
    # Create scraper with API key if provided, otherwise use default
    scraper = ItmediaScraper(
        delay=args.delay, 
        api_key=args.openai_api_key, 
        disable_llm=args.disable_llm,
        output_dir=args.output_dir,
        log_level=args.log_level
    )
    
    scraper.logger.info("Starting to scrape ITmedia AI...")
    
    # 開始時間を記録
    start_time = time.time()
    
    all_articles = []
    
    # アーカイブページのスクレイピング
    if args.archive:
        scraper.logger.info(f"Scraping archive page: {args.archive}")
        all_articles = scraper.scrape_archive(
            archive_url=args.archive,
            fetch_content=not args.metadata_only
        )
    # 月別アーカイブのスクレイピング
    elif args.archive_month:
        archive_url = f"https://www.itmedia.co.jp/aiplus/subtop/archive/{args.archive_month}.html"
        scraper.logger.info(f"Scraping monthly archive: {archive_url}")
        all_articles = scraper.scrape_archive(
            archive_url=archive_url,
            fetch_content=not args.metadata_only
        )
    # 直近の数ヶ月分のアーカイブをスクレイピング
    elif args.recent_archives:
        num_months = args.recent_archives if args.recent_archives > 0 else 3
        if num_months > 12:
            num_months = 12
            scraper.logger.warning(f"Number of months limited to maximum of 12. Using num_months=12.")
        scraper.logger.info(f"Scraping the last {num_months} months of archives")
        all_articles = scraper.scrape_recent_archives(num_months, fetch_content=not args.metadata_only, start_from_month=args.start_from_month)
    # 通常の記事一覧ページのスクレイピング
    else:
        scraper.logger.info(f"Target: {scraper.base_url}")
        scraper.logger.info(f"Pages to scrape: {args.pages}")
        all_articles = scraper.scrape(
            num_pages=args.pages,
            fetch_content=not args.metadata_only
        )
    
    scraper.logger.info(f"Delay between requests: {args.delay} seconds")
    scraper.logger.info(f"Mode: {'Metadata only' if args.metadata_only else 'Full content (fetching article content)'}")
    if scraper.api_key and not scraper.disable_llm:
        scraper.logger.info("Using OpenAI API for URL-based content summarization")
    else:
        scraper.logger.info("Using basic text extraction for summarization")
    
    scraper.logger.info("-" * 50)
    
    # Apply filters if specified
    if args.keyword:
        scraper.logger.info(f"Filtering articles by keyword: '{args.keyword}'")
        all_articles = [a for a in all_articles if args.keyword.lower() in a.get('title', '').lower() or 
                                                  args.keyword.lower() in a.get('content', '').lower()]
        scraper.logger.info(f"Filtered to {len(all_articles)} articles containing keyword '{args.keyword}'")
    
    if args.category:
        scraper.logger.info(f"Filtering articles by category: '{args.category}'")
        all_articles = [a for a in all_articles if args.category.lower() in a.get('custom_category', '').lower()]
        scraper.logger.info(f"Filtered to {len(all_articles)} articles in category '{args.category}'")
    
    # Save to file (both JSON and CSV)
    output_files = scraper.save_to_file(all_articles, args.output)
    
    if output_files:
        scraper.logger.info("\nScraping completed!")
        scraper.logger.info(f"Total articles scraped: {len(all_articles)}")
        scraper.logger.info(f"Data saved to: {', '.join(output_files)}")
        scraper.logger.info(f"Total execution time: {time.time() - start_time:.2f} seconds")
        
        if all_articles:
            scraper.logger.info("\nSample of first article:")
            for key in ['title', 'url', 'custom_category']:
                if key in all_articles[0]:
                    scraper.logger.info(f"{key}: {all_articles[0][key]}")
    else:
        scraper.logger.warning("No data was saved.")

if __name__ == "__main__":
    main()
