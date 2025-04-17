"""
企業のインダストリーを判定するためのユーティリティ
"""
import logging
import re
from ..config.settings import NRI_INDUSTRY_MAPPING, EXPLICIT_COMPANY_MAPPING, INDUSTRY_SYSTEM_MESSAGE
from .openai_client import generate_with_gpt4o_mini

logger = logging.getLogger("nri_scraper")

def determine_industry(company_name, profile_text=""):
    """
    企業名とプロフィールテキストからインダストリーを判定する
    
    Args:
        company_name (str): 企業名
        profile_text (str): お客様プロフィールのテキスト
    
    Returns:
        str: 判定されたインダストリー
    """
    try:
        # 企業名が不明の場合
        if not company_name or company_name == "不明":
            if profile_text:
                # プロフィールテキストからAIで判定
                return classify_with_ai(profile_text)
            else:
                return "その他"
        
        # 明示的なマッピングを確認
        for keyword, industry in EXPLICIT_COMPANY_MAPPING.items():
            if keyword in company_name:
                logger.info(f"企業名 '{company_name}' に '{keyword}' が含まれるため、インダストリー '{industry}' と判定")
                return industry
        
        # 企業名から業種を推測（例：〜銀行、〜証券、〜保険など）
        industry_keywords = {
            r'銀行': "銀行・証券",
            r'信用金庫': "銀行・証券",
            r'信用組合': "銀行・証券",
            r'証券': "銀行・証券",
            r'保険': "保険",
            r'生命保険': "保険",
            r'損害保険': "保険",
            r'自動車': "自動車",
            r'電機': "テクノロジー",
            r'電力': "エネルギー・資源・鉱業",
            r'ガス': "エネルギー・資源・鉱業",
            r'石油': "エネルギー・資源・鉱業",
            r'鉄道': "運輸・物流",
            r'航空': "運輸・物流",
            r'海運': "運輸・物流",
            r'物流': "運輸・物流",
            r'小売': "消費財・小売・流通",
            r'百貨店': "消費財・小売・流通",
            r'スーパー': "消費財・小売・流通",
            r'コンビニ': "消費財・小売・流通",
            r'外食': "消費財・小売・流通",
            r'食品': "消費財・小売・流通",
            r'飲料': "消費財・小売・流通",
            r'アパレル': "消費財・小売・流通",
            r'化粧品': "消費財・小売・流通",
            r'製薬': "ヘルスケア・医薬ライフサイエンス",
            r'医療機器': "ヘルスケア・医薬ライフサイエンス",
            r'病院': "ヘルスケア・医薬ライフサイエンス",
            r'クリニック': "ヘルスケア・医薬ライフサイエンス",
            r'大学': "官公庁・地方自治体・公的機関",
            r'学校': "官公庁・地方自治体・公的機関",
            r'官公庁': "官公庁・地方自治体・公的機関",
            r'自治体': "官公庁・地方自治体・公的機関",
            r'省庁': "官公庁・地方自治体・公的機関",
            r'地方公共団体': "官公庁・地方自治体・公的機関"
        }
        
        for pattern, industry in industry_keywords.items():
            if re.search(pattern, company_name):
                logger.info(f"企業名 '{company_name}' にパターン '{pattern}' が一致するため、インダストリー '{industry}' と判定")
                return industry
        
        # NRIの業種分類マッピングを確認
        for keyword, industry in NRI_INDUSTRY_MAPPING.items():
            if keyword in company_name:
                logger.info(f"企業名 '{company_name}' に '{keyword}' が含まれるため、インダストリー '{industry}' と判定")
                return industry
        
        # プロフィールテキストがある場合はAIで判定
        if profile_text:
            return classify_with_ai(profile_text)
        
        # 企業名だけでAIで判定
        if len(company_name) > 2 and company_name != "不明":
            return classify_with_ai(f"企業名: {company_name}")
        
        # 判定できない場合
        return "その他"
        
    except Exception as e:
        logger.error(f"インダストリー判定中にエラーが発生しました: {str(e)}")
        return "その他"

def classify_with_ai(text):
    """
    AIを使用してテキストからインダストリーを判定する
    
    Args:
        text (str): 判定するテキスト
    
    Returns:
        str: 判定されたインダストリー
    """
    try:
        # AIによるインダストリー判定
        result = generate_with_gpt4o_mini(
            text,
            INDUSTRY_SYSTEM_MESSAGE,
            max_tokens=50,
            temperature=0.3
        )
        
        # 結果をトリミングして返す
        industry = result.strip()
        
        # NRIの業種分類マッピングを確認
        for key, mapped_industry in NRI_INDUSTRY_MAPPING.items():
            if key in industry:
                return mapped_industry
        
        return industry if industry else "その他"
        
    except Exception as e:
        logger.error(f"AIによるインダストリー判定中にエラーが発生しました: {str(e)}")
        return "その他"
