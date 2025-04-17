#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
NRIのサービス一覧ページをスクレイピングするためのスクリプト
"""
import os
import argparse
import datetime
import logging
import json
from dotenv import load_dotenv
from tqdm import tqdm

from nri_scraper.utils.logger import setup_logger
from nri_scraper.utils.webdriver_manager import initialize_webdriver
from nri_scraper.utils.data_processor import save_to_csv, save_to_json, save_page_source
from nri_scraper.models.service_scraper import NRIServiceScraper

def parse_args():
    """
    コマンドライン引数を解析する
    
    Returns:
        argparse.Namespace: 解析されたコマンドライン引数
    """
    parser = argparse.ArgumentParser(description='NRIのサービス一覧ページをスクレイピングするスクリプト')
    parser.add_argument('--headless', action='store_true', help='ヘッドレスモードで実行する（ブラウザを表示しない）')
    parser.add_argument('--use-html', action='store_true', help='提供されたHTMLコードを使用する（ウェブサイトにアクセスしない）')
    parser.add_argument('--no-summary', action='store_true', help='要約機能を使用しない')
    
    return parser.parse_args()

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
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', current_datetime)
    os.makedirs(output_dir, exist_ok=True)
    
    # ロガーの設定
    logger = setup_logger(output_dir)
    logger.name = "nri_service_scraper"
    
    # 過去のスクレイピング結果を読み込む
    previous_services = load_previous_services()
    
    # WebDriverの初期化
    print("WebDriverを初期化しています...")
    driver = initialize_webdriver(args.headless)
    print("WebDriverの初期化が完了しました")
    
    try:
        # スクレイパーの初期化
        scraper = NRIServiceScraper(driver)
        
        # 要約機能の設定
        scraper.summarize = not args.no_summary
        
        # HTMLコードを直接使用する場合
        if args.use_html:
            print("提供されたHTMLコードを使用してサービス一覧を抽出します")
            # HTMLからサービス一覧を抽出
            scraper._extract_services_from_html()
            services = scraper.services
            
            # 要約機能を使用する場合は詳細情報を処理
            if scraper.summarize:
                processed_services = []
                total = len(services)
                print(f"合計{total}件のサービスの詳細情報を処理します...")
                
                # tqdmでプログレスバーを表示
                for i, service in enumerate(tqdm(services, desc="サービス詳細処理", unit="件")):
                    print(f"\nサービス {i+1}/{total} を処理中: {service['タイトル']}")
                    processed_service = scraper._process_service_details(service)
                    processed_services.append(processed_service)
                    progress = (i+1) / total * 100
                    print(f"進捗: {progress:.1f}% ({i+1}/{total})")
                
                services = processed_services
        else:
            # 通常のスクレイピングを実行
            print("ウェブサイトにアクセスしてサービス一覧を抽出します")
            services = scraper.scrape()
        
        # 新しいサービスを検出
        new_services = identify_new_services(services, previous_services)
        if new_services:
            print(f"新しく追加されたサービスが{len(new_services)}件見つかりました")
            for service in new_services:
                print(f"新規サービス: {service['タイトル']} - {service['URL']}")
        
        # データの保存
        if services:
            print("データをCSVとJSONに保存しています...")
            save_to_csv(services, output_dir)
            save_to_json(services, output_dir)
            print("データの保存が完了しました")
            
            # 最新の結果を保存
            save_latest_services(services)
            
            # 結果を表示
            print("\n取得したサービス一覧:")
            for i, service in enumerate(services, 1):
                print(f"{i}. {service['タイトル']} - {service['URL']}")
                
                # 追加情報があれば表示
                if 'インダストリー' in service:
                    print(f"   インダストリー: {service['インダストリー']}")
                if 'ソリューション' in service:
                    print(f"   ソリューション: {service['ソリューション']}")
                if '企業' in service and service['企業']:
                    print(f"   企業: {service['企業']}")
        else:
            print("取得できたサービスがありませんでした。")
            save_page_source(driver.page_source, output_dir)
    
    except Exception as e:
        print(f"スクレイピング中にエラーが発生しました: {str(e)}")
        # エラー情報をファイルに保存
        save_page_source(driver.page_source, output_dir, "error_page_source.html")
    
    finally:
        # WebDriverを終了
        driver.quit()
        print("スクレイピングが完了しました")
        
        # ログファイルのパスを表示
        log_file = os.path.join(output_dir, "nri_scraper_log.txt")
        print(f"\n実行ログは以下に保存されました: {log_file}")
        print(f"出力ファイルは {output_dir} ディレクトリに保存されました。")
        print("\n使用方法:")
        print("  基本実行: python run_nri_service_scraper.py")
        print("  ヘッドレスモード: python run_nri_service_scraper.py --headless")
        print("  HTMLコード使用: python run_nri_service_scraper.py --use-html")
        print("  要約機能を使用しない: python run_nri_service_scraper.py --no-summary")
        print("\n")

def load_previous_services():
    """
    過去のスクレイピング結果を読み込む
    
    Returns:
        list: 過去のサービス一覧
    """
    latest_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'latest_services.json')
    if os.path.exists(latest_file):
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"過去のサービス一覧の読み込み中にエラー: {str(e)}")
    return []

def save_latest_services(services):
    """
    最新のスクレイピング結果を保存する
    
    Args:
        services (list): サービス一覧
    """
    latest_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'latest_services.json')
    try:
        # outputディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(latest_file), exist_ok=True)
        
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(services, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"最新のサービス一覧の保存中にエラー: {str(e)}")

def identify_new_services(current_services, previous_services):
    """
    新しく追加されたサービスを特定する
    
    Args:
        current_services (list): 現在のサービス一覧
        previous_services (list): 過去のサービス一覧
    
    Returns:
        list: 新しく追加されたサービス一覧
    """
    if not previous_services:
        return []
    
    # 過去のサービスのURLリスト
    previous_urls = {service.get('URL', '') for service in previous_services}
    
    # 新しいサービスを特定
    new_services = [service for service in current_services if service.get('URL', '') not in previous_urls]
    
    return new_services

if __name__ == "__main__":
    main()
