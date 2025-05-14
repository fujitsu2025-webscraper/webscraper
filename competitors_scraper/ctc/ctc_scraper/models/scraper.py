"""
CTCの事例ページをスクレイピングするためのクラス
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
from ..utils.web_industry_classifier import determine_industry_with_fallback
from ..utils.company_extractor import extract_company_from_title

logger = logging.getLogger("ctc_scraper")

class CTCScraper:
    """CTCの事例ページをスクレイピングするクラス"""
    
    def __init__(self, driver, summarize=True):
        """
        初期化
        
        Args:
            driver: WebDriverオブジェクト
            summarize (bool): 要約機能を使用するかどうか
        """
        self.driver = driver
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
            # 業種別一覧からタイトルとURLを取得
            cases = self._find_elements()
        
            # 詳細情報を取得
            detailed_data = self._process_cases(cases)
            
            return detailed_data, page_source
            
        except Exception as e:
            logger.error(f"スクレイピング中にエラーが発生しました: {str(e)}")
            return [], self.driver.page_source
    
    def _find_elements(self):
        logger.info("業種カテゴリボタンと事例リストを探索中...")

        results = []

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-button a.button"))
            )
            button_count = len(self.driver.find_elements(By.CSS_SELECTOR, "ul.list-button a.button"))
            logger.info(f"✅ {button_count} 件の業種カテゴリボタンを検出")

            for i in range(button_count):
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-button a.button"))
                    )
                    current_buttons = self.driver.find_elements(By.CSS_SELECTOR, "ul.list-button a.button")
                    label = current_buttons[i].text.strip()
                    logger.info(f"🔘 『{label}』カテゴリをクリック中...")

                    self.driver.execute_script("arguments[0].click();", current_buttons[i])

                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.flexItem .card-introduction"))
                    )

                    result_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.flexItem .card-introduction")
                    logger.info(f"✅ 『{label}』カテゴリから {len(result_elements)} 件の事例を取得")

                    for elem in result_elements:
                        try:
                            title_elem = elem.find_element(By.CSS_SELECTOR, "p")  # もしくは適切なタグ
                            link_elem = elem.find_element(By.TAG_NAME, "a")

                            example = {
                                "タイトル": title_elem.text.strip(),
                                "URL": link_elem.get_attribute("href").strip(),
                                "企業": "CTC"  # 必要に応じて取得
                            }
                            results.append(example)
                        except Exception as e:
                            logger.warning(f"⚠️ カードの解析失敗: {str(e)}")

                except Exception as e:
                    logger.error(f"❌ 『{label}』カテゴリの処理中にエラー発生: {str(e)}")

        except Exception as e:
            logger.error(f"❌ 業種カテゴリボタンの初回取得に失敗: {str(e)}")
            return []

        return results


    def _get_case_count(self, result_list):
        """
        事例数を取得する
        
        Args:
            result_list: 事例リスト要素
        
        Returns:
            int: 事例数
        """
        try:
            if result_list:
                # 結果リスト内のリンク数をカウント
                return len(result_list.find_elements(By.TAG_NAME, "a"))
            else:
                # 全体のリンク数をカウント
                return len(self.driver.find_elements(By.TAG_NAME, "a"))
        except StaleElementReferenceException:
            # 要素が古くなった場合は再取得
            try:
                result_list_updated = self.driver.find_element(By.ID, "NFC-SrchResultList")
                return len(result_list_updated.find_elements(By.TAG_NAME, "a"))
            except:
                return len(self.driver.find_elements(By.TAG_NAME, "a"))
    
    def _extract_case_list(self, result_list, industry_name="不明業種"):
        """
        事例リストから情報を抽出する（業種対応）

        Args:
            result_list: 事例リスト要素
            industry_name (str): 業種名

        Returns:
            list: 事例データのリスト
        """
        logger.info(f"[{industry_name}] 事例リストから情報を抽出します...")

        case_data = []

        if result_list:
            try:
                # DOM更新の可能性があるので再取得
                result_list = self.driver.find_element(By.ID, "NFC-SrchResultList")
                case_items = result_list.find_elements(By.CSS_SELECTOR, "li")
                logger.info(f"[{industry_name}] 事例リスト内のアイテム数: {len(case_items)}")

                for item in case_items:
                    try:
                        link_element = item.find_element(By.TAG_NAME, "a")
                        title = link_element.text.strip()
                        url = link_element.get_attribute("href")

                        if title.startswith("NEW"):
                            title = title.replace("NEW", "", 1).strip()

                        # カテゴリー取得（あれば）
                        categories = []
                        try:
                            tag_elements = item.find_elements(By.CSS_SELECTOR, ".tag, .category, .label")
                            for tag in tag_elements:
                                tag_text = tag.text.strip()
                                if tag_text:
                                    categories.append(tag_text)
                        except:
                            pass

                        if url and not any(existing["URL"] == url for existing in case_data):
                            case_data.append({
                                "業種": industry_name,
                                "タイトル": title or "タイトルなし",
                                "URL": url,
                                "企業": "CTC",
                                "カテゴリー": categories
                            })
                            logger.info(f"[{industry_name}] 事例を取得: {title}")
                    except Exception as e:
                        logger.error(f"[{industry_name}] 事例アイテムの処理中にエラー: {str(e)}")
            except Exception as e:
                logger.error(f"[{industry_name}] 事例リストの再取得中にエラー: {str(e)}")

        
        # 事例が取得できなかった場合の代替手段
        if not case_data:
            logger.warning("事例リストからデータを取得できませんでした。代替手段を試みます...")
            
            # ページ内のすべてのリンクを取得
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"ページ内のリンク総数: {len(all_links)}")
            
            # 事例に関連するリンクをフィルタリング
            for link in all_links:
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    
                    # 事例関連のリンクかどうかを判断
                    if href and text and ("case" in href or "事例" in text):
                        if not any(item["URL"] == href for item in case_data):
                            case_data.append({
                                "タイトル": text or "タイトルなし",
                                "URL": href,
                                "企業": "CTC"  # 企業カラムを追加し、すべての値に「CTC」を設定
                            })
                            logger.info(f"代替手段で事例を取得: {text} - {href}")
                except Exception as e:
                    logger.error(f"リンク処理中にエラー: {str(e)}")
        
        return case_data
    
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
            result = self._process_case(idx, case)
            detailed_data.append(result)
        
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
            logger.info(f"事例 {idx+1}: {case['タイトル']}の詳細情報を取得中...")
            
            # 詳細ページにアクセス
            logger.info(f"事例: {case['タイトル']}の詳細情報を取得中: {case['URL']}")
            self.driver.get(case["URL"])
            
            # ランダムな待機時間
            wait_time = random.uniform(2, 4)
            logger.info(f"{wait_time}秒待機中...")
            time.sleep(wait_time)
            
            # 詳細ページが読み込まれるまで待機
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            
            # 詳細ページのHTMLを解析
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            # 企業名、業種情報、業務情報、顧客プロフィールを抽出
            company_name = case.get("企業", "")
            business_type = ""
            business_field = ""
            customer_profile = ""
            
            # 顧客プロフィールセクションを探す
            profile_section = soup.find("h2", string=lambda text: text and "お客様プロフィール" in text)
            if profile_section:
                profile_div = profile_section.find_next("div", class_="NFC-CaseDetailBlock")
                if profile_div:
                    customer_profile = profile_div.get_text(strip=True)
                    logger.info(f"顧客プロフィール: {customer_profile[:50]}...")
            
            # 業種情報を探す
            business_info_section = soup.find("h2", string=lambda text: text and "業種" in text)
            if business_info_section:
                business_info_div = business_info_section.find_next("div", class_="NFC-CaseDetailBlock")
                if business_info_div:
                    business_type = business_info_div.get_text(strip=True)
                    logger.info(f"業種情報: {business_type}")
            
            # 業務情報を探す
            field_info_section = soup.find("h2", string=lambda text: text and "業務" in text)
            if field_info_section:
                field_info_div = field_info_section.find_next("div", class_="NFC-CaseDetailBlock")
                if field_info_div:
                    business_field = field_info_div.get_text(strip=True)
                    logger.info(f"業務情報: {business_field}")
            
            # 初期インダストリーを設定
            logger.info("初期インダストリーを設定しました: テクノロジー")
            industry = "テクノロジー"
            
            # 詳細ページの内容全体を取得
            content = soup.get_text(strip=True)
            
            # 既存のインダストリー分類ロジックを使用
            traditional_industry = determine_industry(
                url=case["URL"],
                company_name=company_name,
                business_type=business_type,
                business_field=business_field,
                customer_profile=customer_profile
            )
            
            # 要約機能が有効な場合のみ要約を生成
            if self.summarize:
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
                    
                    # タイトルから企業名を抽出
                    extracted_company = extract_company_from_title(generated_title)
                    
                    # 企業名が抽出できた場合、その企業名でGoogle検索
                    if extracted_company:
                        logger.info(f"【企業名更新】企業名を更新します: '{company_name}' -> '{extracted_company}'")
                        company_name = extracted_company
                        
                        # Google検索によるインダストリー分類
                        try:
                            web_industry = determine_industry_with_fallback(company_name, content)
                            if web_industry != "その他":
                                logger.info(f"【インダストリー更新】インダストリーを更新します: '{traditional_industry}' -> '{web_industry}'")
                                industry = web_industry
                            else:
                                industry = traditional_industry
                        except Exception as e:
                            logger.error(f"Google検索によるインダストリー分類中にエラー: {str(e)}")
                            industry = traditional_industry
                    else:
                        # 企業名が抽出できなかった場合は従来の方法でインダストリーを判定
                        industry = traditional_industry
                        
                except Exception as e:
                    logger.error(f"タイトル生成中にエラー: {str(e)}")
                    generated_title = case["タイトル"]
                    industry = traditional_industry
                
                return {
                    "タイトル": generated_title,
                    "URL": case["URL"],
                    "企業": company_name,
                    "インダストリー": industry,
                    "ソリューション": solution,
                    "要約": summary
                }
            else:
                # 要約機能が無効の場合
                # Google検索によるインダストリー分類
                try:
                    web_industry = determine_industry_with_fallback(company_name, content)
                    if web_industry != "その他":
                        logger.info(f"【インダストリー更新】インダストリーを更新します: '{traditional_industry}' -> '{web_industry}'")
                        industry = web_industry
                    else:
                        industry = traditional_industry
                except Exception as e:
                    logger.error(f"Google検索によるインダストリー分類中にエラー: {str(e)}")
                    industry = traditional_industry
                    
                return {
                    "タイトル": case["タイトル"],
                    "URL": case["URL"],
                    "企業": company_name,
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
