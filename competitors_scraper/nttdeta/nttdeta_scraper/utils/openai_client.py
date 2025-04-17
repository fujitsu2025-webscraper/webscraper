"""
OpenAI APIを使用するためのクライアント関数
"""
import os
import time
import logging
import openai
from openai import OpenAI

logger = logging.getLogger("nttdata_scraper")

def generate_with_gpt4o_mini(prompt, system_message, max_tokens=1000, temperature=0.7):
    """
    GPT-4o-miniを使用してテキストを生成する
    
    Args:
        prompt (str): プロンプト
        system_message (str): システムメッセージ
        max_tokens (int): 生成する最大トークン数
        temperature (float): 温度パラメータ
    
    Returns:
        str: 生成されたテキスト
    """
    # APIキーを環境変数から取得
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEYが設定されていません")
        return "APIキーが設定されていないため、生成できませんでした"
    
    # OpenAIクライアントを初期化
    client = OpenAI(api_key=api_key)
    
    # リトライ設定
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # GPT-4o-miniを使用してテキストを生成
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # 生成されたテキストを返す
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"GPT-4o-mini生成中にエラー（試行{attempt+1}/{max_retries}）: {str(e)}")
            
            if attempt < max_retries - 1:
                # リトライ前に待機
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数バックオフ
            else:
                logger.error(f"GPT-4o-mini生成に{max_retries}回失敗しました")
                return "テキスト生成に失敗しました"
