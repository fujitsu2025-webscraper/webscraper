"""
ロギング機能を提供するモジュール
"""
import os
import logging

def setup_logger(output_dir, filename="ibm_scraper_log.txt"):
    """
    ロガーを設定する
    
    Args:
        output_dir (str): ログファイルを保存するディレクトリ
        filename (str): ログファイル名
    
    Returns:
        logging.Logger: 設定済みのロガーオブジェクト
    """
    log_file = os.path.join(output_dir, filename)
    
    # ロガーの設定
    logger = logging.getLogger("ibm_scraper")
    logger.setLevel(logging.INFO)
    
    # ハンドラーがすでに設定されている場合は追加しない
    if not logger.handlers:
        # ファイルハンドラー
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # フォーマッタ
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # ハンドラーをロガーに追加
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger
