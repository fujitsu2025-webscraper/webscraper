"""
テキストからインダストリーを判断するモジュール
"""
import re
import logging
from ..config.settings import INDUSTRY_LIST, CTC_INDUSTRY_MAPPING, EXPLICIT_COMPANY_MAPPING, INDUSTRY_SYSTEM_MESSAGE
from .openai_client import generate_with_gpt4o_mini

logger = logging.getLogger("ctc_scraper")

# インダストリー判定用のパターン定義（グローバル変数として定義）
INDUSTRY_PATTERNS = {
    r'自動車|車|カー|モビリティ': "自動車",
    r'重工|重機|造船|航空|宇宙': "重工業・エンジニアリング",
    r'機械|装置|設備|ロボット': "産業機械",
    r'素材|化学|繊維|紙': "素材・化学",
    r'エネルギー|電力|ガス|石油|鉱業|資源': "エネルギー・資源・鉱業",
    r'建設|建築|土木|住宅': "建設",
    r'物流|運輸|配送|宅配|輸送': "運輸・物流",
    r'小売|販売|流通|消費|百貨店|スーパー|コンビニ': "消費財・小売・流通",
    r'テクノロジー|IT|情報|システム|ソフトウェア|ハードウェア|電子': "テクノロジー",
    r'通信|電話|モバイル|インターネット': "情報通信",
    r'エンタテイメント|メディア|放送|出版|広告|ゲーム': "エンタテイメント&メディア",
    r'ホテル|旅行|観光|レジャー|外食|飲食': "ホスピタリティ&レジャー",
    r'商社': "総合商社",
    r'金融|ファイナンス': "金融サービス",
    r'銀行|証券|投資': "銀行・証券",
    r'資産|運用|ファンド': "資産運用",
    r'保険': "保険",
    r'不動産|住宅|マンション': "不動産",
    r'プライベート・エクイティ|PE|投資ファンド': "プライベート・エクイティ（PE）",
    r'都市|インフラ|社会基盤': "都市・インフラストラクチャー",
    r'官公庁|自治体|公的|政府|省庁|市役所|区役所|役場|県庁|市$|町$|村$|区$|[都道府県]$|[都道府県]庁': "官公庁・地方自治体・公的機関",
    r'農業|林業|水産|食品|バイオ': "農林水産・食・バイオ",
    r'人材|採用|求人|派遣': "人材サービス",
    r'医療|病院|クリニック|製薬|薬局|介護|福祉|ヘルスケア': "ヘルスケア・医薬ライフサイエンス"
}

# 都道府県と市町村のパターン
PREFECTURE_PATTERN = r'(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)'
MUNICIPALITY_PATTERN = r'([^\s]+[市町村区])'

def determine_industry(url=None, company_name=None, business_type=None, business_field=None, customer_profile=None, content=None):
    """
    テキストからインダストリーを判断する
    
    Args:
        url (str): 事例のURL
        company_name (str): 企業名
        business_type (str): 業種情報
        business_field (str): 業務情報
        customer_profile (str): 顧客プロフィール
        content (str): urlの文章全体
    
    Returns:
        str: 判断されたインダストリー
    """
    industry = "その他"
    
    # URLからの判断
    if url:
        # URLからインダストリーを判断
        if "fintech" in url or "finance" in url or "banking" in url:
            industry = "銀行・証券"
            logger.info(f"URLに基づいて判断されたインダストリー: {industry}")
        elif "kurumie" in url or "logistics" in url or "transport" in url:
            industry = "運輸・物流"
            logger.info(f"URLに基づいて判断されたインダストリー: {industry}")
        elif "manufacturing" in url or "factory" in url:
            industry = "産業機械"
            logger.info(f"URLに基づいて判断されたインダストリー: {industry}")
        elif "retail" in url or "distribution" in url:
            industry = "消費財・小売・流通"
            logger.info(f"URLに基づいて判断されたインダストリー: {industry}")
        elif "healthcare" in url or "medical" in url or "hospital" in url:
            industry = "ヘルスケア・医薬ライフサイエンス"
            logger.info(f"URLに基づいて判断されたインダストリー: {industry}")
        elif "government" in url or "public" in url:
            industry = "官公庁・地方自治体・公的機関"
            logger.info(f"URLに基づいて判断されたインダストリー: {industry}")
        elif "energy" in url or "power" in url:
            industry = "エネルギー・資源・鉱業"
            logger.info(f"URLに基づいて判断されたインダストリー: {industry}")
        elif "construction" in url or "building" in url:
            industry = "建設"
            logger.info(f"URLに基づいて判断されたインダストリー: {industry}")
        elif "automotive" in url or "car" in url or "mobility" in url:
            industry = "自動車"
            logger.info(f"URLに基づいて判断されたインダストリー: {industry}")
    
    # URLに県名や市町村名が含まれる場合の判定
    if industry == "その他" and url:
        if re.search(PREFECTURE_PATTERN, url) or re.search(MUNICIPALITY_PATTERN, url):
            industry = "官公庁・地方自治体・公的機関"
            logger.info(f"URLの県名・市町村名に基づいて判断されたインダストリー: {industry}")
    
    # 特定の企業名マッピングからの判断
    if industry == "その他" and company_name:
        for company_keyword, mapped_industry in EXPLICIT_COMPANY_MAPPING.items():
            if company_keyword in company_name:
                industry = mapped_industry
                logger.info(f"特定の企業名マッピングに基づいて判断されたインダストリー: {industry}")
                break
    
    # 企業名に県名や市町村名が含まれる場合の判定
    if industry == "その他" and company_name:
        if re.search(PREFECTURE_PATTERN, company_name) or re.search(MUNICIPALITY_PATTERN, company_name):
            industry = "官公庁・地方自治体・公的機関"
            logger.info(f"企業名の県名・市町村名に基づいて判断されたインダストリー: {industry}")
    
    # 顧客プロフィールに県名や市町村名が含まれる場合の判定
    if industry == "その他" and customer_profile:
        if re.search(PREFECTURE_PATTERN, customer_profile) or re.search(MUNICIPALITY_PATTERN, customer_profile):
            industry = "官公庁・地方自治体・公的機関"
            logger.info(f"顧客プロフィールの県名・市町村名に基づいて判断されたインダストリー: {industry}")
    
    # 業種情報に「地方公共団体・官庁」が含まれる場合
    if industry == "その他" and business_type and "地方公共団体・官庁" in business_type:
        industry = "官公庁・地方自治体・公的機関"
        logger.info(f"業種情報「地方公共団体・官庁」に基づいて判断されたインダストリー: {industry}")
    
    # CTCの業種分類からの判断
    if industry == "その他" and business_type:
        for ctc_industry, mapped_industry in CTC_INDUSTRY_MAPPING.items():
            if ctc_industry in business_type:
                industry = mapped_industry
                logger.info(f"CTCの業種分類に基づいて判断されたインダストリー: {industry}")
                break
    
    # 業務情報からの判断
    if industry == "その他" and business_field:
        if "製造" in business_field or "生産" in business_field:
            industry = "産業機械"
            logger.info(f"業務情報（一般製造業）に基づいて判断されたインダストリー: {industry}")
        elif "物流" in business_field or "配送" in business_field or "輸送" in business_field:
            industry = "運輸・物流"
            logger.info(f"業務情報に基づいて判断されたインダストリー: {industry}")
        elif "小売" in business_field or "販売" in business_field or "流通" in business_field:
            industry = "消費財・小売・流通"
            logger.info(f"業務情報に基づいて判断されたインダストリー: {industry}")
    
    # 企業名に基づく判断
    if industry == "その他" and company_name:
        for pattern, ind in INDUSTRY_PATTERNS.items():
            if re.search(pattern, company_name):
                industry = ind
                logger.info(f"企業名に基づいて判断されたインダストリー: {industry}")
                break
    
    # 顧客プロフィールに基づく判断
    if industry == "その他" and customer_profile:
        for pattern, ind in INDUSTRY_PATTERNS.items():
            if re.search(pattern, customer_profile):
                industry = ind
                logger.info(f"顧客プロフィールに基づいて判断されたインダストリー: {industry}")
                break
    
    # 上記の方法で判断できない場合はGPT-4o-miniを使用
    if industry == "その他" and (company_name or customer_profile):
        prompt = f"企業名: {company_name or ''}\nお客様プロフィール: {customer_profile or ''}\n業種情報: {business_type or ''}\n業務情報: {business_field or ''}\nコンテンツ: {content or ''}"
        
        try:
            gpt_industry = generate_with_gpt4o_mini(prompt, INDUSTRY_SYSTEM_MESSAGE, max_tokens=50, temperature=0.3)
            
            # GPTの回答が有効なインダストリーかチェック
            if gpt_industry in INDUSTRY_LIST:
                industry = gpt_industry
                logger.info(f"GPT-4o-miniによって判断されたインダストリー: {industry}")
            else:
                logger.warning(f"GPT-4o-miniの回答 '{gpt_industry}' は有効なインダストリーではありません")
        except Exception as e:
            logger.error(f"GPT-4o-miniによるインダストリー判断中にエラー: {str(e)}")
    
    return industry
