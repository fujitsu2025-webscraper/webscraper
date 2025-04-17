"""
OpenAI APIを使用するためのユーティリティ
"""
import os
import logging
import time
import openai
from openai import OpenAI

logger = logging.getLogger("nri_scraper")

def generate_with_gpt4o_mini(prompt, system_message, max_tokens=1000, temperature=0.7):
    """
    GPT-4o-miniを使用してテキストを生成する
    
    Args:
        prompt (str): 生成のためのプロンプト
        system_message (str): システムメッセージ
        max_tokens (int, optional): 生成する最大トークン数
        temperature (float, optional): 生成の多様性を制御するパラメータ
    
    Returns:
        str: 生成されたテキスト
    """
    try:
        # APIキーの取得
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEYが設定されていません")
            return "APIキーが設定されていないため、要約を生成できませんでした"
        
        # OpenAIクライアントの初期化
        client = OpenAI(api_key=api_key)
        
        # リトライ回数とバックオフ時間の設定
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # GPT-4o-miniによるテキスト生成
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                # 生成されたテキストを取得
                generated_text = response.choices[0].message.content
                
                return generated_text
                
            except openai.RateLimitError:
                # レート制限エラーの場合、バックオフして再試行
                if attempt < max_retries - 1:
                    sleep_time = retry_delay * (2 ** attempt)
                    logger.warning(f"レート制限に達しました。{sleep_time}秒後に再試行します...")
                    time.sleep(sleep_time)
                else:
                    logger.error("レート制限エラーが続いています。後でもう一度お試しください。")
                    return "レート制限のため、要約を生成できませんでした"
                    
            except Exception as e:
                logger.error(f"OpenAI API呼び出し中にエラーが発生しました: {str(e)}")
                if attempt < max_retries - 1:
                    sleep_time = retry_delay * (2 ** attempt)
                    logger.warning(f"{sleep_time}秒後に再試行します...")
                    time.sleep(sleep_time)
                else:
                    return f"エラーのため、要約を生成できませんでした: {str(e)}"
        
    except Exception as e:
        logger.error(f"テキスト生成中にエラーが発生しました: {str(e)}")
        return "エラーのため、要約を生成できませんでした"
