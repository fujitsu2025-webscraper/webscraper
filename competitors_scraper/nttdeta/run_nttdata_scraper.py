"""
NTTデータの事例ページをスクレイピングするためのメインスクリプト
"""
import os
import sys
import time
import json
import logging
import datetime
import argparse
from pathlib import Path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import traceback

# 親ディレクトリをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# .envファイルを読み込む
load_dotenv()

# ロガーの設定
def setup_logger():
    """ロガーを設定する"""
    logger = logging.getLogger("nttdata_scraper")
    logger.setLevel(logging.INFO)
    
    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # ロガーにハンドラを追加
    logger.addHandler(console_handler)
    
    return logger

# WebDriverを設定する
def setup_webdriver():
    """WebDriverを設定する"""
    from nttdeta_scraper.config.settings import WEBDRIVER_OPTIONS
    
    # ロガーを取得
    logger = logging.getLogger("nttdata_scraper")
    
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--window-size={WEBDRIVER_OPTIONS['window_size'][0]},{WEBDRIVER_OPTIONS['window_size'][1]}")
    options.add_argument(f"user-agent={WEBDRIVER_OPTIONS['user_agent']}")
    
    if 'exclude_switches' in WEBDRIVER_OPTIONS:
        for switch in WEBDRIVER_OPTIONS['exclude_switches']:
            options.add_experimental_option("excludeSwitches", [switch])
    
    if 'use_automation_extension' in WEBDRIVER_OPTIONS:
        options.add_experimental_option("useAutomationExtension", WEBDRIVER_OPTIONS['use_automation_extension'])
    
    # ChromeDriverを設定
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        logger.error(f"ChromeDriverの設定中にエラーが発生しました: {str(e)}")
        # 代替方法を試す
        try:
            logger.info("代替方法でChromeDriverを設定します...")
            driver = webdriver.Chrome(options=options)
            return driver
        except Exception as e:
            logger.error(f"代替ChromeDriver設定中にもエラーが発生しました: {str(e)}")
            raise

# 出力ディレクトリを作成する
def create_output_directory():
    """出力ディレクトリを作成する"""
    from nttdeta_scraper.config.settings import OUTPUT_BASE_DIR
    
    # 現在の日時を取得
    now = datetime.datetime.now()
    date_str = now.strftime("%Y%m%d_%H%M%S")
    
    # 出力ディレクトリを作成
    output_dir = os.path.join(OUTPUT_BASE_DIR, date_str)
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir

# 結果をJSONファイルに保存する
def save_results(output_dir, data):
    """結果をJSONファイルに保存する"""
    # 現在の日時を取得
    now = datetime.datetime.now()
    date_str = now.strftime("%Y%m%d_%H%M%S")
    
    # ファイル名を生成
    filename = f"nttdata_cases_{date_str}.json"
    filepath = os.path.join(output_dir, filename)
    
    # JSONファイルに保存
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath

# 結果をCSVファイルに保存する
def save_results_to_csv(output_dir, data):
    """結果をCSVファイルに保存する"""
    import csv
    
    # ファイル名を生成
    filename = f"nttdata_cases.csv"
    filepath = os.path.join(output_dir, filename)
    
    # CSVファイルに保存
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["タイトル", "概要", "URL"])
        for case in data:
            writer.writerow([case["title"], case["summary"], case["url"]])
    
    return filepath

# メイン関数
def main():
    """メイン関数"""
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="NTTデータの事例ページをスクレイピングするツール")
    parser.add_argument("--max-clicks", type=int, help="「もっと見る」ボタンの最大クリック回数（指定しない場合は無制限）")
    parser.add_argument("--no-summarize", action="store_false", dest="summarize", help="要約生成を無効にする")
    parser.add_argument("--output-dir", type=str, help="出力ディレクトリのパス（指定がない場合は自動生成）")
    args = parser.parse_args()
    
    # ロガーを設定
    logger = setup_logger()
    logger.info("NTTデータスクレイパーを開始します")
    
    # 出力ディレクトリの設定
    if args.output_dir:
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)
    else:
        # 現在の日時を含む出力ディレクトリを作成
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", timestamp)
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"出力ディレクトリを作成しました: {output_dir}")
    
    # ログファイルの設定
    log_file = os.path.join(output_dir, "scraper.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    
    try:
        # WebDriverを設定
        logger.info("WebDriverを設定中...")
        driver = setup_webdriver()
        
        # スクレイパーの初期化と実行
        from nttdeta_scraper.models.scraper import NTTDataScraper
        scraper = NTTDataScraper(driver=driver, max_clicks=args.max_clicks, summarize=args.summarize)
        
        # スクレイピングの実行
        logger.info("スクレイピングを開始します...")
        case_data = scraper.scrape()
        
        # 結果の保存
        scraper.save_results(case_data, output_dir)
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        traceback.print_exc()
    finally:
        # WebDriverの終了
        if 'driver' in locals() and driver:
            logger.info("WebDriverを終了します...")
            driver.quit()
    
    logger.info("NTTデータスクレイパーを終了します")

if __name__ == "__main__":
    main()
