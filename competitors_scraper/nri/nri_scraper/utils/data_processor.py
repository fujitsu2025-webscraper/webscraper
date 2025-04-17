"""
データ処理と保存のためのユーティリティ
"""
import os
import json
import csv
import logging
from datetime import datetime

logger = logging.getLogger("nri_scraper")

def save_to_csv(data, output_dir):
    """
    データをCSVファイルに保存する
    
    Args:
        data (list): 保存するデータのリスト
        output_dir (str): 出力ディレクトリ
    """
    if not data:
        logger.warning("保存するデータがありません")
        return
    
    try:
        # 現在の日時を取得してファイル名に使用
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"nri_cases_{timestamp}.csv")
        
        # CSVファイルに書き込み
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            # ヘッダーを取得（最初の要素のキー）
            fieldnames = data[0].keys()
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in data:
                writer.writerow(item)
        
        logger.info(f"データをCSVファイルに保存しました: {filename}")
        
    except Exception as e:
        logger.error(f"CSVファイルへの保存中にエラーが発生しました: {str(e)}")

def save_to_json(data, output_dir):
    """
    データをJSONファイルに保存する
    
    Args:
        data (list): 保存するデータのリスト
        output_dir (str): 出力ディレクトリ
    """
    if not data:
        logger.warning("保存するデータがありません")
        return
    
    try:
        # 現在の日時を取得してファイル名に使用
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"nri_cases_{timestamp}.json")
        
        # JSONファイルに書き込み
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"データをJSONファイルに保存しました: {filename}")
        
    except Exception as e:
        logger.error(f"JSONファイルへの保存中にエラーが発生しました: {str(e)}")

def save_page_source(page_source, output_dir, filename=None):
    """
    ページソースをHTMLファイルに保存する
    
    Args:
        page_source (str): 保存するページソース
        output_dir (str): 出力ディレクトリ
        filename (str, optional): ファイル名。指定がない場合は現在時刻に基づいて生成
    """
    try:
        if not filename:
            # 現在の日時を取得してファイル名に使用
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nri_page_source_{timestamp}.html"
        
        filepath = os.path.join(output_dir, filename)
        
        # HTMLファイルに書き込み
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(page_source)
        
        logger.info(f"ページソースをHTMLファイルに保存しました: {filepath}")
        
    except Exception as e:
        logger.error(f"ページソースの保存中にエラーが発生しました: {str(e)}")
