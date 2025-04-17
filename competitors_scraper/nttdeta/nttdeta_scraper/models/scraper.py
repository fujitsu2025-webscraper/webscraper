"""
NTTデータの事例ページをスクレイピングするためのクラス
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
from ..utils.web_industry_classifier import determine_industry_with_web_search
import json
import csv
import os
import datetime
import traceback
import pandas as pd  # Excel出力用

logger = logging.getLogger("nttdata_scraper")

class NTTDataScraper:
    """NTTデータの事例ページをスクレイピングするクラス"""
    
    def __init__(self, driver=None, max_clicks=None, summarize=True):
        """
        NTTデータスクレイパーの初期化
        
        Args:
            driver: WebDriverインスタンス（Noneの場合は新規作成）
            max_clicks: 「もっと見る」ボタンの最大クリック回数（Noneの場合は無制限）
            summarize: 要約生成を行うかどうか
        """
        # WebDriverの設定
        if driver:
            self.driver = driver
        else:
            options = Options()
            options.add_argument("--headless")  # ヘッドレスモードで実行
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        
        self.max_clicks = max_clicks
        self.summarize = summarize
        self.url = TARGET_URL
        self.start_time = time.time()
    
    def scrape(self):
        """
        スクレイピングを実行する
        
        Returns:
            list: 事例データのリスト
        """
        try:
            logger.info("スクレイピングを開始します...")
            
            # ページにアクセス
            self._access_page()
            
            # ページの読み込みを待機
            logger.info("ページの読み込みを待機中...")
            self._wait_for_page_load()
            
            # 事例リストと「もっと見る」ボタンを探す
            result_list, more_button = self._find_elements()
            
            if not result_list:
                logger.error("事例リスト要素が見つかりませんでした。")
                return []
            
            # 「もっと見る」ボタンをクリックして全ての事例を表示
            if more_button:
                self._load_more_cases(result_list, more_button)
            
            # 事例リストから情報を抽出
            case_data = self._extract_case_list(result_list)
            
            # 各事例の詳細情報を取得
            logger.info("各事例の詳細情報を取得しています...")
            for i, case in enumerate(case_data):
                logger.info(f"事例 {i+1}/{len(case_data)}: 「{case['タイトル']}」の詳細情報を取得中...")
                self._get_case_details(case)
                
                # 負荷軽減のための待機
                wait_time = random.uniform(1.0, 2.0)
                logger.info(f"{wait_time}秒待機中...")
                time.sleep(wait_time)
            
            logger.info(f"スクレイピングが完了しました（実行時間: {time.time() - self.start_time:.2f}秒）")
            
            return case_data
            
        except Exception as e:
            logger.error(f"スクレイピング中にエラーが発生しました: {str(e)}")
            traceback.print_exc()
            return []
    
    def _access_page(self):
        """
        ページにアクセス
        """
        logger.info(f"ページにアクセス中: {self.url}")
        self.driver.get(self.url)
        
        # ランダムな待機時間（ボットと認識されにくくするため）
        wait_time = random.uniform(3, 5)
        logger.info(f"{wait_time}秒待機中...")
        time.sleep(wait_time)
    
    def _wait_for_page_load(self):
        """
        ページの読み込みを待機
        """
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
    
    def _find_elements(self):
        """
        事例リストと「もっと見る」ボタンを探す
        
        Returns:
            tuple: (事例リスト要素, 「もっと見る」ボタン要素)
        """
        logger.info("事例リストと「もっと見る」ボタンを探しています...")
        
        # 事例リストの要素を確認
        result_list = None
        try:
            # 記事一覧のセクションを探す
            article_section = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h2[contains(@class, 'c-block-insight-article-grid-head') and text()='記事一覧']/.."))
            )
            logger.info("記事一覧セクションを発見しました")
            
            # 記事一覧セクション内の記事リストを取得
            result_list = article_section
            logger.info("記事一覧リストを発見しました")
        except Exception as e:
            logger.warning(f"記事一覧セクションが見つかりませんでした: {str(e)}")
            # 代替の要素を探す
            try:
                result_list = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".c-block-insight-article-right-body"))
                )
                logger.info("代替の事例リスト(.c-block-insight-article-right-body)を発見しました")
            except Exception as e:
                logger.error(f"事例リスト要素が見つかりませんでした: {str(e)}")
                return None, None
        
        # 「もっと見る」ボタンを探す
        more_button = None
        try:
            # NTTデータの「もっと見る」ボタンを特定
            more_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".c-btn-insight"))
            )
            logger.info("「もっと見る」ボタン(.c-btn-insight)を発見しました")
        except Exception as e:
            logger.warning(f"標準の「もっと見る」ボタンが見つかりませんでした: {str(e)}")
            # 代替のボタンを探す
            try:
                more_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button.c-btn-insight"))
                )
                logger.info("代替の「もっと見る」ボタン(button.c-btn-insight)を発見しました")
            except Exception as e:
                logger.warning(f"「もっと見る」ボタンが見つかりませんでした: {str(e)}")
                # ボタンがない場合はNoneを返す
        
        return result_list, more_button
    
    def _load_more_cases(self, result_list, more_button):
        """
        「もっと見る」ボタンをクリックして全ての事例を表示する
        
        Args:
            result_list: 事例リスト要素
            more_button: 「もっと見る」ボタン要素
        """
        logger.info("「もっと見る」ボタンをクリックして全ての事例を表示します...")
        
        # 初期の事例数を取得
        initial_count = self._count_cases(result_list)
        logger.info(f"初期事例数: {initial_count}")
        
        # 「もっと見る」ボタンをクリックし続ける
        click_count = 0
        consecutive_failures = 0
        max_consecutive_failures = 3  # 連続失敗の最大数
        
        while True:
            # 最大クリック回数に達したかチェック
            if self.max_clicks is not None and click_count >= self.max_clicks:
                logger.info(f"最大クリック回数({self.max_clicks}回)に達しました")
                break
            
            try:
                # 「もっと見る」ボタンが表示されているかチェック
                try:
                    # ボタンが表示されているか確認
                    if not more_button.is_displayed():
                        logger.info("「もっと見る」ボタンが表示されなくなりました")
                        break
                    
                    # ボタンが無効化されているかチェック
                    if more_button.get_attribute("disabled"):
                        logger.info("「もっと見る」ボタンが無効化されています")
                        break
                except Exception as e:
                    logger.warning(f"ボタンの状態確認中にエラー: {str(e)}")
                    # ボタンを再取得
                    try:
                        more_button = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".c-btn-insight"))
                        )
                        if not more_button.is_displayed():
                            logger.info("「もっと見る」ボタンが表示されなくなりました")
                            break
                    except Exception:
                        logger.info("「もっと見る」ボタンが見つかりません")
                        break
                
                # ボタンの位置までスクロール
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_button)
                time.sleep(0.5)  # スクロール後の短い待機
                
                # ボタンをクリック
                click_count += 1
                logger.info(f"「もっと見る」ボタンをクリックしました（{click_count}回目）")
                
                # JavaScriptでクリック
                self.driver.execute_script("arguments[0].click();", more_button)
                
                # クリック後の待機時間
                wait_time = random.uniform(2, 3)
                time.sleep(wait_time)
                
                # 新しい事例が読み込まれるのを待機
                new_count = self._count_cases(result_list)
                logger.info(f"クリック後の事例数: {new_count}")
                
                # 事例数が増えたかチェック
                if new_count > initial_count:
                    logger.info(f"事例数が増加しました: {initial_count} -> {new_count}")
                    initial_count = new_count
                    consecutive_failures = 0  # 成功したらカウンタをリセット
                else:
                    logger.warning(f"事例数が増加していません: {initial_count} -> {new_count}")
                    consecutive_failures += 1
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning(f"連続で{max_consecutive_failures}回事例数が増加しませんでした。処理を終了します。")
                        break
                    
                    # 追加の待機時間を設定
                    extra_wait = random.uniform(1, 2)
                    logger.info(f"追加で{extra_wait}秒待機します...")
                    time.sleep(extra_wait)
                
            except Exception as e:
                logger.error(f"「もっと見る」ボタンのクリック中にエラーが発生しました: {str(e)}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning(f"連続で{max_consecutive_failures}回エラーが発生しました。処理を終了します。")
                    break
                
                # エラー後の待機時間
                error_wait = random.uniform(2, 3)
                logger.info(f"エラー後に{error_wait}秒待機します...")
                time.sleep(error_wait)
        
        # 最終的な事例数を取得
        final_count = self._count_cases(result_list)
        logger.info(f"最終事例数: {final_count}（{final_count - initial_count}件追加）")
    
    def _count_cases(self, result_list):
        """
        現在の事例数をカウントする
        
        Args:
            result_list: 事例リスト要素
        
        Returns:
            int: 事例数
        """
        try:
            # 記事一覧セクション内の記事要素を取得
            case_items = result_list.find_elements(By.CSS_SELECTOR, "article.c-block-insight-article-grid-item")
            count = len(case_items)
            logger.info(f"現在の事例数: {count}")
            return count
        except Exception as e:
            logger.error(f"事例数のカウント中にエラーが発生しました: {str(e)}")
            return 0
    
    def _extract_case_list(self, result_list):
        """
        事例リストから情報を抽出する
        
        Args:
            result_list: 事例リスト要素
        
        Returns:
            list: 事例データのリスト
        """
        if not result_list:
            logger.error("事例リスト要素がありません。")
            return []
        
        logger.info("事例リストから情報を抽出しています...")
        case_data = []
        
        try:
            # 記事一覧セクション内の記事要素を取得
            case_items = result_list.find_elements(By.CSS_SELECTOR, "article.c-block-insight-article-grid-item")
            logger.info(f"{len(case_items)}件の事例記事を発見しました")
            
            # 各事例記事から情報を抽出
            for idx, item in enumerate(case_items):
                try:
                    # タイトル要素を取得
                    title_element = item.find_element(By.CSS_SELECTOR, "h3.c-block-insight-article-grid-item-head")
                    title = title_element.text.strip()
                    
                    # リンク要素を取得
                    link_element = item.find_element(By.TAG_NAME, "a")
                    url = link_element.get_attribute("href")
                    
                    # データを追加
                    case_data.append({
                        "タイトル": title,
                        "URL": url,
                        "企業": "NTTデータ"
                    })
                    
                    logger.info(f"事例 {idx+1}: タイトル「{title}」を抽出しました")
                    
                except Exception as e:
                    logger.error(f"事例 {idx+1} の情報抽出中にエラーが発生しました: {str(e)}")
            
        except Exception as e:
            logger.warning(f"標準の事例記事抽出中にエラーが発生しました: {str(e)}")
            # 代替の事例要素を取得
            try:
                case_items = result_list.find_elements(By.CSS_SELECTOR, ".c-block-insight-article-right-editors-recommend")
                logger.info(f"{len(case_items)}件の代替事例アイテムを発見しました")
                
                # 各事例アイテムから情報を抽出
                for idx, item in enumerate(case_items):
                    try:
                        # リンク要素を取得
                        link_element = item.find_element(By.TAG_NAME, "a")
                        url = link_element.get_attribute("href")
                        
                        # タイトル要素を取得（テキスト全体から抽出）
                        title = item.text.strip().split('\n')[0]
                        
                        # データを追加
                        case_data.append({
                            "タイトル": title,
                            "URL": url,
                            "企業": "NTTデータ"
                        })
                        
                        logger.info(f"事例 {idx+1}: タイトル「{title}」を抽出しました")
                        
                    except Exception as e:
                        logger.error(f"事例 {idx+1} の情報抽出中にエラーが発生しました: {str(e)}")
                
            except Exception as e:
                logger.error(f"事例リストからの情報抽出に失敗しました: {str(e)}")
        
        logger.info(f"合計 {len(case_data)} 件の事例データを抽出しました")
        return case_data
    
    def _get_case_details(self, case):
        """
        事例の詳細情報を取得する
        
        Args:
            case (dict): 事例データ
        """
        logger.info(f"事例: 「{case['タイトル']}」の詳細情報を取得中: {case['URL']}")
        
        try:
            # 詳細ページにアクセス
            self.driver.get(case["URL"])
            
            # ランダムな待機時間
            wait_time = random.uniform(2, 3)
            time.sleep(wait_time)
            
            # ページが完全に読み込まれるまで待機
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            
            # 初期インダストリーは固定値を使用
            industry = "テクノロジー"
            logger.info(f"初期インダストリーを設定しました: {industry}")
            
            # 要約が必要な場合は要約を生成
            if self.summarize:
                try:
                    logger.info("要約を生成中...")
                    summary = generate_with_gpt4o_mini(
                        f"タイトル: {case['タイトル']}\n\n{self.driver.find_element(By.TAG_NAME, 'body').text}",
                        SUMMARY_SYSTEM_MESSAGE
                    )
                    logger.info(f"要約を生成しました: {summary[:50]}...")
                except Exception as e:
                    logger.error(f"要約生成中にエラー: {str(e)}")
                    summary = "要約の生成に失敗しました"
                
                # 生成されたタイトルを取得
                try:
                    title_prompt = f"以下の要約に基づいて、非常に具体的で内容を的確に表現するタイトルを生成してください。\n\n要約内容：{summary}\n\n50文字以内で、この事例の主要な価値や成果が明確に伝わるタイトルを1つだけ提案してください。可能であれば、具体的な数値（例：40%削減、2倍向上）や、企業名、製品名、技術名などの固有名詞を含めてください。"
                    
                    generated_title = generate_with_gpt4o_mini(title_prompt, TITLE_SYSTEM_MESSAGE, max_tokens=100, temperature=0.8)
                    logger.info(f"生成されたタイトル: {generated_title}")
                except Exception as e:
                    logger.error(f"タイトル生成中にエラー: {str(e)}")
                    generated_title = case["タイトル"]
                
                # 生成されたタイトルから企業名を抽出
                extracted_company = None
                title_company_match = re.search(r"^([^、,]+)[、,]", generated_title)
                if title_company_match:
                    extracted_company = title_company_match.group(1).strip()
                    logger.info(f"【企業名抽出】生成タイトルから企業名を抽出しました: '{extracted_company}'")
                    
                    # 抽出した企業名をケースに設定（オプション）
                    if extracted_company and extracted_company != "NTTデータ" and "NTTデータ" not in extracted_company:
                        logger.info(f"【企業名更新】企業名を更新します: '{case.get('企業', '')}' -> '{extracted_company}'")
                        case["企業"] = extracted_company
                        
                        # 新しい企業名でインダストリーを再判定（オプション）
                        try:
                            new_industry = determine_industry_with_web_search(extracted_company, self.driver.find_element(By.TAG_NAME, "body").text)
                            if new_industry != industry:
                                logger.info(f"【インダストリー更新】インダストリーを更新します: '{industry}' -> '{new_industry}'")
                                industry = new_industry
                        except Exception as e:
                            logger.error(f"企業名更新後のインダストリー再判定中にエラー: {str(e)}")
                else:
                    logger.info("【企業名抽出】生成タイトルから企業名を抽出できませんでした")
                
                # ソリューションカテゴリを判定
                try:
                    solution_prompt = f"タイトル: {case['タイトル']}\n\n要約: {summary}\n\n内容: {self.driver.find_element(By.TAG_NAME, 'body').text[:2000]}"
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
                
                case["インダストリー"] = industry
                case["ソリューション"] = solution
                case["要約"] = summary
                case["生成タイトル"] = generated_title
            else:
                case["インダストリー"] = industry
        
        except Exception as e:
            logger.error(f"詳細ページの取得中にエラーが発生: {str(e)}")
            # エラーが発生しても続行
            if self.summarize:
                case["インダストリー"] = "その他"
                case["ソリューション"] = "その他"
                case["要約"] = "取得エラー"
            else:
                case["インダストリー"] = "その他"
    
    def save_results(self, case_data, output_dir):
        """
        スクレイピング結果を保存する
        
        Args:
            case_data (list): 事例データのリスト
            output_dir (str): 出力ディレクトリ
        """
        if not case_data:
            logger.warning("事例データが取得できませんでした")
            return
        
        # 現在の日時を取得
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # データ形式を変更（タイトルを削除し、生成タイトルをタイトルに変更）
        formatted_data = []
        for case in case_data:
            formatted_case = case.copy()
            if "生成タイトル" in formatted_case:
                formatted_case["タイトル"] = formatted_case.pop("生成タイトル")
            formatted_data.append(formatted_case)
        
        # JSONファイルに保存
        json_file = os.path.join(output_dir, f"nttdata_cases_{timestamp}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=4)
        logger.info(f"結果をJSONファイルに保存しました: {json_file}")
        
        # CSVファイルに保存
        csv_file = os.path.join(output_dir, f"nttdata_cases_{timestamp}.csv")
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            # 列の順序を定義
            fieldnames = ["タイトル", "URL", "企業", "インダストリー", "ソリューション", "要約"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for case in formatted_data:
                writer.writerow(case)
        logger.info(f"結果をCSVファイルに保存しました: {csv_file}")
