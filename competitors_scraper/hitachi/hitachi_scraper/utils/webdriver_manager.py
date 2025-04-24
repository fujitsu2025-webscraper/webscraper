"""
WebDriverの初期化と管理を行うモジュール
"""
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger("hitachi_scraper")

def initialize_webdriver(headless=False, options_config=None):
    """
    WebDriverを初期化する
    
    Args:
        headless (bool): ヘッドレスモードで実行するかどうか
        options_config (dict): WebDriverのオプション設定
    
    Returns:
        webdriver.Chrome: 初期化されたWebDriverオブジェクト
    """
    if options_config is None:
        from ..config.settings import WEBDRIVER_OPTIONS
        options_config = WEBDRIVER_OPTIONS
    
    options = Options()
    
    # ヘッドレスモードの設定
    if headless:
        options.add_argument('--headless')
        logger.info("ヘッドレスモードで実行します")
    else:
        logger.info("ブラウザを表示して実行します")
    
    # オプションの設定
    if options_config.get('no_sandbox', True):
        options.add_argument('--no-sandbox')
    
    if options_config.get('disable_dev_shm_usage', True):
        options.add_argument('--disable-dev-shm-usage')
    
    # ウィンドウサイズを設定
    window_size = options_config.get('window_size', (1920, 1080))
    options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')
    
    # ユーザーエージェントを設定
    user_agent = options_config.get('user_agent')
    if user_agent:
        options.add_argument(f'--user-agent={user_agent}')
    
    # JavaScriptを有効にする
    if options_config.get('enable_javascript', True):
        options.add_argument('--enable-javascript')
    
    # 自動化されたテストソフトウェアによって制御されていることを隠す
    exclude_switches = options_config.get('exclude_switches')
    if exclude_switches:
        options.add_experimental_option('excludeSwitches', exclude_switches)
    
    use_automation_extension = options_config.get('use_automation_extension')
    if use_automation_extension is not None:
        options.add_experimental_option('useAutomationExtension', use_automation_extension)
    
    # WebDriverの初期化
    logger.info("WebDriverを初期化中...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    return driver
