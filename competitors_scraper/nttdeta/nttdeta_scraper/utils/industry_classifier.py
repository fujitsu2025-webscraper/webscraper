"""
インダストリー分類のためのユーティリティ関数
"""
import re
import logging
from ..config.settings import INDUSTRY_LIST, NTTDATA_INDUSTRY_MAPPING, EXPLICIT_COMPANY_MAPPING, INDUSTRY_SYSTEM_MESSAGE
from .openai_client import generate_with_gpt4o_mini

logger = logging.getLogger("nttdata_scraper")

def determine_industry(company, content):
    """
    企業名とコンテンツからインダストリーを判定する
    
    Args:
        company (str): 企業名
        content (str): コンテンツテキスト
    
    Returns:
        str: インダストリー
    """
    logger.info("インダストリーを判定中...")
    
    # 明示的なマッピングをチェック
    for key, value in EXPLICIT_COMPANY_MAPPING.items():
        if key in content:
            logger.info(f"明示的なマッピングを発見: '{key}' -> '{value}'")
            return value
    
    # NTTデータの業種分類マッピングをチェック
    for key, value in NTTDATA_INDUSTRY_MAPPING.items():
        if key in content:
            logger.info(f"NTTデータの業種分類マッピングを発見: '{key}' -> '{value}'")
            return value
    
    # 業種に関連するキーワードをチェック
    industry_keywords = {
        "自動車": ["自動車", "カー", "車両", "モビリティ"],
        "重工業・エンジニアリング": ["重工業", "エンジニアリング", "プラント"],
        "産業機械": ["産業機械", "工作機械", "製造装置"],
        "素材・化学": ["素材", "化学", "材料"],
        "エネルギー・資源・鉱業": ["エネルギー", "電力", "ガス", "資源", "鉱業", "石油"],
        "建設": ["建設", "建築", "土木"],
        "運輸・物流": ["運輸", "物流", "輸送", "配送", "鉄道", "航空"],
        "消費財・小売・流通": ["消費財", "小売", "流通", "スーパー", "百貨店", "EC"],
        "テクノロジー": ["テクノロジー", "IT", "ソフトウェア", "ハードウェア"],
        "情報通信": ["情報通信", "通信", "キャリア", "モバイル"],
        "エンタテイメント&メディア": ["エンタテイメント", "メディア", "放送", "出版", "ゲーム"],
        "ホスピタリティ&レジャー": ["ホスピタリティ", "レジャー", "ホテル", "旅行", "観光"],
        "総合商社": ["総合商社", "商社"],
        "金融サービス": ["金融サービス", "フィンテック", "決済"],
        "銀行・証券": ["銀行", "証券", "信用金庫", "信用組合"],
        "資産運用": ["資産運用", "投資", "ファンド"],
        "保険": ["保険", "生命保険", "損害保険"],
        "不動産": ["不動産", "住宅", "マンション", "賃貸"],
        "プライベート・エクイティ（PE）": ["プライベートエクイティ", "PE", "ベンチャーキャピタル"],
        "都市・インフラストラクチャー": ["都市", "インフラ", "スマートシティ"],
        "官公庁・地方自治体・公的機関": ["官公庁", "自治体", "公的機関", "行政", "政府", "省庁", "市役所", "県庁"],
        "農林水産・食・バイオ": ["農林水産", "農業", "林業", "水産", "食品", "バイオ"],
        "人材サービス": ["人材", "採用", "求人", "転職"],
        "ヘルスケア・医薬ライフサイエンス": ["ヘルスケア", "医療", "病院", "製薬", "医薬", "ライフサイエンス"]
    }
    
    # キーワードマッチングでインダストリーを判定
    for industry, keywords in industry_keywords.items():
        for keyword in keywords:
            if keyword in content:
                logger.info(f"キーワードマッチング: '{keyword}' -> '{industry}'")
                return industry
    
    # キーワードマッチングで判定できない場合はAIを使用
    try:
        logger.info("AIを使用してインダストリーを判定...")
        prompt = f"企業名: {company}\n\nお客様プロフィール:\n{content[:2000]}"
        industry = generate_with_gpt4o_mini(prompt, INDUSTRY_SYSTEM_MESSAGE, max_tokens=50, temperature=0.3)
        
        # 結果が有効なインダストリーかチェック
        if industry in INDUSTRY_LIST:
            logger.info(f"AIによるインダストリー判定結果: {industry}")
            return industry
        else:
            logger.warning(f"AIによる判定結果が無効です: {industry}")
            return "テクノロジー"  # デフォルト値
    
    except Exception as e:
        logger.error(f"AIによるインダストリー判定中にエラー: {str(e)}")
        return "テクノロジー"  # デフォルト値
