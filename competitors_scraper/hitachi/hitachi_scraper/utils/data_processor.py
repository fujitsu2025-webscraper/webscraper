"""
データ処理のためのユーティリティ
"""
import os
import json
import pandas as pd
import logging

logger = logging.getLogger("hitachi_scraper")

def save_to_csv(data, output_dir, filename="hitachi_cases.csv"):
    """
    データをCSVファイルとして保存する
    
    Args:
        data (list): 保存するデータのリスト
        output_dir (str): 出力ディレクトリ
        filename (str): ファイル名
    """
    if not data:
        logger.warning("保存するデータがありません")
        return
    
    # DataFrameに変換
    df = pd.DataFrame(data)
    
    # CSVファイルとして保存
    csv_file = os.path.join(output_dir, filename)
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    logger.info(f"CSVデータを保存しました: {csv_file} ({len(df)}件)")

def save_to_json(data, output_dir, filename="hitachi_cases.json"):
    """
    データをJSONファイルとして保存する
    
    Args:
        data (list): 保存するデータのリスト
        output_dir (str): 出力ディレクトリ
        filename (str): ファイル名
    """
    if not data:
        logger.warning("保存するデータがありません")
        return
    
    # JSONファイルとして保存
    json_file = os.path.join(output_dir, filename)
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info(f"JSONデータを保存しました: {json_file} ({len(data)}件)")

def save_page_source(page_source, output_dir, filename="page_source.html"):
    """
    ページソースをファイルとして保存する
    
    Args:
        page_source (str): 保存するページソース
        output_dir (str): 出力ディレクトリ
        filename (str): ファイル名
    """
    if not page_source:
        logger.warning("保存するページソースがありません")
        return
    
    # ファイルとして保存
    page_source_file = os.path.join(output_dir, filename)
    with open(page_source_file, "w", encoding="utf-8") as f:
        f.write(page_source)
    logger.info(f"ページソースを保存しました: {page_source_file}")
