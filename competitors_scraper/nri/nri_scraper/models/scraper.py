"""
NRIの事例ページをスクレイピングするためのクラス
"""
import time
import random
import logging
import re
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

from ..config.settings import TARGET_URL, SUMMARY_SYSTEM_MESSAGE, TITLE_SYSTEM_MESSAGE, SOLUTION_SYSTEM_MESSAGE
from ..utils.openai_client import generate_with_gpt4o_mini
from ..utils.industry_classifier import determine_industry

logger = logging.getLogger("nri_scraper")

class NRIScraper:
    """NRIの事例ページをスクレイピングするクラス"""
    
    def __init__(self, driver, max_pages=10, summarize=True):
        """
        初期化
        
        Args:
            driver: WebDriverオブジェクト
            max_pages (int): ページネーションの最大ページ数
            summarize (bool): 要約機能を使用するかどうか
        """
        self.driver = driver
        self.max_pages = max_pages
        self.summarize = summarize
        self.url = TARGET_URL
    
    def scrape(self):
        """
        スクレイピングを実行する
        
        Returns:
            tuple: (事例データのリスト, ページソース)
        """
        try:
            # ページにアクセス
            logger.info(f"ページにアクセス中: {self.url}")
            self.driver.get(self.url)
            
            # ランダムな待機時間（ボットと認識されにくくするため）
            wait_time = random.uniform(3, 5)
            logger.info(f"{wait_time}秒待機中...")
            time.sleep(wait_time)
            
            # ページのソースを取得して確認
            page_source = self.driver.page_source
            logger.info(f"ページソースの長さ: {len(page_source)}文字")
            
            # ページのタイトルを取得して確認
            page_title = self.driver.title
            logger.info(f"ページタイトル: {page_title}")
            
            # ページが完全に読み込まれるまで待機
            logger.info("ページの読み込みを待機中...")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            
            # 事例リストを取得
            case_data = self._extract_case_list()
            
            # 詳細情報を取得
            detailed_data = self._process_cases(case_data)
            
            return detailed_data, page_source
            
        except Exception as e:
            logger.error(f"スクレイピング中にエラーが発生しました: {str(e)}")
            return [], self.driver.page_source
    
    def _extract_case_list(self):
        """
        事例リストから情報を抽出する
        
        Returns:
            list: 事例データのリスト
        """
        case_data = []
        current_page = 1
        
        try:
            while current_page <= self.max_pages:
                logger.info(f"ページ {current_page} の事例を抽出中...")
                
                # 事例リストの要素を取得
                try:
                    # NRIの事例リストのコンテナを特定
                    case_container = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".casestudy-list"))
                    )
                    
                    # 個々の事例要素を取得
                    case_elements = case_container.find_elements(By.CSS_SELECTOR, ".casestudy-item")
                    logger.info(f"{len(case_elements)}件の事例を発見しました")
                    
                    # 各事例の情報を抽出
                    for case_element in case_elements:
                        try:
                            # タイトル
                            title_element = case_element.find_element(By.CSS_SELECTOR, ".casestudy-item__title")
                            title = title_element.text.strip() if title_element else "タイトルなし"
                            
                            # URL
                            link_element = case_element.find_element(By.CSS_SELECTOR, "a")
                            url = link_element.get_attribute("href") if link_element else ""
                            
                            # 企業名（NRIの場合は別途取得する必要があるかもしれません）
                            company = self._extract_company_name(case_element)
                            
                            # 事例データを追加
                            case_data.append({
                                "タイトル": title,
                                "URL": url,
                                "企業": company
                            })
                            
                        except Exception as e:
                            logger.error(f"事例要素の処理中にエラー: {str(e)}")
                            continue
                    
                except Exception as e:
                    logger.error(f"事例リストの取得中にエラー: {str(e)}")
                    break
                
                # 次のページがあるか確認
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, ".pagination__next:not(.is-disabled)")
                    next_button.click()
                    logger.info(f"次のページに移動中...")
                    
                    # ページ読み込み待機
                    time.sleep(random.uniform(2, 4))
                    current_page += 1
                    
                except NoSuchElementException:
                    logger.info("次のページがないため、抽出を終了します")
                    break
                except Exception as e:
                    logger.error(f"ページネーション処理中にエラー: {str(e)}")
                    break
        
        except Exception as e:
            logger.error(f"事例リストの抽出中にエラー: {str(e)}")
        
        logger.info(f"合計 {len(case_data)} 件の事例データを抽出しました")
        return case_data
    
    def _extract_company_name(self, case_element):
        """
        事例要素から企業名を抽出する
        
        Args:
            case_element: 事例要素
        
        Returns:
            str: 企業名
        """
        try:
            # NRIの事例では企業名が含まれている可能性のある要素を探す
            company_element = case_element.find_element(By.CSS_SELECTOR, ".casestudy-item__company")
            return company_element.text.strip()
        except NoSuchElementException:
            # 企業名が明示的に表示されていない場合はタイトルから推測
            try:
                title_element = case_element.find_element(By.CSS_SELECTOR, ".casestudy-item__title")
                title_text = title_element.text.strip()
                
                # タイトルから企業名を抽出する試み（「〜株式会社」「〜社」などのパターン）
                company_match = re.search(r'(.+?)(株式会社|社|グループ|銀行|証券|保険)', title_text)
                if company_match:
                    return company_match.group(0)
                
                return "不明"
            except:
                return "不明"
    
    def _process_cases(self, case_data):
        """
        各事例の詳細情報を取得する
        
        Args:
            case_data (list): 事例データのリスト
        
        Returns:
            list: 詳細情報を含む事例データのリスト
        """
        detailed_data = []
        for idx, case in enumerate(case_data):
            logger.info(f"事例 {idx+1}/{len(case_data)} の詳細情報を取得中: {case['タイトル']}")
            detailed_case = self._process_case(idx, case)
            detailed_data.append(detailed_case)
        
        return detailed_data
    
    def _process_case(self, idx, case):
        """
        事例の詳細情報を取得する
        
        Args:
            idx (int): 事例のインデックス
            case (dict): 事例データ
        
        Returns:
            dict: 詳細情報を含む事例データ
        """
        try:
            # URLが存在しない場合はスキップ
            if not case["URL"]:
                logger.warning(f"事例 {idx+1} にURLがありません")
                return case
            
            # 詳細ページにアクセス
            logger.info(f"詳細ページにアクセス中: {case['URL']}")
            self.driver.get(case["URL"])
            
            # ランダムな待機時間
            wait_time = random.uniform(2, 4)
            time.sleep(wait_time)
            
            # ページが読み込まれるまで待機
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            
            # 企業名の取得・更新（詳細ページに正確な情報がある場合）
            company = self._extract_company_from_detail()
            if company and company != "不明":
                case["企業"] = company
            
            # インダストリーの判定
            industry = determine_industry(case["企業"], "")
            logger.info(f"インダストリーを判定しました: {industry}")
            
            # 要約機能が有効な場合
            if self.summarize:
                # 詳細ページの内容を取得
                content = self._extract_detail_content()
                
                # 要約を生成
                try:
                    summary = generate_with_gpt4o_mini(
                        f"タイトル: {case['タイトル']}\n\n{content}",
                        SUMMARY_SYSTEM_MESSAGE
                    )
                    logger.info(f"要約を生成しました: {summary[:50]}...")
                except Exception as e:
                    logger.error(f"要約生成中にエラー: {str(e)}")
                    summary = "要約の生成に失敗しました"
                
                # ソリューションカテゴリを判定
                try:
                    solution_prompt = f"タイトル: {case['タイトル']}\n\n要約: {summary}\n\n内容: {content[:2000]}"
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
                except Exception as e:
                    logger.error(f"ソリューションカテゴリ判定中にエラー: {str(e)}")
                    solution = "その他"
                
                # 具体的なタイトルを生成
                try:
                    title_prompt = f"以下の要約に基づいて、非常に具体的で内容を的確に表現するタイトルを生成してください。\n\n要約内容：{summary}\n\n50文字以内で、この事例の主要な価値や成果が明確に伝わるタイトルを1つだけ提案してください。可能であれば、具体的な数値（例：40%削減、2倍向上）や、企業名、製品名、技術名などの固有名詞を含めてください。"
                    
                    generated_title = generate_with_gpt4o_mini(title_prompt, TITLE_SYSTEM_MESSAGE, max_tokens=100, temperature=0.8)
                    logger.info(f"生成されたタイトル: {generated_title}")
                except Exception as e:
                    logger.error(f"タイトル生成中にエラー: {str(e)}")
                    generated_title = case["タイトル"]
                
                return {
                    "タイトル": generated_title,
                    "URL": case["URL"],
                    "企業": case["企業"],
                    "インダストリー": industry,
                    "ソリューション": solution,
                    "要約": summary
                }
            else:
                return {
                    "タイトル": case["タイトル"],
                    "URL": case["URL"],
                    "企業": case["企業"],
                    "インダストリー": industry
                }
        except Exception as e:
            logger.error(f"詳細ページの取得中にエラーが発生: {str(e)}")
            # エラーが発生しても続行
            if self.summarize:
                return {
                    "タイトル": case["タイトル"],
                    "URL": case["URL"],
                    "企業": case["企業"],
                    "インダストリー": "その他",
                    "ソリューション": "その他",
                    "要約": "取得エラー"
                }
            else:
                return {
                    "タイトル": case["タイトル"],
                    "URL": case["URL"],
                    "企業": case["企業"],
                    "インダストリー": "その他"
                }
    
    def _extract_company_from_detail(self):
        """
        詳細ページから企業名を抽出する
        
        Returns:
            str: 企業名
        """
        try:
            # NRIの詳細ページでの企業名表示要素を探す
            company_element = self.driver.find_element(By.CSS_SELECTOR, ".case-company")
            return company_element.text.strip()
        except NoSuchElementException:
            # 他の可能性のある要素を探す
            try:
                # タイトル下のサブタイトルや導入事例の顧客名などを探す
                subtitle_element = self.driver.find_element(By.CSS_SELECTOR, ".case-subtitle")
                subtitle_text = subtitle_element.text.strip()
                
                # 「〜株式会社」「〜社」などのパターンを探す
                company_match = re.search(r'(.+?)(株式会社|社|グループ|銀行|証券|保険)', subtitle_text)
                if company_match:
                    return company_match.group(0)
            except:
                pass
            
            return "不明"
    
    def _extract_detail_content(self):
        """
        詳細ページの内容を抽出する
        
        Returns:
            str: 詳細ページの内容
        """
        try:
            # NRIの詳細ページでのコンテンツ要素を探す
            content_element = self.driver.find_element(By.CSS_SELECTOR, ".case-content")
            content = content_element.text.strip()
            
            # コンテンツが取得できない場合は、ページ全体のテキストを取得
            if not content:
                content = self.driver.find_element(By.TAG_NAME, "body").text
            
            return content
        except Exception as e:
            logger.error(f"詳細内容の抽出中にエラー: {str(e)}")
            # エラー時はページ全体のテキストを取得
            try:
                return self.driver.find_element(By.TAG_NAME, "body").text
            except:
                return "内容を取得できませんでした"
