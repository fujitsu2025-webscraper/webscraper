"""
Google検索を使用したインダストリー分類モジュール

Google Custom Search APIを使用して企業のインダストリーを検索します。
"""

import os
import logging
import requests
import re
import time
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# ロガーの設定
logger = logging.getLogger("ctc_scraper")

# グローバル変数
api_used = False
rate_limited = False

def search_company_industry_google(company_name: str) -> str:
    """
    Google Custom Search APIを使用して企業の業種情報を検索
    
    Args:
        company_name (str): 企業名
    
    Returns:
        str: 検索結果のテキスト
    """
    global api_used, rate_limited
    
    # 環境変数を読み込む
    load_dotenv()
    
    # APIキーとCSE IDを取得
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    
    # APIキーとCSE IDが設定されていない場合はエラー
    if not api_key or not cse_id:
        logger.error("Google APIキーまたはCSE IDが設定されていません")
        raise ValueError("Google APIキーとCSE IDを設定してください")
    
    # レート制限に達している場合はエラー
    if rate_limited:
        logger.error("Google APIのレート制限に達しています")
        raise ValueError("Google APIのレート制限に達しています")
    
    try:
        # 検索クエリを作成（より具体的なクエリに改善）
        query = f"{company_name} 業種 業界 セクター 事業内容"
        
        # APIリクエストを送信
        api_endpoint = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cse_id,
            "q": query,
            "num": 5,  # 検索結果の数
            "lr": "lang_ja",  # 日本語の結果のみ
            "gl": "jp"  # 日本からの検索結果
        }
        
        logger.info(f"Google APIで検索中: {query}")
        response = requests.get(api_endpoint, params=params)
        api_used = True
        
        # レスポンスをチェック
        if response.status_code == 200:
            # 成功した場合は結果を解析
            data = response.json()
            
            # 検索結果がない場合は空文字列を返す
            if "items" not in data or not data["items"]:
                logger.warning(f"Google検索結果が見つかりませんでした: {company_name}")
                return ""
            
            # 検索結果からテキストを抽出
            search_text = ""
            for item in data["items"]:
                if "title" in item:
                    search_text += item["title"] + " "
                if "snippet" in item:
                    search_text += item["snippet"] + " "
            
            logger.info(f"Google検索結果を取得しました: {search_text[:100]}...")
            return search_text
            
        elif response.status_code == 403:
            # レート制限に達した場合
            rate_limited = True
            logger.error("【重要】Google検索APIのレート制限に達しました。")
            
            # レスポンスからエラー詳細を取得
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "詳細不明")
                logger.error(f"Google APIエラー: {error_message}")
            except:
                logger.error("Google APIエラーの詳細を取得できませんでした")
            
            raise ValueError("Google APIのレート制限に達しました")
        else:
            # その他のエラー
            logger.error(f"Google API呼び出し中にエラー発生: ステータスコード {response.status_code}")
            try:
                error_data = response.json()
                logger.error(f"エラー詳細: {error_data}")
            except:
                logger.error(f"レスポンス: {response.text}")
            
            raise ValueError(f"Google API呼び出し中にエラー発生: ステータスコード {response.status_code}")
            
    except Exception as e:
        logger.error(f"Google API呼び出し中に例外が発生: {str(e)}")
        raise

def extract_company_from_text(content: str) -> str:
    """
    テキストから企業名を抽出
    
    Args:
        content (str): テキスト
    
    Returns:
        str: 抽出された企業名
    """
    logger.info("テキストから企業名を抽出中...")
    
    # CTCを除外するパターン
    exclude_patterns = [
        r"CTC",
        r"伊藤忠テクノソリューションズ",
        r"シーティーシー"
    ]
    
    # 企業名抽出パターン
    patterns = [
        r"([^\s]+)株式会社",  # 「〇〇株式会社」
        r"株式会社([^\s]+)",  # 「株式会社〇〇」
        r"([^\s]+)社は",      # 「〇〇社は」
        r"([^\s]+)社が",      # 「〇〇社が」
        r"([^\s]+)社の",      # 「〇〇社の」
        r"([^\s]+)社と",      # 「〇〇社と」
        r"([^\s]+)社を"       # 「〇〇社を」
    ]
    
    # 各パターンで検索
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            company = match.strip()
            
            # 空文字列や短すぎる名前はスキップ
            if not company or len(company) < 2:
                continue
            
            # 除外パターンに一致する場合はスキップ
            skip = False
            for exclude_pattern in exclude_patterns:
                if re.search(exclude_pattern, company):
                    logger.info(f"除外パターンに一致するため、企業名をスキップ: {company}")
                    skip = True
                    break
            
            if not skip:
                logger.info(f"企業名を抽出しました: {company}")
                return company
    
    logger.warning("企業名を抽出できませんでした")
    return ""

def classify_industry_from_web_data(company: str, web_data: str) -> str:
    """
    Web検索結果からインダストリーを分類
    
    Args:
        company (str): 企業名
        web_data (str): Web検索結果
    
    Returns:
        str: インダストリー
    """
    # 特定の企業に対する固定マッピング
    company_industry_map = {
        "日本政策金融公庫": "銀行・証券",
        "JFC": "銀行・証券",
        "JR東海": "運輸・物流",
        "JR東海ツアーズ": "運輸・物流",
        "東邦ガス": "エネルギー・資源・鉱業",
        "東邦ガス情報システム": "エネルギー・資源・鉱業",
        "J-POWER": "エネルギー・資源・鉱業",
        "電源開発": "エネルギー・資源・鉱業",
        "旭化成": "素材・化学",
        "大陽日酸": "素材・化学",
        "三菱ロジスネクスト": "運輸・物流",
        "JAバンク": "銀行・証券",
        "農林中央金庫": "銀行・証券",
        "NEC": "テクノロジー",
        "日本電気": "テクノロジー",
        "CTC": "テクノロジー",
        "伊藤忠テクノソリューションズ": "テクノロジー",
    }
    
    # 企業名が直接マッピングにある場合はそれを返す
    for key, value in company_industry_map.items():
        if key.lower() in company.lower():
            logger.info(f"企業名マッピングからインダストリーを判定: {company} -> {value}")
            return value
    
    # インダストリーキーワードのマッピング（重み付け調整）
    industry_keywords = {
        "自動車": {
            "weight": 1.5,
            "keywords": ["自動車", "カー", "車両", "モビリティ", "自動車メーカー", "カーメーカー"]
        },
        "重工業・エンジニアリング": {
            "weight": 1.2,
            "keywords": ["重工業", "エンジニアリング", "プラント", "重機", "建機", "工業"]
        },
        "産業機械": {
            "weight": 1.2,
            "keywords": ["産業機械", "工作機械", "製造装置", "機械メーカー", "産業機器"]
        },
        "素材・化学": {
            "weight": 1.3,
            "keywords": ["素材", "化学", "材料", "化学メーカー", "素材メーカー", "化成品"]
        },
        "エネルギー・資源・鉱業": {
            "weight": 1.5,
            "keywords": ["エネルギー", "電力", "ガス", "資源", "鉱業", "石油", "発電", "電気", "ガス会社", "電力会社"]
        },
        "建設": {
            "weight": 1.2,
            "keywords": ["建設", "建築", "土木", "ゼネコン", "建設会社", "建設業"]
        },
        "運輸・物流": {
            "weight": 1.4,
            "keywords": ["運輸", "物流", "輸送", "配送", "鉄道", "航空", "船舶", "海運", "運送", "宅配", "交通"]
        },
        "消費財・小売・流通": {
            "weight": 1.0,
            "keywords": ["消費財", "小売", "流通", "スーパー", "百貨店", "EC", "ショッピング", "通販", "販売"]
        },
        "テクノロジー": {
            "weight": 1.0,
            "keywords": ["テクノロジー", "IT", "ソフトウェア", "ハードウェア", "情報システム", "システム開発", "IT企業"]
        },
        "情報通信": {
            "weight": 1.1,
            "keywords": ["情報通信", "通信", "キャリア", "モバイル", "通信事業者", "通信会社"]
        },
        "エンタテイメント&メディア": {
            "weight": 1.0,
            "keywords": ["エンタテイメント", "メディア", "放送", "出版", "ゲーム", "映像", "音楽", "コンテンツ"]
        },
        "ホスピタリティ&レジャー": {
            "weight": 1.0,
            "keywords": ["ホスピタリティ", "レジャー", "ホテル", "旅行", "観光", "リゾート", "レストラン"]
        },
        "総合商社": {
            "weight": 1.3,
            "keywords": ["総合商社", "商社", "トレーディング"]
        },
        "金融サービス": {
            "weight": 1.2,
            "keywords": ["金融サービス", "フィンテック", "決済", "金融", "ファイナンス"]
        },
        "銀行・証券": {
            "weight": 1.5,
            "keywords": ["銀行", "証券", "信用金庫", "信用組合", "金融機関", "銀行業", "金融公庫", "政策金融"]
        },
        "資産運用": {
            "weight": 1.1,
            "keywords": ["資産運用", "投資", "ファンド", "アセットマネジメント"]
        },
        "保険": {
            "weight": 1.3,
            "keywords": ["保険", "生命保険", "損害保険", "保険会社", "生保", "損保"]
        },
        "不動産": {
            "weight": 1.1,
            "keywords": ["不動産", "住宅", "マンション", "賃貸","ビル", "ホテル", "不動産会社", "デベロッパー"]
        },
        "プライベート・エクイティ（PE）": {
            "weight": 1.0,
            "keywords": ["プライベートエクイティ", "PE", "ベンチャーキャピタル", "VC"]
        },
        "都市・インフラストラクチャー": {
            "weight": 1.0,
            "keywords": ["都市", "インフラ", "スマートシティ", "社会インフラ", "インフラ整備"]
        },
        "官公庁・地方自治体・公的機関": {
            "weight": 1.3,
            "keywords": ["官公庁", "自治体", "公的機関", "行政", "政府", "省庁", "市役所", "県庁", "官庁", "公共"]
        },
        "農林水産・食・バイオ": {
            "weight": 1.2,
            "keywords": ["農林水産", "農業", "林業", "水産", "食品", "バイオ", "農林", "食品メーカー"]
        },
        "人材サービス": {
            "weight": 1.0,
            "keywords": ["人材", "採用", "求人", "転職", "人材紹介", "人材派遣", "人材会社"]
        },
        "ヘルスケア・医薬ライフサイエンス": {
            "weight": 1.3,
            "keywords": ["ヘルスケア", "医療", "病院", "製薬", "医薬", "ライフサイエンス", "医薬品", "医療機器"]
        },
        "教育・文化・学術": {
            "weight": 1.1,
            "keywords": ["教育", "学校", "大学", "高校", "学習", "文化", "学術", "研究所", "教育機関"]
        }
    }
    
    # 各インダストリーの重み付きスコアを計算
    scores = {}
    
    for industry, data in industry_keywords.items():
        weight = data["weight"]
        keywords = data["keywords"]
        
        industry_score = 0
        for keyword in keywords:
            # 大文字小文字を区別せずに検索
            count = len(re.findall(keyword, web_data, re.IGNORECASE))
            if count > 0:
                # スコアに重みを掛ける
                industry_score += count * weight
        
        if industry_score > 0:
            scores[industry] = industry_score
    
    # マッチング結果がある場合は最も高いスコアのインダストリーを返す
    if scores:
        best_industry = max(scores.items(), key=lambda x: x[1])[0]
        logger.info(f"インダストリーを判定しました: {best_industry} (スコア: {scores[best_industry]:.1f})")
        return best_industry
    
    # マッチング結果がない場合はデフォルト値を返す
    logger.warning(f"インダストリーを判定できませんでした: {company}")
    return "その他"

def determine_industry_with_web_search(company: str, content: str) -> str:
    """
    Google検索を使用したインダストリー分類
    
    Args:
        company (str): 企業名
        content (str): コンテンツテキスト
    
    Returns:
        str: インダストリー
    """
    global api_used, rate_limited
    api_used = False
    
    logger.info("Google検索を使用したインダストリー分類を開始...")
    
    # 企業名が指定されていない場合は抽出を試みる
    main_company = company
    if not main_company:
        main_company = extract_company_from_text(content)
    if not main_company:
        logger.warning("企業名が指定されておらず、抽出もできませんでした")
        return "その他"
    
    # Google検索を使用
    try:
        # 環境変数を読み込む
        load_dotenv()
        
        # APIキーとCSE IDを取得
        api_key = os.getenv("GOOGLE_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")
        
        # Google検索を実行
        if api_key and cse_id:
            web_data = search_company_industry_google(main_company)
            
            # 検索結果からインダストリーを分類
            industry = classify_industry_from_web_data(main_company, web_data)
            
            # APIの使用状況をログに記録
            if rate_limited:
                logger.info(f"【分類結果】企業: {main_company}, インダストリー: {industry} (Google APIレート制限)")
            else:
                logger.info(f"【分類結果】企業: {main_company}, インダストリー: {industry} (Google API使用)")
            
            return industry
        else:
            logger.error("Google APIキーまたはCSE IDが設定されていません")
            return "その他"
    except Exception as e:
        logger.error(f"Google API検索中にエラー発生: {str(e)}")
        return "その他"

def determine_industry_with_fallback(company: str, content: str) -> str:
    """
    Google検索を使用したインダストリー分類
    
    Args:
        company (str): 企業名
        content (str): コンテンツテキスト
    
    Returns:
        str: インダストリー
    """
    try:
        # Google検索による分類を試みる
        industry = determine_industry_with_web_search(company, content)
        return industry
    except Exception as e:
        logger.error(f"インダストリー分類中に例外が発生しました: {str(e)}")
        return "その他"
