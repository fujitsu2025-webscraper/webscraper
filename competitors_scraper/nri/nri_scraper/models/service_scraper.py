"""
NRIのサービス一覧ページをスクレイピングするためのクラス
"""
import time
import random
import logging
import re
import json
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException, 
    StaleElementReferenceException
)

from ..config.settings import SUMMARY_SYSTEM_MESSAGE, TITLE_SYSTEM_MESSAGE, SOLUTION_SYSTEM_MESSAGE
from ..utils.openai_client import generate_with_gpt4o_mini
from ..utils.web_industry_classifier import determine_industry_with_fallback
from ..utils.company_extractor import extract_company_from_title

logger = logging.getLogger("nri_service_scraper")

class NRIServiceScraper:
    """NRIのサービス一覧ページをスクレイピングするクラス"""
    
    def __init__(self, driver):
        """
        初期化
        
        Args:
            driver: WebDriverオブジェクト
        """
        self.driver = driver
        self.url = "https://www.nri.com/jp/service/solution/index.html"
        self.services = []
        self.summarize = True

    def scrape(self):
        """
        スクレイピングを実行する
        
        Returns:
            list: サービス一覧データ
        """
        try:
            # ページにアクセス
            logger.info(f"ページにアクセス中: {self.url}")
            print(f"ページにアクセス中: {self.url}")
            self.driver.get(self.url)
            
            # ランダムな待機時間（ボットと認識されにくくするため）
            wait_time = random.uniform(3, 5)
            logger.info(f"{wait_time}秒待機中...")
            print(f"{wait_time}秒待機中...")
            time.sleep(wait_time)
            
            # ページのソースを取得して確認
            page_source = self.driver.page_source
            logger.info(f"ページソースの長さ: {len(page_source)}文字")
            print(f"ページソースの長さ: {len(page_source)}文字")
            
            # ページのタイトルを取得して確認
            page_title = self.driver.title
            logger.info(f"ページタイトル: {page_title}")
            print(f"ページタイトル: {page_title}")
            
            # ページが完全に読み込まれるまで待機
            logger.info("ページの読み込みを待機中...")
            print("ページの読み込みを待機中...")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            
            # サービス一覧を抽出
            self._extract_services()
            
            # サービスが見つからない場合は、ページ全体から探す
            if not self.services:
                logger.info("サービス一覧が見つかりませんでした。ページ全体から探します...")
                print("サービス一覧が見つかりませんでした。ページ全体から探します...")
                self._extract_services_from_page()
            
            # サービス詳細情報を処理
            processed_services = []
            for service in self.services:
                processed_service = self._process_service_details(service)
                processed_services.append(processed_service)
            
            return processed_services
            
        except Exception as e:
            logger.error(f"スクレイピング中にエラーが発生しました: {str(e)}")
            print(f"スクレイピング中にエラーが発生しました: {str(e)}")
            return []
    
    def _extract_services(self):
        """
        サービス一覧を抽出する
        """
        try:
            logger.info("サービス一覧を抽出中...")
            print("サービス一覧を抽出中...")
            
            # サービス一覧のコンテナを探す
            # lst-cardindexクラスを持つul要素を探す
            try:
                service_container = self.driver.find_element(By.CSS_SELECTOR, "ul.lst-cardindex#lst-solution")
                
                # li要素を取得
                service_items = service_container.find_elements(By.TAG_NAME, "li")
                
                logger.info(f"{len(service_items)}個のサービスアイテムを発見しました")
                print(f"{len(service_items)}個のサービスアイテムを発見しました")
                
                # 各サービスアイテムから情報を抽出
                from tqdm import tqdm
                for i, item in enumerate(tqdm(service_items, desc="サービス抽出", unit="件")):
                    try:
                        progress = (i+1) / len(service_items) * 100
                        print(f"\rサービスアイテム {i+1}/{len(service_items)} を処理中... 進捗: {progress:.1f}%", end="")
                        service_info = self._extract_service_info(item)
                        if service_info:
                            self.services.append(service_info)
                            print(f"\nサービス「{service_info['タイトル']}」を抽出しました")
                    except Exception as e:
                        logger.error(f"サービスアイテムからの抽出中にエラー: {str(e)}")
                        print(f"\nサービスアイテムからの抽出中にエラー: {str(e)}")
                
                print("")  # 改行
                logger.info(f"合計{len(self.services)}件のサービスを抽出しました")
                print(f"合計{len(self.services)}件のサービスを抽出しました")
            
            except NoSuchElementException:
                logger.warning("lst-cardindex#lst-solutionが見つかりません。別のセレクタを試します...")
                print("lst-cardindex#lst-solutionが見つかりません。別のセレクタを試します...")
                
                # 別のセレクタを試す
                try:
                    # 一般的なカード/リスト要素を探す
                    service_containers = self.driver.find_elements(By.CSS_SELECTOR, ".card-list, .solution-list, .service-list, .list-items")
                    
                    total_items = 0
                    for container in service_containers:
                        items = container.find_elements(By.CSS_SELECTOR, "li, .card, .item, .solution-item, .service-item")
                        total_items += len(items)
                    
                    print(f"別のセレクタから{total_items}個のアイテムを発見しました")
                    
                    item_count = 0
                    from tqdm import tqdm
                    
                    # 全アイテムのリストを作成
                    all_items = []
                    for container in service_containers:
                        items = container.find_elements(By.CSS_SELECTOR, "li, .card, .item, .solution-item, .service-item")
                        all_items.extend(items)
                    
                    # tqdmでプログレスバーを表示
                    for i, item in enumerate(tqdm(all_items, desc="サービス抽出", unit="件")):
                        try:
                            progress = (i+1) / total_items * 100
                            print(f"\rアイテム {i+1}/{total_items} を処理中... 進捗: {progress:.1f}%", end="")
                            service_info = self._extract_service_info(item)
                            if service_info:
                                self.services.append(service_info)
                                print(f"\nサービス「{service_info['タイトル']}」を抽出しました")
                        except Exception as e:
                            logger.error(f"サービスアイテムからの抽出中にエラー: {str(e)}")
                            print(f"\nサービスアイテムからの抽出中にエラー: {str(e)}")
                    
                    print("")  # 改行
                    logger.info(f"別のセレクタから{len(self.services)}件のサービスを抽出しました")
                    print(f"別のセレクタから{len(self.services)}件のサービスを抽出しました")
                
                except Exception as e:
                    logger.error(f"別のセレクタからの抽出中にエラー: {str(e)}")
                    print(f"別のセレクタからの抽出中にエラー: {str(e)}")
            
        except Exception as e:
            logger.error(f"サービス一覧の抽出中にエラー: {str(e)}")
            print(f"サービス一覧の抽出中にエラー: {str(e)}")
    
    def _extract_service_info(self, element):
        """
        サービスアイテムから情報を抽出する
        
        Args:
            element: サービスアイテム要素
        
        Returns:
            dict: サービス情報
        """
        try:
            # タイトルを取得
            title_element = element.find_element(By.CSS_SELECTOR, "h3")
            title = title_element.text.strip() if title_element else ""
            
            # URLを取得
            link_element = element.find_element(By.TAG_NAME, "a")
            url = link_element.get_attribute("href") if link_element else ""
            
            # 説明文を取得
            description_element = element.find_element(By.CSS_SELECTOR, "p")
            description = description_element.text.strip() if description_element else ""
            
            # サービス情報を作成
            service_info = {
                "タイトル": title,
                "URL": url,
                "説明": description,
                "企業": "NRI"
            }
            
            return service_info
        
        except Exception as e:
            logger.error(f"サービス情報の抽出中にエラー: {str(e)}")
            return None
    
    def _extract_services_from_page(self):
        """
        ページ全体からサービス一覧を抽出する
        """
        try:
            # ページ全体のHTMLを取得
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            
            # サービス一覧を探す方法1: リンクリストから
            service_links = []
            
            # メインコンテンツエリアを特定
            main_content = soup.select_one("main, .main-content, #content, .content")
            if not main_content:
                main_content = soup
            
            # サービス関連のリンクを探す
            for a_tag in main_content.select("a"):
                href = a_tag.get("href", "")
                text = a_tag.get_text().strip()
                
                # サービス関連のリンクかどうかを判断
                if (text and 
                    ("/service/" in href or "/solution/" in href) and 
                    "index.html" not in href):
                    
                    # 説明文を探す
                    description = ""
                    parent = a_tag.parent
                    for p_tag in parent.select("p"):
                        if p_tag.get_text().strip() and p_tag.get_text().strip() != text:
                            description = p_tag.get_text().strip()
                            break
                    
                    # URLが相対パスの場合は絶対パスに変換
                    if href and not href.startswith("http"):
                        href = f"https://www.nri.com{href}" if href.startswith("/") else f"https://www.nri.com/{href}"
                    
                    service_links.append({
                        "タイトル": text,
                        "URL": href,
                        "説明": description,
                        "企業": "NRI"
                    })
            
            # 重複を排除
            unique_services = []
            seen_urls = set()
            
            for service in service_links:
                if service["URL"] not in seen_urls:
                    seen_urls.add(service["URL"])
                    unique_services.append(service)
            
            self.services = unique_services
            logger.info(f"ページ全体から{len(self.services)}件のサービスを抽出しました")
            print(f"ページ全体から{len(self.services)}件のサービスを抽出しました")
            
        except Exception as e:
            logger.error(f"ページ全体からのサービス抽出中にエラー: {str(e)}")
            print(f"ページ全体からのサービス抽出中にエラー: {str(e)}")

    def _process_service_details(self, service):
        """
        サービスの詳細情報を取得・処理する
        
        Args:
            service (dict): サービス情報
        
        Returns:
            dict: 詳細情報を含むサービス情報
        """
        try:
            logger.info(f"サービス詳細情報を取得中: {service['タイトル']}")
            print(f"サービス詳細情報を取得中: {service['タイトル']}")
            
            # サービス詳細ページにアクセス
            self.driver.get(service["URL"])
            
            # ページの読み込みを待機
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # ランダムな待機時間
            wait_time = random.uniform(1, 3)
            logger.info(f"{wait_time}秒待機中...")
            print(f"{wait_time}秒待機中...")
            time.sleep(wait_time)
            
            # ページのHTMLを取得
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            
            # 企業名を取得（デフォルトはNRI）
            company = "NRI"
            
            # ページのコンテンツを取得
            content = soup.get_text(strip=True)
            
            # 初期インダストリーを設定
            logger.info("初期インダストリーを設定しました: テクノロジー")
            print("初期インダストリーを設定しました: テクノロジー")
            industry = "テクノロジー"
            
            # 要約機能が有効な場合
            if self.summarize:
                try:
                    from ..utils.openai_client import generate_with_gpt4o_mini
                    from ..config.settings import SUMMARY_SYSTEM_MESSAGE, TITLE_SYSTEM_MESSAGE, SOLUTION_SYSTEM_MESSAGE
                    
                    print("要約を生成中...")
                    # 要約を生成
                    try:
                        summary = generate_with_gpt4o_mini(
                            f"タイトル: {service['タイトル']}\n\n{content}",
                            SUMMARY_SYSTEM_MESSAGE
                        )
                        logger.info(f"要約を生成しました: {summary[:50]}...")
                        print(f"要約を生成しました: {summary[:50]}...")
                    except Exception as e:
                        logger.error(f"要約生成中にエラー: {str(e)}")
                        print(f"要約生成中にエラー: {str(e)}")
                        summary = "要約の生成に失敗しました"
                    
                    # ソリューションカテゴリを判定
                    try:
                        print("ソリューションカテゴリを判定中...")
                        solution_prompt = f"タイトル: {service['タイトル']}\n\n要約: {summary}\n\n内容: {content[:2000]}"
                        solution_result = generate_with_gpt4o_mini(
                            solution_prompt,
                            SOLUTION_SYSTEM_MESSAGE,
                            max_tokens=100,
                            temperature=0.5
                        )
                        
                        # 結果からソリューションカテゴリを抽出
                        solution = "その他"
                        if "ソリューション:" in solution_result:
                            solution_parts = solution_result.split("ソリューション:")
                            if len(solution_parts) > 1:
                                solution = solution_parts[1].strip()
                        
                        logger.info(f"ソリューションカテゴリを判定しました: {solution}")
                        print(f"ソリューションカテゴリを判定しました: {solution}")
                    except Exception as e:
                        logger.error(f"ソリューションカテゴリ判定中にエラー: {str(e)}")
                        print(f"ソリューションカテゴリ判定中にエラー: {str(e)}")
                        solution = "その他"
                    
                    # 具体的なタイトルを生成
                    try:
                        print("具体的なタイトルを生成中...")
                        title_prompt = f"以下の要約に基づいて、非常に具体的で内容を的確に表現するタイトルを生成してください。\n\n要約内容：{summary}\n\n50文字以内で、この事例の主要な価値や成果が明確に伝わるタイトルを1つだけ提案してください。可能であれば、具体的な数値（例：40%削減、2倍向上）や、企業名、製品名、技術名などの固有名詞を含めてください。"
                        
                        generated_title = generate_with_gpt4o_mini(title_prompt, TITLE_SYSTEM_MESSAGE, max_tokens=100, temperature=0.8)
                        logger.info(f"生成されたタイトル: {generated_title}")
                        print(f"生成されたタイトル: {generated_title}")
                        
                        # タイトルから企業名を抽出
                        extracted_company = extract_company_from_title(generated_title)
                        if extracted_company:
                            logger.info(f"【企業名更新】企業名を更新します: '{company}' -> '{extracted_company}'")
                            print(f"【企業名更新】企業名を更新します: '{company}' -> '{extracted_company}'")
                            company = extracted_company
                    except Exception as e:
                        logger.error(f"タイトル生成中にエラー: {str(e)}")
                        print(f"タイトル生成中にエラー: {str(e)}")
                        generated_title = service["タイトル"]
                    
                    # インダストリーを判定
                    industry = self._determine_industry(company, content)
                    
                    return {
                        "タイトル": generated_title,
                        "URL": service["URL"],
                        "企業": company,
                        "インダストリー": industry,
                        "ソリューション": solution,
                        "要約": summary
                    }
                except Exception as e:
                    logger.error(f"要約生成中にエラー: {str(e)}")
                    print(f"要約生成中にエラー: {str(e)}")
                    return {
                        "タイトル": service["タイトル"],
                        "URL": service["URL"],
                        "企業": company,
                        "インダストリー": industry
                    }
            else:
                # インダストリーを判定
                industry = self._determine_industry(company, content)
                
                return {
                    "タイトル": service["タイトル"],
                    "URL": service["URL"],
                    "企業": company,
                    "インダストリー": industry
                }
    
        except Exception as e:
            logger.error(f"サービス詳細の処理中にエラー: {str(e)}")
            print(f"サービス詳細の処理中にエラー: {str(e)}")
            return {
                "タイトル": service.get("タイトル", ""),
                "URL": service.get("URL", ""),
                "企業": "NRI",
                "インダストリー": "その他"
            }
    
    def _determine_industry(self, company, content):
        """
        企業名とコンテンツからインダストリーを判定する
        
        Args:
            company (str): 企業名
            content (str): コンテンツテキスト
        
        Returns:
            str: インダストリー
        """
        try:
            # 初期インダストリーを設定
            logger.info("初期インダストリーを設定しました: テクノロジー")
            print("初期インダストリーを設定しました: テクノロジー")
            industry = "テクノロジー"
            
            # 既存の高度なインダストリー判定を使用
            try:
                from ..utils.advanced_industry_classifier import advanced_determine_industry
                
                # ページのタイトルを取得
                title = self.driver.title
                
                # 高度なインダストリー判定を使用
                traditional_industry = advanced_determine_industry(company, content, title)
                
                logger.info(f"高度なインダストリー判定結果: {traditional_industry}")
                print(f"高度なインダストリー判定結果: {traditional_industry}")
                
                industry = traditional_industry
            
            except Exception as e:
                logger.error(f"高度なインダストリー判定中にエラー: {str(e)}")
                print(f"高度なインダストリー判定中にエラー: {str(e)}")
            
            # Google検索によるインダストリー分類
            try:
                # 企業名がNRIでない場合のみGoogle検索を実行
                if company != "NRI" and company != "野村総合研究所" and company != "野村総研":
                    web_industry = determine_industry_with_fallback(company, content)
                    if web_industry != "その他":
                        logger.info(f"【インダストリー更新】インダストリーを更新します: '{industry}' -> '{web_industry}'")
                        print(f"【インダストリー更新】インダストリーを更新します: '{industry}' -> '{web_industry}'")
                        industry = web_industry
            except Exception as e:
                logger.error(f"Google検索によるインダストリー分類中にエラー: {str(e)}")
                print(f"Google検索によるインダストリー分類中にエラー: {str(e)}")
            
            return industry
        
        except Exception as e:
            logger.error(f"インダストリー判定中にエラー: {str(e)}")
            print(f"インダストリー判定中にエラー: {str(e)}")
            return "テクノロジー"  # デフォルト値
