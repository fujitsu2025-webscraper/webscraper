"""
タイトルから企業名を抽出するモジュール
"""

import re
import logging

logger = logging.getLogger("hitachi_scraper")

def extract_company_from_title(title: str) -> str:
    """
    タイトルから企業名を抽出する
    
    Args:
        title (str): タイトル
    
    Returns:
        str: 抽出された企業名
    """
    if not title:
        logger.warning("タイトルが空です")
        return ""
    
    # 日立を除外するパターン
    exclude_patterns = [
            r"日立",
            r"Hitachi",
            r"ハイタッチ",
            r"日立ソリューション",
            r"日立製作所",
            r"日立システムズ"
        ]
    
    # 企業名を抽出するパターン
    patterns = [
        # 「〇〇、」パターン（タイトルの先頭にある会社名）
        r"^([^、,]{2,10})[、,]",
        
        # 「〇〇が」「〇〇は」「〇〇と」「〇〇を」パターン
        r"^([^、,]{2,10})(が|は|と|を)",
        
        # 「株式会社〇〇」パターン
        r"株式会社([^\s、,]{2,10})",
        
        # 「〇〇株式会社」パターン
        r"([^\s、,]{2,10})株式会社",
        
        # 特定の企業パターン
        r"(東京電力|東電|首都高|首都高速道路|豊田自動織機|JAバンク|三菱UFJ|みずほ|三井住友|福岡ひびき信用金庫)"
    ]
    
    # 各パターンで検索
    for pattern in patterns:
        matches = re.findall(pattern, title)
        if matches:
            # マッチした場合、最初のグループを取得
            if isinstance(matches[0], tuple):
                company = matches[0][0]
            else:
                company = matches[0]
            
            # 空白を削除
            company = company.strip()
            
            # 除外パターンに一致する場合はスキップ
            skip = False
            for exclude_pattern in exclude_patterns:
                if re.search(exclude_pattern, company, re.IGNORECASE):
                    logger.info(f"除外パターンに一致するため、企業名をスキップ: {company}")
                    skip = True
                    break
            
            if not skip and len(company) >= 2:
                logger.info(f"【企業名抽出】生成タイトルから企業名を抽出しました: '{company}'")
                return company
    
    logger.info("【企業名抽出】生成タイトルから企業名を抽出できませんでした")
    return ""
