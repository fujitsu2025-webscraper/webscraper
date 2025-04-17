"""
ロギング機能を提供するモジュール
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logger(output_dir):
    """
    ロガーを設定する
    
    Args:
        output_dir (str): ログファイルの出力ディレクトリ
    
    Returns:
        logging.Logger: 設定されたロガーオブジェクト
    """
    # ロガーの作成
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # すでにハンドラが設定されている場合は削除
    if logger.handlers:
        logger.handlers.clear()
    
    # フォーマッターの作成
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # ファイルハンドラの作成
    log_file = os.path.join(output_dir, "nri_scraper_log.txt")
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # ストリームハンドラの作成（ターミナルに出力）
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    
    # ハンドラをロガーに追加
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    return logger
