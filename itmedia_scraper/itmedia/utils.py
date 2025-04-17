"""
ユーティリティ関数モジュール
"""
import re
import os
import json
import csv
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

logger = logging.getLogger("ItmediaScraper")

def setup_logging(log_level="INFO", output_dir=None, timestamp_dir=None):
    """ロギングの設定
    
    Args:
        log_level: ログレベル
        output_dir: 出力ディレクトリ
        timestamp_dir: タイムスタンプディレクトリ
    
    Returns:
        logger: 設定されたロガー
    """
    import logging
    import sys
    
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
    logger = logging.getLogger("ItmediaScraper")
    logger.setLevel(level)
    
    # 既存のハンドラをクリア
    if logger.handlers:
        logger.handlers.clear()
    
    # コンソール出力用ハンドラ
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # フォーマットの設定
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # ハンドラの追加
    logger.addHandler(console_handler)
    
    # ログファイル用のハンドラを追加（タイムスタンプディレクトリが指定されている場合）
    if timestamp_dir:
        log_file = os.path.join(timestamp_dir, "scraper.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_file}")
    
    logger.debug("Logging initialized at level: %s", log_level)
    return logger

def create_output_directory(output_dir="output"):
    """出力ディレクトリの作成
    
    Args:
        output_dir: 出力ディレクトリパス
    
    Returns:
        tuple: (output_dir, timestamp_dir)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
    else:
        logger.debug(f"Output directory already exists: {output_dir}")
    
    # 現在の日時でタイムスタンプディレクトリを作成
    timestamp_dir = os.path.join(output_dir, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(timestamp_dir, exist_ok=True)
    logger.info(f"Created timestamp directory: {timestamp_dir}")
    
    return output_dir, timestamp_dir

def limit_text(text, max_length):
    """テキストを指定された最大長に制限
    
    Args:
        text: 制限するテキスト
        max_length: 最大文字数
    
    Returns:
        str: 制限されたテキスト
    """
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

def extract_publication_date(soup, url):
    """記事ページから公開日を抽出
    
    Args:
        soup: BeautifulSoupオブジェクト
        url: 記事のURL
    
    Returns:
        str: 公開日（YYYY-MM-DD形式）
    """
    # 1. 標準の公開日要素を探す（最も一般的なパターン）
    date_element = soup.select_one('.publish')
    if date_element:
        date_text = date_element.text.strip()
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 2. 別の公開日要素パターンを探す（ITmediaの別レイアウト用）
    date_element = soup.select_one('.update')
    if date_element:
        date_text = date_element.text.strip()
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 3. 記事ヘッダー内の日付要素を探す
    date_element = soup.select_one('.head_info_date')
    if date_element:
        date_text = date_element.text.strip()
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 4. メタタグを確認（OGPタグ）
    meta_time = soup.select_one('meta[property="article:published_time"]')
    if meta_time and meta_time.get('content'):
        date_str = meta_time.get('content')
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if match:
            return match.group(0)
    
    # 5. 別のメタタグパターンを確認
    meta_date = soup.select_one('meta[name="pubdate"]')
    if meta_date and meta_date.get('content'):
        date_str = meta_date.get('content')
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if match:
            return match.group(0)
    
    # 6. 記事本文内の日付表記を探す
    article_body = soup.select_one('#cmsBody')
    if article_body:
        date_text = article_body.text[:200]  # 最初の200文字だけ検索
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 7. URLから抽出を試みる（最後の手段）
    match = re.search(r'/(\d{2})(\d{2})/(\d{2})/', url)
    if match:
        yy, mm, dd = match.groups()
        year = f"20{yy}"  # 21世紀と仮定
        return f"{year}-{mm}-{dd}"
    
    # 8. 別のURL形式を試す
    match = re.search(r'(\d{4})(\d{2})(\d{2})', url)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
            
    return ""

def get_recent_archive_months(num_months=3):
    """最近の月のアーカイブURLを生成する（現在の月を含む）
    
    Args:
        num_months: 取得する月数
    
    Returns:
        list: アーカイブ月のリスト（YYMM形式）
    """
    if num_months < 1:
        num_months = 1
    elif num_months > 12:
        num_months = 12
        logger.warning(f"Number of months limited to maximum of 12. Using num_months=12.")
        
    current_date = datetime.now()
    archive_months = []
    
    for i in range(num_months):
        # i ヶ月前の日付を計算
        past_date = current_date - relativedelta(months=i)
        # YYMMフォーマットに変換
        archive_month = past_date.strftime("%y%m")
        archive_months.append(archive_month)
        
    logger.info(f"Generated {len(archive_months)} recent archive months: {', '.join(archive_months)}")
    return archive_months

def save_progress(timestamp_dir, current_month, num_articles):
    """スクレイピングの進捗状況を保存
    
    Args:
        timestamp_dir: タイムスタンプディレクトリ
        current_month: 現在処理中の月
        num_articles: スクレイピングした記事数
    """
    progress_file = os.path.join(timestamp_dir, "scraping_progress.json")
    progress_data = {
        "last_month_scraped": current_month,
        "articles_scraped": num_articles,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
    logger.debug(f"Saved progress: Month {current_month}, {num_articles} articles scraped")

def save_to_file(articles, timestamp_dir, output_file=None, format='json'):
    """記事データをJSONとCSVファイルに保存
    
    Args:
        articles: 記事データのリスト
        timestamp_dir: タイムスタンプディレクトリ
        output_file: 出力ファイル名
        format: 出力形式（json/csv）
    
    Returns:
        list: 保存されたファイルのパスのリスト
    """
    if not articles:
        logger.warning("No articles to save.")
        return None
    
    # タイムスタンプ付きのデフォルトファイル名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 出力ファイル名の設定
    if not output_file:
        json_filename = f"itmedia_articles_{timestamp}.json"
        csv_filename = f"itmedia_articles_{timestamp}.csv"
        json_output_file = os.path.join(timestamp_dir, json_filename)
        csv_output_file = os.path.join(timestamp_dir, csv_filename)
    else:
        # 拡張子を取り除いたベース名を取得
        base_name = os.path.splitext(output_file)[0]
        # 絶対パスでない場合は出力ディレクトリに配置
        if not os.path.isabs(output_file):
            json_output_file = os.path.join(timestamp_dir, f"{base_name}.json")
            csv_output_file = os.path.join(timestamp_dir, f"{base_name}.csv")
        else:
            output_dir = os.path.dirname(output_file)
            base_filename = os.path.basename(base_name)
            json_output_file = os.path.join(output_dir, f"{base_filename}.json")
            csv_output_file = os.path.join(output_dir, f"{base_filename}.csv")
            
    # 出力ディレクトリが存在することを確認
    output_dir = os.path.dirname(json_output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.debug(f"Created directory for output file: {output_dir}")
        
    saved_files = []
    
    # JSONファイルに保存
    logger.info(f"Saving {len(articles)} articles to {json_output_file}")
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved JSON data to {json_output_file}")
    saved_files.append(json_output_file)
    
    # CSVファイルに保存
    logger.info(f"Saving {len(articles)} articles to {csv_output_file}")
    # 読みやすさのための列の順序を定義
    fieldnames = [
        'title', 'url', 'custom_category', 'publication_date', 'summary', 'companies'
    ]
    
    # CSV用に記事データをコピーして加工
    csv_articles = []
    for article in articles:
        # 記事データをコピー
        csv_article = article.copy()
        
        # 不要なフィールドを削除（指定された要件）
        fields_to_remove = ['publication_date_text',
                           'archive_date_section', 'author', 'archive_source',
                           'article_type', 'content']
        for field in fields_to_remove:
            if field in csv_article:
                del csv_article[field]
                
        # すべてのフィールドがあることを確認
        for field in fieldnames:
            if field not in csv_article:
                csv_article[field] = ""
                
        # companiesフィールドが存在し、リストの場合は文字列に変換
        if 'companies' in csv_article and isinstance(csv_article['companies'], list):
            # カギカッコを削除して文字列に変換
            companies = [company.strip('[]「」') for company in csv_article['companies']]
            csv_article['companies'] = ', '.join(companies)
                
        csv_articles.append(csv_article)
    
    with open(csv_output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_articles)
        logger.debug(f"Saved CSV data to {csv_output_file}")
    saved_files.append(csv_output_file)
    
    logger.info(f"Successfully saved {len(articles)} articles to JSON and CSV formats")
    return saved_files
