#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hitachiの事例ページをスクレイピングするためのスクリプト
"""
import os
import argparse
import datetime
import logging
from dotenv import load_dotenv

from hitachi_scraper.utils.logger import setup_logger
from hitachi_scraper.utils.webdriver_manager import initialize_webdriver
from hitachi_scraper.utils.data_processor import save_to_csv, save_to_json, save_page_source
from hitachi_scraper.models.scraper import HitachiScraper
from hitachi_scraper.config.settings import OUTPUT_BASE_DIR

def parse_args():
    """
    コマンドライン引数を解析する
    
    Returns:
        argparse.Namespace: 解析されたコマンドライン引数
    """
    parser = argparse.ArgumentParser(description='Hitachiの事例ページをスクレイピングするスクリプト')
    parser.add_argument('--max-pages', type=int, default=10, 
                      help='スクレイピングする最大ページ数 (デフォルト: 10)')
    parser.add_argument('--headless', action='store_true', 
                      help='ヘッドレスモードで実行する（ブラウザを表示しない）')
    parser.add_argument('--no-download', action='store_true',
                      help='PDFダウンロードをスキップする')
    
    args = parser.parse_args()
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
    
    # PDF保存用ディレクトリ
    pdf_dir = os.path.join(output_dir, "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    
    # ロガーの設定
    logger = setup_logger(output_dir)
    
    # WebDriverの初期化（PDFダウンロード設定追加）
    driver = initialize_webdriver(
        headless=args.headless,
        download_dir=pdf_dir if not args.no_download else None
    )
    
    try:
        # スクレイパーの初期化
        scraper = HitachiScraper(
            driver, 
            max_pages=args.max_pages,
            download_pdfs=not args.no_download
        )
        
        # スクレイピングの実行
        case_data, pdf_files = scraper.scrape()
        
        # データの保存
        if case_data:
            save_to_csv(case_data, output_dir)
            save_to_json(case_data, output_dir)
            logger.info(f"{len(case_data)}件の事例データを保存しました")
            
            if pdf_files:
                logger.info(f"{len(pdf_files)}件のPDFをダウンロードしました")
        else:
            logger.warning("取得できたデータがありませんでした。")
            save_page_source(driver.page_source, output_dir)
    
    except Exception as e:
        logger.error(f"スクレイピング中にエラーが発生しました: {str(e)}", exc_info=True)
        save_page_source(driver.page_source, output_dir, "error_page_source.html")
    
    finally:
        # WebDriverを終了
        driver.quit()
        logger.info("スクレイピングが完了しました")
        
        # 実行結果のサマリー表示
        print(f"\n{'='*40}")
        print(f" スクレイピング結果サマリー")
        print(f"{'='*40}")
        print(f"出力ディレクトリ: {output_dir}")
        if os.path.exists(pdf_dir) and not args.no_download:
            print(f"PDF保存先: {pdf_dir}")
        print(f"\n使用方法:")
        print("  基本実行: python run_hitachi_scraper.py")
        print("  ページ数指定: python run_hitachi_scraper.py --max-pages 5")
        print("  PDFダウンロード省略: python run_hitachi_scraper.py --no-download")
        print(f"{'='*40}\n")

if __name__ == "__main__":
    main()