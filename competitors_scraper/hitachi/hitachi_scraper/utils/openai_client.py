"""
OpenAI APIを使用するためのモジュール
"""
import os
import time
import logging
import openai
from dotenv import load_dotenv

logger = logging.getLogger("hitachi_scraper")

# .envファイルから環境変数を読み込む
load_dotenv()

# OpenAI APIキーを環境変数から設定
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_with_gpt4o_mini(prompt, system_message, max_tokens=1000, temperature=0.7, retry_count=3):
    """
    GPT-4o-miniを使用してテキストを生成する関数
    
    Args:
        prompt (str): ユーザープロンプト
        system_message (str): システムメッセージ
        max_tokens (int): 生成する最大トークン数
        temperature (float): 生成の多様性を制御するパラメータ
        retry_count (int): エラー時の再試行回数
    
    Returns:
        str: 生成されたテキスト
    """
    for attempt in range(retry_count):
        try:
            # OpenAI APIを使用して要約を生成
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # 応答から要約テキストを抽出
            result = response.choices[0].message.content.strip()
            return result
        except Exception as e:
            logger.error(f"OpenAI APIでエラーが発生 (試行 {attempt+1}/{retry_count}): {str(e)}")
            if attempt < retry_count - 1:
                wait_time = 2 * (attempt + 1)  # 指数バックオフ
                logger.info(f"{wait_time}秒待機してリトライします...")
                time.sleep(wait_time)
            else:
                logger.error(f"OpenAI API呼び出しが {retry_count} 回失敗しました")
                return "APIエラーのため生成できませんでした。"
