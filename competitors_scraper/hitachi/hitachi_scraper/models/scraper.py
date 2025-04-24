#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hitachiの事例ページをスクレイピングするためのクラス
"""
import os
import time
import random
import logging
import requests
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

logger = logging.getLogger("hitachi_scraper")

class HitachiScraper:
    """Hitachiの事例ページをスクレイピングするクラス"""
    
    def __init__(self, driver, max_pages=10, download_pdfs=True, summarize=True):
        """
        初期化
        
        Args:
            driver: WebDriverオブジェクト
            max_pages (int): スクレイピングする最大ページ数
            download_pdfs (bool): PDFをダウンロードするかどうか
            summarize (bool): 要約機能を使用するかどうか
        """
        self.driver = driver
        self.max_pages = max_pages
        self.download_pdfs = download_pdfs
        self.summarize = summarize
        self.url = TARGET_URL
        self.downloaded_pdfs = []
    
    def scrape(self):
        """
        スクレイピングを実行する
        
        Returns:
            tuple: (事例データのリスト, ダウンロードしたPDFファイルのリスト)
        """
        try:
            # ページにアクセス
            logger.info(f"Hitachi事例ページにアクセス中: {self.url}")
            self.driver.get(self.url)
            
            # ランダムな待機時間
            wait_time = random.uniform(3, 5)
            logger.info(f"{wait_time}秒待機中...")
            time.sleep(wait_time)
            
            # Cookie同意ボタンをクリック（存在する場合）
            self._accept_cookies()
            
            # 事例リストを取得
            case_data = []
            current_page = 1
            
            while current_page <= self.max_pages:
                logger.info(f"ページ {current_page}/{self.max_pages} を処理中...")
                
                # ページの完全読み込みを待機
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )
                
                # 事例リストを取得
                page_cases = self._extract_case_list()
                case_data.extend(page_cases)
                
                # PDFダウンロード
                if self.download_pdfs:
                    self._download_case_pdfs(page_cases)
                
                # 次のページへ遷移
                if not self._go_to_next_page():
                    break
                
                current_page += 1
                time.sleep(random.uniform(2, 4))  # ページ間の待機
            
            # 詳細情報を取得
            detailed_data = self._process_cases(case_data)
            
            return detailed_data, self.downloaded_pdfs
            
        except Exception as e:
            logger.error(f"スクレイピング中にエラーが発生しました: {str(e)}", exc_info=True)
            return [], []
    
    def _accept_cookies(self):
        """Cookie同意ボタンをクリック"""
        try:
            cookie_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.cookie-consent__agree"))
            cookie_button.click()
            logger.info("Cookie同意ボタンをクリックしました")
            time.sleep(1)
        except Exception as e:
            logger.info(f"Cookie同意ボタンが見つかりませんでした: {str(e)}")
    
    def _extract_case_list(self):
        """
        現在のページから事例リストを抽出
        
        Returns:
            list: 事例データのリスト
        """
        logger.info("事例リストを抽出中...")
        case_data = []
        
        try:
            # 事例コンテナを取得
            case_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.case-list"))
            )
            
            # 各事例カードを取得
            case_cards = case_container.find_elements(By.CSS_SELECTOR, "div.case-card")
            logger.info(f"見つかった事例カード数: {len(case_cards)}")
            
            for card in case_cards:
                try:
                    # タイトルとURLを取得
                    title_element = card.find_element(By.CSS_SELECTOR, "h3.case-title a")
                    title = title_element.text.strip()
                    url = title_element.get_attribute("href")
                    
                    # 業種とソリューションを取得
                    industry = ""
                    solution = ""
                    try:
                        meta_elements = card.find_elements(By.CSS_SELECTOR, "div.case-meta span")
                        if len(meta_elements) >= 2:
                            industry = meta_elements[0].text.strip()
                            solution = meta_elements[1].text.strip()
                    except:
                        pass
                    
                    # PDFリンクを取得
                    pdf_url = ""
                    try:
                        pdf_link = card.find_element(By.CSS_SELECTOR, "a.case-pdf")
                        pdf_url = pdf_link.get_attribute("href")
                    except:
                        pass
                    
                    if url:
                        case_data.append({
                            "タイトル": title,
                            "URL": url,
                            "業種": industry,
                            "ソリューション": solution,
                            "PDF_URL": pdf_url,
                            "企業": "Hitachi"  # デフォルト値
                        })
                        logger.info(f"事例を追加: {title}")
                        
                except Exception as e:
                    logger.error(f"事例カード処理中にエラー: {str(e)}")
        
        except Exception as e:
            logger.error(f"事例リスト抽出中にエラー: {str(e)}")
            # 代替方法で取得を試みる
            return self._fallback_extract_case_list()
        
        return case_data
    
    def _fallback_extract_case_list(self):
        """代替方法で事例リストを抽出"""
        logger.warning("標準的な方法で事例リストを取得できませんでした。代替方法を試します...")
        case_data = []
        
        try:
            # ページ内のすべてのリンクを取得
            all_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='case']")
            
            for link in all_links:
                try:
                    url = link.get_attribute("href")
                    title = link.text.strip()
                    
                    if url and title and "/case/" in url:
                        case_data.append({
                            "タイトル": title,
                            "URL": url,
                            "企業": "Hitachi"
                        })
                        logger.info(f"代替方法で事例を追加: {title}")
                except:
                    continue
        
        except Exception as e:
            logger.error(f"代替方法でも事例リストを取得できませんでした: {str(e)}")
        
        return case_data
    
    def _download_case_pdfs(self, case_data):
        """事例に関連するPDFをダウンロード"""
        if not self.download_pdfs:
            return
            
        logger.info("PDFダウンロードを開始します...")
        
        for case in case_data:
            pdf_url = case.get("PDF_URL", "")
            if pdf_url:
                try:
                    # PDFファイル名を生成
                    pdf_name = f"{case['タイトル'][:50]}.pdf".replace("/", "_")
                    pdf_path = os.path.join(self.download_dir, pdf_name)
                    
                    # PDFをダウンロード
                    response = requests.get(pdf_url, stream=True)
                    with open(pdf_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    
                    self.downloaded_pdfs.append(pdf_path)
                    logger.info(f"PDFをダウンロードしました: {pdf_name}")
                    
                except Exception as e:
                    logger.error(f"PDFダウンロード中にエラー: {str(e)}")
    
    def _go_to_next_page(self):
        """次のページに遷移"""
        try:
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.pagination-next"))
            )
            
            # ボタンが無効になっていないか確認
            if "disabled" in next_button.get_attribute("class"):
                logger.info("最終ページに到達しました")
                return False
            
            # 次のページへ移動
            next_button.click()
            logger.info("次のページへ移動しました")
            
            # ページ読み込みを待機
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.case-list"))
            )
            
            return True
            
        except Exception as e:
            logger.info(f"次のページへ移動できませんでした: {str(e)}")
            return False
    
    def _process_cases(self, case_data):
        """
        各事例の詳細情報を処理
        
        Args:
            case_data (list): 事例データのリスト
        
        Returns:
            list: 処理済みの詳細データ
        """
        detailed_data = []
        
        for idx, case in enumerate(case_data):
            try:
                logger.info(f"事例 {idx+1}/{len(case_data)} 処理中: {case['タイトル']}")
                
                # 詳細ページにアクセス
                self.driver.get(case["URL"])
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.case-detail"))
                
                # ページ内容を解析
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                
                # 基本情報を抽出
                case_info = {
                    "タイトル": case["タイトル"],
                    "URL": case["URL"],
                    "企業": case["企業"],
                    "業種": case["業種"],
                    "ソリューション": case["ソリューション"],
                    "PDF_URL": case.get("PDF_URL", "")
                }
                
                # 詳細セクションを抽出
                detail_sections = soup.select("div.case-detail-section")
                for section in detail_sections:
                    title = section.find("h3")
                    if title:
                        section_title = title.text.strip()
                        content = "\n".join(p.text.strip() for p in section.find_all("p"))
                        case_info[section_title] = content
                
                # 要約機能が有効な場合
                if self.summarize:
                    content = "\n".join(f"{k}: {v}" for k, v in case_info.items() if k not in ["URL", "PDF_URL"])
                    
                    # 要約を生成
                    summary = generate_with_gpt4o_mini(
                        f"タイトル: {case['タイトル']}\n\n{content}",
                        SUMMARY_SYSTEM_MESSAGE
                    )
                    case_info["要約"] = summary
                    
                    # 企業名を抽出して更新
                    extracted_company = extract_company_from_title(case["タイトル"])
                    if extracted_company:
                        case_info["企業"] = extracted_company
                    
                    # 業種を再分類
                    web_industry = determine_industry_with_fallback(
                        case_info["企業"],
                        content
                    )
                    if web_industry != "その他":
                        case_info["業種"] = web_industry
                
                detailed_data.append(case_info)
                time.sleep(random.uniform(1, 3))  # リクエスト間隔
            
            except Exception as e:
                logger.error(f"事例詳細処理中にエラー: {str(e)}")
                detailed_data.append(case)  # 最低限の情報を保持
        
        return detailed_data