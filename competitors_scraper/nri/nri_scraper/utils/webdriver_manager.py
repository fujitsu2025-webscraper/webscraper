"""
WebDriverを初期化・管理するためのモジュール
"""
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from ..config.settings import WEBDRIVER_OPTIONS

logger = logging.getLogger("nri_scraper")

def initialize_webdriver(headless=False):
    """
    WebDriverを初期化する
    
    Args:
        headless (bool): ヘッドレスモードで実行するかどうか
    
    Returns:
        webdriver.Chrome: 初期化されたWebDriverオブジェクト
    """
    try:
        logger.info("WebDriverを初期化しています...")
        
        # Chrome オプションの設定
        chrome_options = Options()
        
        # ヘッドレスモードの設定
        if headless:
            chrome_options.add_argument("--headless")
            logger.info("ヘッドレスモードで実行します")
        
        # 設定ファイルからのオプション適用
        if WEBDRIVER_OPTIONS.get('no_sandbox', False):
            chrome_options.add_argument("--no-sandbox")
        
        if WEBDRIVER_OPTIONS.get('disable_dev_shm_usage', False):
            chrome_options.add_argument("--disable-dev-shm-usage")
        
        if 'window_size' in WEBDRIVER_OPTIONS:
            width, height = WEBDRIVER_OPTIONS['window_size']
            chrome_options.add_argument(f"--window-size={width},{height}")
        
        if 'user_agent' in WEBDRIVER_OPTIONS:
            chrome_options.add_argument(f"user-agent={WEBDRIVER_OPTIONS['user_agent']}")
        
        if WEBDRIVER_OPTIONS.get('enable_javascript', True):
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.javascript": 1
            })
        
        if 'exclude_switches' in WEBDRIVER_OPTIONS:
            chrome_options.add_experimental_option("excludeSwitches", WEBDRIVER_OPTIONS['exclude_switches'])
        
        if 'use_automation_extension' in WEBDRIVER_OPTIONS:
            chrome_options.add_experimental_option("useAutomationExtension", WEBDRIVER_OPTIONS['use_automation_extension'])
        
        # WebDriverの初期化
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # タイムアウトの設定
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        logger.info("WebDriverの初期化が完了しました")
        return driver
        
    except Exception as e:
        logger.error(f"WebDriverの初期化中にエラーが発生しました: {str(e)}")
        raise
