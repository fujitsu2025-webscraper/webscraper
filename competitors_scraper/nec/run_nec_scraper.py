#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
NECの事例ページをスクレイピングするためのスクリプト
"""
import os
import argparse
import datetime
import logging
from dotenv import load_dotenv

from nec_scraper.utils.logger import setup_logger
from nec_scraper.utils.webdriver_manager import initialize_webdriver
from nec_scraper.utils.data_processor import save_to_csv, save_to_json, save_page_source
from nec_scraper.models.scraper import NECScraper
from nec_scraper.config.settings import OUTPUT_BASE_DIR

def parse_args():
    """
    コマンドライン引数を解析する
    
    Returns:
        argparse.Namespace: 解析されたコマンドライン引数
    """
    parser = argparse.ArgumentParser(description='NECの事例ページをスクレイピングするスクリプト')
    parser.add_argument('--max-clicks', type=int, default=30, help='「もっと見る」ボタンの最大クリック回数 (デフォルト: 30)')
    parser.add_argument('--headless', action='store_true', help='ヘッドレスモードで実行する（ブラウザを表示しない）')
    parser.add_argument('--no-summarize', action='store_true', help='要約機能を無効にする（デフォルトは有効）')
    
    args = parser.parse_args()
    # summarizeフラグの反転（デフォルトでTrue）
    args.summarize = not args.no_summarize
    
    return args

def main():
    """
    メイン処理
    """
    # コマンドライン引数の解析
    args = parse_args()
    
    # .envファイルから環境変数を読み込む
    load_dotenv()
    
    # 現在の日時を取得してフォーマット
    current_datetime = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 出力ディレクトリの作成
    output_dir = os.path.join(OUTPUT_BASE_DIR, current_datetime)
    os.makedirs(output_dir, exist_ok=True)
    
    # ロガーの設定
    logger = setup_logger(output_dir)
    
    # WebDriverの初期化
    driver = initialize_webdriver(args.headless)
    
    try:
        # スクレイパーの初期化
        scraper = NECScraper(driver, max_clicks=args.max_clicks, summarize=args.summarize)
        
        # スクレイピングの実行
        detailed_data, page_source = scraper.scrape()
        
        # データの保存
        if detailed_data:
            save_to_csv(detailed_data, output_dir)
            save_to_json(detailed_data, output_dir)
        else:
            logger.warning("取得できたデータがありませんでした。")
            save_page_source(page_source, output_dir)
    
    except Exception as e:
        logger.error(f"スクレイピング中にエラーが発生しました: {str(e)}")
        # エラー情報をファイルに保存
        save_page_source(driver.page_source, output_dir, "error_page_source.html")
    
    finally:
        # WebDriverを終了
        driver.quit()
        logger.info("スクレイピングが完了しました")
        
        # ログファイルのパスを表示
        log_file = os.path.join(output_dir, "nec_scraper_log.txt")
        print(f"\n実行ログは以下に保存されました: {log_file}")
        print(f"出力ファイルは {output_dir} ディレクトリに保存されました。")
        print("\n使用方法:")
        print("  基本実行: python run_nec_scraper.py")
        print("  クリック回数指定: python run_nec_scraper.py --max-clicks 10")
        print("  ヘッドレスモード: python run_nec_scraper.py --headless")
        print("  要約機能: python run_nec_scraper.py --no-summarize")
        print("\n")

if __name__ == "__main__":
    main()
