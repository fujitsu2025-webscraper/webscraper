"""
OpenAI APIを使用したLLM機能モジュール
"""
import re
import logging
import openai

logger = logging.getLogger("ItmediaScraper")

def summarize_with_llm(url, title, api_key):
    """
    OpenAIのAPIを使用してURLから内容を要約
    LLMは直接URLにアクセスして内容を読み取り要約する
    
    Args:
        url: 記事のURL
        title: 記事のタイトル
        api_key: OpenAI APIキー
        
    Returns:
        str: 要約内容
    """
    if not api_key:
        logger.warning("APIキーが設定されていないため、LLMによる要約をスキップします")
        return ""
        
    # LLM用のプロンプトを作成
    prompt = f"""
    以下のURLにアクセスして、記事を要約してください:
    
    URL: {url}
    タイトル: {title}
    
    以下の要素を含めて要約を作成してください：
    1. 主要なポイント（何が、なぜ、どのように）
    2. 技術的な詳細（該当する場合）
    3. ビジネスインパクトや実用性
    4. 今後の展望や課題
    
    要約は200〜300文字程度で、以下の点に注意して作成してください：
    - 具体的な数値、日付、組織名は正確に含める
    - 技術用語は原文のまま使用
    - 主観的な評価は避け、客観的な事実を中心に記述
    - 箇条書きは使用せず、文章として構成
    
    【出力形式】
    要約: [要約内容]
    """
    
    # OpenAI APIを呼び出し
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは日本のAIとテクノロジーに関するニュース記事を要約する専門家です。URLにアクセスして記事を読み、要約ができます。要約を書く際は以下の点を重視してください：\n1. 技術的な正確性\n2. 事実関係の明確な記述\n3. 重要な数値やデータの保持\n4. 簡潔かつ論理的な文章構成\n\n「記事では、」「この記事では、」「contentの記事では、」などの冗長な表現は使わず、内容を直接簡潔に説明してください。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2500,  # トークン数を増やして詳細な要約に対応
            temperature=0.1  # 温度を0.1に保持して決定論的な出力を維持
        )
        
        # レスポンステキストを抽出
        response_text = response.choices[0].message.content.strip()
        
        # 要約部分を抽出
        content = ""
        
        # 要約部分を抽出
        summary_match = re.search(r'要約:\s*(.*?)(?=\n\n|$)', response_text, re.DOTALL)
        if summary_match:
            content = summary_match.group(1).strip()
        else:
            # 要約部分が見つからない場合は全体を要約として扱う
            logger.warning(f"要約部分が正しく抽出できませんでした。全体を要約として使用します: {url}")
            content = response_text
            
        return content
            
    except Exception as e:
        logger.error(f"Error in summarize_with_llm: {str(e)}")
        return ""

def categorize_with_llm(url, title, api_key, custom_categories):
    """
    OpenAIのAPIを使用してURLから記事のカテゴリを決定する
    二段階分類アプローチを実装し、まず「研究動向」カテゴリかどうかを判断してから
    適切なカテゴリに分類する
    
    Args:
        url: 記事のURL
        title: 記事のタイトル
        api_key: OpenAI APIキー
        custom_categories: カスタムカテゴリのリスト
        
    Returns:
        str: カスタムカテゴリ
    """
    if not api_key:
        return None
        
    try:
        # ステップ1: 記事が「研究動向」カテゴリに属するかどうかを判断
        is_research = is_research_category(url, title, api_key)
        logger.info(f"First step classification for '{title}': {'研究動向' if is_research else '非研究動向'}")
        
        # ステップ2: 最終的なカテゴリ分類
        return final_categorization(url, title, api_key, custom_categories, is_research)
        
    except Exception as e:
        logger.error(f"Error in LLM categorization: {str(e)}")
        return None

def is_research_category(url, title, api_key):
    """
    記事が「研究動向」カテゴリに属するかどうかを判断する
    
    Args:
        url: 記事のURL
        title: 記事のタイトル
        api_key: OpenAI APIキー
        
    Returns:
        bool: 研究動向カテゴリに属する場合はTrue、それ以外はFalse
    """
    try:
        # 研究動向に関連する可能性が高いキーワード
        research_keywords = ["研究", "論文", "学会", "理論", "アルゴリズム", "実験", "開発中"]
        
        # 明らかに研究動向ではないキーワードのリスト（拡充）
        non_research_keywords = [
            "発売", "提供開始", "リリース", "新製品", "新サービス", "搭載", "対応", 
            "アップデート", "バージョンアップ", "機能追加", "新機能", "公開", "ベータ版", "正式版", "サブスク", 
            "月額", "値下げ", "無料提供", "新アプリ", "iOS版", "Android版", "アプリ配信", "インストール"]
        
        # 企業名リスト（拡充）
        company_names = [
            "Google", "Microsoft", "OpenAI", "Meta", "Amazon", "Apple", "IBM", "NVIDIA", 
            "AMD", "Intel", "富士通", "NEC", "日立", "東芝", "パナソニック", "ソニー", 
            "キヤノン", "リコー", "NTT", "KDDI", "ソフトバンク", "楽天", "LINE", 
            "DeNA", "サイバーエージェント", "Anthropic", "GitHub", "Stability AI",
            "Midjourney", "Runway", "Hugging Face", "Salesforce", "Adobe", "HP", "Dell",
            "Lenovo", "ASUS", "Acer"
        ]
        
        # 製品・サービスに関連する特定のパターン
        product_service_patterns = [
            r'新(機能|サービス|製品|ツール)',
            r'(機能|サービス)を(追加|拡張)',
            r'(発売|リリース|提供開始)',
            r'バージョンアップ',
            r'アップデート',
            r'新たに登場',
            r'新バージョン'
        ]
        
        # タイトルの特徴に基づく事前判定
        
        # 1. 企業名で始まるタイトルは多くの場合、製品・サービス発表
        for company in company_names:
            if title.startswith(f"{company}、") or title.startswith(f"{company}が") or title.startswith(f"{company}は"):
                logger.info(f"企業名「{company}」で始まるタイトルのため、研究動向ではないと判断: {title}")
                return False
        
        # 2. 製品・サービスパターンに一致する場合
        for pattern in product_service_patterns:
            if re.search(pattern, title):
                logger.info(f"製品・サービスパターン「{pattern}」に一致するため、研究動向ではないと判断: {title}")
                return False
        
        # 3. 非研究キーワードを含み、研究キーワードを含まない場合
        if any(keyword in title for keyword in non_research_keywords) and not any(keyword in title for keyword in research_keywords):
            logger.info(f"非研究キーワードを含み、研究キーワードを含まないため「研究動向」ではないと判断: {title}")
            return False
        
        # 4. 企業名の後に「〜を発表」「〜を開始」などがある場合
        company_announcement_pattern = r'(.+社|.+[株]|' + '|'.join(company_names) + r').+[、は](.+を発表|.+を開始|.+を提供|.+を搭載|.+に対応)'
        if re.search(company_announcement_pattern, title) and not any(keyword in title for keyword in ["研究成果", "論文", "学会", "理論"]):
            # 学術的な文脈でない限り、研究動向ではない可能性が高い
            if not any(academic_term in title for academic_term in ["論文", "学会", "大学", "理論"]):
                logger.info(f"企業の発表パターンだが、学術的文脈ではないため「研究動向」ではない可能性が高い: {title}")
                return False
        
        # 5. 「試してみた」「レビュー」などのユーザー体験系は研究動向ではない
        user_experience_keywords = ["試してみた", "レビュー", "使ってみた", "体験", "インプレッション", "ハンズオン"]
        if any(keyword in title for keyword in user_experience_keywords):
            logger.info(f"ユーザー体験系キーワード「{[k for k in user_experience_keywords if k in title]}」を含むため、研究動向ではないと判断: {title}")
            return False
        
        # 6. 「トップ人材は、生成AIをこう使う」などの連載記事は研究動向ではない
        if "トップ人材は、生成AIをこう使う" in title or "連載" in title:
            logger.info(f"連載記事のため、研究動向ではないと判断: {title}")
            return False
        
        # 7. 「〜Day」「〜PC」などの製品・イベント関連は研究動向ではない
        if re.search(r'(Day|PC|イベント|カンファレンス)', title):
            logger.info(f"製品・イベント関連キーワードを含むため、研究動向ではないと判断: {title}")
            return False
        
        # 8. 「〜氏」「〜さん」などの人物インタビュー系は研究動向ではない
        if re.search(r'[氏|さん]', title):
            logger.info(f"人物インタビュー系キーワードを含むため、研究動向ではないと判断: {title}")
            return False
            
        # 9. 特定の製品名を含む場合は研究動向ではない
        product_names = ["ChatGPT", "Gemini", "Claude", "Copilot", "DALL-E", "Midjourney", "Stable Diffusion", "iPhone", "iPad"]
        if any(product in title for product in product_names) and not any(keyword in title for keyword in ["研究成果", "論文", "学会"]):
            logger.info(f"製品名「{[p for p in product_names if p in title]}」を含み、学術研究キーワードを含まないため、研究動向ではないと判断: {title}")
            return False
            
        # 10. 「研究」を含むが「研究が発表」のような形式の場合は、研究動向の可能性は低い
        if "研究" in title and any(phrase in title for phrase in ["研究が発表", "研究を発表", "研究発表"]):
            # 学術的な文脈でない限り、研究動向ではない可能性が高い
            if not any(academic_term in title for academic_term in ["論文", "学会", "大学", "理論"]):
                logger.info(f"「研究発表」を含むが学術的文脈ではないため、研究動向ではない可能性が高い: {title}")
                return False
        
        # 研究動向カテゴリの判断に特化したプロンプトを作成
        prompt = f"""
        記事のタイトルとURLから、この記事が「研究動向」カテゴリに属するかどうかを厳密に判断してください。
        
        **記事情報:**
        タイトル: {title}
        URL: {url}
        
        **「研究動向」の定義（極めて厳格に適用してください）:**
        「研究動向」カテゴリは、**学術論文として発表された、または研究機関・大学による基礎研究段階にある技術・理論の研究**に関する記事に限定されます。製品発表や商用サービスの記事は例外なく「研究動向」ではありません。
        
        **「研究動向」に該当する記事の特徴:**
        * 学術論文や学会で発表された研究成果に関する報告
        * 理論的なAIアルゴリズムや手法の発明・改良に関する内容
        * 研究機関や大学が発表した基礎研究の成果
        * まだ実用化されていない実験的・理論的なAI技術の進展
        * 査読済みの学術的研究に基づく新しい発見
        * 「研究チーム」「研究者」「論文」「実験」「理論」などの単語が含まれている
        
        **「研究動向」では決してない記事の特徴:**
        * 製品の発売や販売に関する発表（「発売」「提供開始」「リリース」などを含む）
        * 企業の導入事例やビジネス応用（「導入」「活用事例」「採用」などを含む）
        * 企業のサービス提供や機能追加（「サービス」「機能追加」「開始」などを含む）
        * マーケットや市場に関する調査や分析（「市場調査」「シェア」「予測」などを含む）
        * インタビューや業界動向（「インタビュー」「〜氏」「〜さん」などを含む）
        * すでに実用化されたAI技術の紹介や応用
        * イベントレポートや展示会の内容（「イベント」「展示会」などを含む）
        * 商品発表、製品リリース、サービス開始の発表
        * 企業による製品やサービスへのAI機能の搭載や追加
        
        **判断の指針（必ず従ってください）:**
        1. タイトルに「発売」「提供」「導入」「開始」「発表」「搭載」「対応」などのキーワードがある場合は、ほぼ確実に「研究動向」ではありません。
        2. 企業名に続いて「〜を発表」「〜を開始」などの表現がある場合は、ほとんどの場合「研究動向」ではなく製品・サービスの発表です。
        3. 基礎研究の成果であっても、すでに製品化・サービス化されている場合は「研究動向」ではなく、「製品・サービス」や「AI技術基盤」に分類すべきです。
        4. カテゴリを判断する際は、記事の主題が「学術研究の成果報告」であるかどうかを最重視してください。
        5. 「研究」という言葉が含まれていても、商用目的の開発や製品紹介の場合は「研究動向」ではありません。
        6. 企業名が記事タイトルの冒頭にある場合は、ほとんどの場合「研究動向」ではなく、製品・サービスの発表です。
        
        **判断例（必ず参照してください）:**
        * 「深層学習を用いた新しい画像認識アルゴリズムの研究」→「研究動向」に該当する
        * 「メタが開発中の多言語AI翻訳モデルの研究成果を発表」→「研究動向」に該当する
        * 「GPUを用いた機械学習の高速化に関する理論研究」→「研究動向」に該当する
        * 「新型AIカメラが発売、全モデルに対応」→「研究動向」には該当しない（製品発売のため）
        * 「企業がAIチャットボットサービスの提供を開始」→「研究動向」には該当しない（サービス開始のため）
        * 「AIを活用した業務改善事例：コスト削減と効率化」→「研究動向」には該当しない（応用事例のため）
        * 「ソニーとラズパイ共同開発のAIカメラが発売」→「研究動向」には該当しない（製品発売のため）
        * 「富士通、大規模言語モデル「Takane」提供開始　「世界一の日本語性能を持つ」とうたう」→「研究動向」には該当しない（製品開発のため）
        * 「リコー、モデルマージで"GPT-4レベル"の大規模言語モデル開発」→「研究動向」には該当しない（製品開発のため）
        * 「いらっしゃいませなのだ！──ずんだもんが接客してくれる「AI売り子」」→「研究動向」には該当しない（サービス/製品紹介のため）
        * 「楽天モバイル、メッセージアプリ「Rakuten Link」に生成AI機能を搭載」→「研究動向」には該当しない（製品機能追加のため）
        * 「GitHub Copilotが「Gemini 1.5 Pro」「o1-preview」「Claude 3.5 Sonnet」に対応」→「研究動向」には該当しない（製品機能追加のため）
        
        この記事は「研究動向」カテゴリに該当しますか？「はい」または「いいえ」で明確に回答してください。
        """
        
        # OpenAI APIを呼び出し
        client = openai.OpenAI(api_key=api_key)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたはAIニュース記事を分析し、「研究動向」カテゴリに該当するかどうかを厳密に判断する専門家です。「研究動向」の定義を厳格に適用し、製品発表や商用サービスの記事を「研究動向」と誤分類しないようにしてください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,  # トークン数を増やして長い記事にも対応
                temperature=0.1
            )
            
            # レスポンステキストを抽出
            response_text = response.choices[0].message.content.strip().lower()
            
            # 「はい」または「いいえ」の回答を抽出
            is_research = "はい" in response_text or "yes" in response_text
            
            logger.info(f"LLMによる「研究動向」判定結果: {is_research} (タイトル: {title})")
            return is_research
            
        except openai.APIError as e:
            logger.error(f"OpenAI API Error: {str(e)}")
            return False
        except openai.RateLimitError as e:
            logger.error(f"OpenAI Rate Limit Error: {str(e)}")
            return False
        except openai.APIConnectionError as e:
            logger.error(f"OpenAI API Connection Error: {str(e)}")
            return False
        except openai.APITimeoutError as e:
            logger.error(f"OpenAI API Timeout Error: {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"研究動向カテゴリ判定中にエラー: {str(e)}")
        # エラーが発生した場合はデフォルトとして研究動向ではないと判断
        return False

def format_categories_for_prompt_non_research(categories):
    """
    研究動向を除外したカテゴリリストをプロンプト用にフォーマットする
    
    Args:
        categories: カテゴリリスト
        
    Returns:
        str: フォーマットされたカテゴリリスト
    """
    # 研究動向を除外
    non_research_categories = [cat for cat in categories if cat != "研究動向"]
    
    # カンマで区切られたリストとして返す
    return ", ".join([f"「{cat}」" for cat in non_research_categories])

def apply_heuristic_categorization(title):
    """
    タイトルに基づくヒューリスティックカテゴリ分類
    
    Args:
        title: 記事のタイトル
        
    Returns:
        str: 推定されるカテゴリ
    """
    # 各カテゴリに関連するキーワード
    product_service_keywords = ["発売", "リリース", "新製品", "新サービス", "搭載", "対応", 
                                "アップデート", "バージョンアップ", "機能追加", "新機能", "公開", "ベータ版", "正式版", "サブスク", 
                                "月額", "値下げ", "無料提供", "新アプリ", "iOS版", "Android版", "アプリ配信", "インストール"]
    tech_base_keywords = ["大規模言語モデル", "LLM", "プラットフォーム", "API", "基盤", "開発", "Gemini", "Claude", 
                          "GPT", "Takane", "Llama", "Mistral", "Mixtral", "ファインチューニング", "推論", "トレーニング", "学習", 
                          "モデル", "パラメータ", "トークナイザー", "エンベディング", "ベクトル検索", "RAG", "TGI", "vLLM", 
                          "開発キット", "SDK", "GitHub", "オープンソース", "開発者向け", "自社開発", "フレームワーク", 
                          "開発環境", "モデルマージ", "蒸留", "量子化", "プロンプトエンジニアリング", "微調整"]
    efficiency_keywords = ["業務効率", "自動化", "コスト削減", "生産性", "業務改善", "効率化", "工数削減", "人材不足", 
                           "人手不足", "省力化", "省人化", "RPA", "ワークフロー", "業務プロセス", "BPR", "バックオフィス", 
                           "社内業務", "内部業務", "業務改革", "ホワイトカラー", "事務作業", "経費精算", "会議議事録", "書類作成", 
                           "マニュアル作成", "ナレッジ管理", "顧客対応", "問い合わせ対応", "コールセンター", "チャットボット導入"]
    social_impl_keywords = ["社会実装", "応用", "実証", "活用事例", "導入事例", "接客", "売り子", "導入", 
                            "実用化", "商用化", "現場導入", "医療", "教育", "農業", "小売", "流通", "物流", "金融", "保険", 
                            "不動産", "建設", "製造", "エネルギー", "交通", "通信", "放送", "エンターテイメント", "スポーツ", 
                            "接客支援", "顧客体験", "UX改善", "店舗", "病院", "学校", "大学", "研究所", "実証実験"]
    market_keywords = ["市場", "予測", "動向", "調査", "トレンド", "シェア", "経営", "戦略", "投資", "競争", 
                       "業界", "ビジネスモデル", "収益", "決算", "四半期", "売上", "利益", "成長率", "分析", "レポート", 
                       "白書", "調査報告", "アンケート", "意識調査", "利用実態", "消費者", "ユーザー", "導入障壁", "課題", 
                       "人材育成", "仕事を奪う", "失業", "雇用", "働き方", "企業戦略", "経営戦略"]
    security_keywords = ["セキュリティ", "倫理", "著作権", "リスク", "安全性", "ガイドライン", "プライバシー", "無断", 
                         "脆弱性", "フェイク", "偽情報", "デマ", "ディープフェイク", "なりすまし", "改ざん", "漏洩", "情報漏洩", 
                         "攻撃", "防御", "対策", "保護", "コンプライアンス", "法的責任", "訴訟", "監査", "認証", "暗号化", 
                         "悪用", "誤用", "バイアス", "差別", "公平性", "透明性", "説明可能性", "XAI", "中止"]
    policy_keywords = ["政策", "規制", "法律", "ガイドライン", "政府", "省庁", "IPA", "公取委", "ハローワーク", 
                       "厚労省", "経産省", "総務省", "文科省", "デジタル庁", "内閣府", "国会", "法案", "条例", "自治体", 
                       "規則", "基準", "審議会", "検討会", "報告書", "パブコメ", "意見募集", "国際標準", "ISO", "予算", 
                       "補助金", "助成金", "税制優遇", "特区", "実証特区", "AI戦略", "デジタル戦略", "DX戦略"]
    
    # デフォルトのカテゴリ（最も一般的な分類）
    default_category = "社会実装・応用"
    
    # 企業名パターン
    company_pattern = r'(.+社|.+[株]|楽天|Google|Microsoft|Meta|OpenAI|富士通|リコー|キヤノン|ソニー|パナソニック|日立|東芝|NEC|NTT|KDDI|ソフトバンク|GitHub)'
    
    # 「提供開始」は特別扱い - 大規模言語モデルやAI技術基盤の場合は「AI技術基盤」に分類
    if "提供開始" in title and any(keyword in title for keyword in tech_base_keywords):
        logger.info(f"大規模言語モデルの提供開始は「AI技術基盤」に分類: {title}")
        return "AI技術基盤"
    
    # キーワードに基づく分類
    if any(keyword in title for keyword in product_service_keywords):
        return "製品・サービス"
    elif any(keyword in title for keyword in tech_base_keywords):
        return "AI技術基盤"
    elif any(keyword in title for keyword in efficiency_keywords):
        return "業務効率化・自動化"
    elif any(keyword in title for keyword in social_impl_keywords):
        return "社会実装・応用"
    elif any(keyword in title for keyword in market_keywords):
        return "市場・ビジネス動向"
    elif any(keyword in title for keyword in security_keywords):
        return "セキュリティ・倫理"
    elif any(keyword in title for keyword in policy_keywords):
        return "政策・規制"
    
    # 特定のパターンに基づく分類
    if "AI売り子" in title or "接客" in title:
        return "社会実装・応用"
    elif "カメラ" in title and ("発売" in title or "提供" in title):
        return "製品・サービス"
    elif "大規模言語モデル" in title or "LLM" in title or "Takane" in title:
        return "AI技術基盤"
    else:
        # 企業名がタイトルに含まれる場合、多くは製品・サービスか社会実装
        if re.search(company_pattern, title) and ("、" in title or "は" in title):
            if "開発" in title or "技術" in title or "モデル" in title:
                return "AI技術基盤"
            else:
                return "製品・サービス"
    
    # どれにも該当しない場合はデフォルトカテゴリを返す
    return default_category

def final_categorization(url, title, api_key, custom_categories, is_research):
    """
    最終的なカテゴリ分類を行う
    
    Args:
        url: 記事のURL
        title: 記事のタイトル
        api_key: OpenAI APIキー
        custom_categories: カスタムカテゴリのリスト
        is_research: 研究動向カテゴリの場合はTrue
        
    Returns:
        str: 最終的なカテゴリ
    """
    try:
        # タイトルに基づく事前チェック - 明らかに製品・サービスや社会実装の場合
        if not is_research:
            # まずヒューリスティックで判断してみる
            heuristic_category = apply_heuristic_categorization(title)
            
            # 特別なケース: 富士通Takaneなどの大規模言語モデルは「AI技術基盤」に分類
            if ("大規模言語モデル" in title or "LLM" in title or "Takane" in title) and "提供開始" in title:
                logger.info(f"大規模言語モデルの提供開始は「AI技術基盤」に分類: {title}")
                return "AI技術基盤"
            
            # 明確なキーワードがある場合は直接ヒューリスティック結果を返す
            product_service_clear = ["発売", "提供開始", "リリース", "新製品", "新サービス", "搭載", "対応", "発表"]
            if any(keyword in title for keyword in product_service_clear) and heuristic_category == "製品・サービス":
                logger.info(f"明確な製品・サービスキーワードに基づきヒューリスティック分類を採用: {title} → {heuristic_category}")
                return heuristic_category
                
            # 企業名パターン
            company_announcement_pattern = r'(.+社|.+[株]|楽天|Google|Microsoft|Meta|OpenAI|富士通|リコー|キヤノン|ソニー|パナソニック|日立|東芝|NEC|NTT|KDDI|ソフトバンク|GitHub).+[、は](.+を発表|.+を開始|.+を提供|.+を搭載|.+に対応)'
            if re.search(company_announcement_pattern, title):
                # 大規模言語モデルやAI基盤技術に関する場合は「AI技術基盤」に分類
                if any(keyword in title for keyword in ["大規模言語モデル", "LLM", "Takane", "基盤", "モデル"]):
                    logger.info(f"企業の発表パターンだが、AI技術基盤に関連するキーワードを含むため「AI技術基盤」に分類: {title}")
                    return "AI技術基盤"
                else:
                    logger.info(f"企業の発表パターンに基づきヒューリスティック分類を採用: {title} → {heuristic_category}")
                    return heuristic_category
        
        if is_research:
            return "研究動向"
        
        # 研究動向以外のカテゴリを決定するためのプロンプトを作成
        prompt = f"""
        あなたは日本のAIニュース記事を分析し、指定されたカテゴリに分類する専門家AIです。
        
        **前提条件:**
        この記事は「研究動向」カテゴリに該当しないことが既に確認されています。したがって「研究動向」は選択肢から除外してください。
        
        **タスク:**
        提供された記事のタイトルとURLに基づいて記事の内容を理解し、以下の指示に**厳密に従って**最適なカテゴリを1つだけ選択してください。
        
        **記事情報:**
        タイトル: {title}
        URL: {url}
        
        **カテゴリ選択肢（「研究動向」は除外）:**
        {format_categories_for_prompt_non_research(custom_categories)}
        
        **各カテゴリの明確な区別:**
        * **製品・サービス**: 最終ユーザーが利用する製品やサービスに関する記事。「発売」「提供開始」「リリース」などのキーワードを含むことが多い。例：新製品発表、サービス開始など。
        
        * **AI技術基盤**: AIを開発・運用するためのプラットフォームやLLMなどの基盤技術に関する記事。大規模言語モデル、APIサービス、AIクラウド基盤など。富士通Takaneやリコーのモデルマージなどの企業による大規模言語モデル開発・提供なども含まれる。
        
        * **業務効率化・自動化**: 企業内の業務プロセス改善に関する記事。AIによる業務効率化、RPA、生産性向上施策など。「効率化」「自動化」「コスト削減」などのキーワードを含むことが多い。
        
        * **社会実装・応用**: 医療・教育・農業・小売など特定分野でのAI応用事例に関する記事。「いらっしゃいませなのだ！──ずんだもんが接客してくれる「AI売り子」」のように特定業界や社会で実際に使われるAI応用例。
        
        * **市場・ビジネス動向**: 市場調査や企業戦略、業界の展望に関する記事。「AIは仕事を奪うのか？」などAIの社会的影響やビジネスへの影響についての記事も含む。
        
        * **セキュリティ・倫理**: AIの安全性、倫理的問題、法的問題、著作権などに関する記事。「松江市、生成AIで"ゆるキャラ制作"→約2カ月で中止に　「著作権侵害のリスク払拭できない」」のような事例。
        
        * **政策・規制**: 政府や公的機関によるAI関連の政策に関する記事。規制、ガイドライン、法整備など。
        
        **正確な分類のためのガイドライン:**
        1. タイトルだけでなく、記事の冒頭数段落を重視して分類してください
        2. 複数のカテゴリにまたがる場合は、記事の主要なテーマを優先してください
        3. 具体的な企業名や製品名に惑わされず、記事の本質的な内容で判断してください
        4. 特に「AI技術基盤」と「製品・サービス」の区別に注意してください：
           - 「AI技術基盤」：開発者向けのAI技術（LLM、API、開発基盤など）
           - 「製品・サービス」：一般ユーザー向けの最終製品
        
        **曖昧なケースの分類ガイドライン:**
        * **AI技術基盤と製品・サービスの境界:**
          - LLMやAI開発プラットフォームは「AI技術基盤」に分類
          - 同じAI機能でも、エンドユーザー向け実装は「製品・サービス」に分類
        
        * **社会実装・応用と業務効率化の境界:**
          - 特定業界（医療、小売、教育など）でのAI活用は「社会実装・応用」
          - 社内業務プロセス改善は「業務効率化・自動化」に分類
        
        **分類の具体例（Few-Shot Learning）:**
        以下の正確な分類例を参考にしてください：
        
        **「製品・サービス」の正しい例:**
        * 「ソニーとラズパイ共同開発のAIカメラが発売\u3000Raspberry Piの全モデルに対応」
          * 理由: 新しいハードウェア製品（AIカメラ）の**発売**に関する記事であるため。
        * 「中小企業向けAIチャットボットサービス『AI秘書』提供開始、月額9800円から」
          * 理由: エンドユーザー向けの新サービスの提供開始に関する記事であるため。
        * 「楽天モバイル、メッセージアプリ「Rakuten Link」に生成AI機能を搭載」
          * 理由: 既存製品への新機能搭載に関する記事であるため。
        * 「GitHub Copilotが「Gemini 1.5 Pro」「o1-preview」「Claude 3.5 Sonnet」に対応」
          * 理由: 既存サービスの機能拡張・対応に関する記事であるため。
        * 「Microsoft、Word・Excel・PowerPointにAIアシスタント「Copilot」導入」
          * 理由: 一般ユーザー向け製品への新機能追加に関する記事であるため。
          
        **「AI技術基盤」の正しい例:**
        * 「リコー、モデルマージで"GPT-4レベル"の大規模言語モデル開発\u3000プライベートLLMの開発効率化に貢献」
          * 理由: 大規模言語モデル（LLM）という**AI技術基盤**の開発に関する記事であるため。
        * 「富士通、大規模言語モデル「Takane」提供開始　「世界一の日本語性能を持つ」とうたう」
          * 理由: 言語モデルというAI基盤技術に関する記事であるため。
        * 「OpenAI、「GPT-4o」公開〜画像・音声・テキスト同時処理可能なマルチモーダルモデル」
          * 理由: 新しい大規模言語モデルの開発・公開に関する記事であるため。
        * 「Anthropic、次世代AIモデル「Claude 3.5 Sonnet」発表〜マルチモーダル能力強化と推論速度向上」
          * 理由: AI開発基盤となるモデルの公開に関する記事であるため。
          
        **「業務効率化・自動化」の正しい例:**
        * 「〇〇社、AIチャットボット導入で問い合わせ対応時間を80%削減、年間3000万円のコスト削減を実現」
          * 理由: 企業の業務プロセス改善とコスト削減に関する具体的な事例であるため。
        * 「「ここは人間も失敗するしAIでもいいのでは」――生成AIの業務導入で外せない"幻覚"との付き合い方」
          * 理由: 企業の業務へのAI導入に関する記事であるため。
        * 「大手物流企業、AIによる配送ルート最適化で燃料費15%削減、配送効率20%向上」
          * 理由: 企業の内部業務プロセス改善に関する事例であるため。
        * 「バックオフィス業務にAIアシスタント導入、データ入力作業を自動化し生産性30%向上」
          * 理由: 社内の業務効率化に関する記事であるため。
          
        **「社会実装・応用」の正しい例:**
        * 「いらっしゃいませなのだ！──ずんだもんが接客してくれる「AI売り子」　GPT-4o活用　Gateboxが開発」
          * 理由: 小売・販売という特定分野でのAI応用事例（AIキャラクターによる接客）に関する記事であるため。
        * 「AIによる画像診断支援システム、〇〇病院で導入開始、診断精度が15%向上」
          * 理由: 医療分野でのAI応用事例に関する記事であるため。
        * 「小学校教育にAIチューターを導入、個別最適化学習で学力向上効果を実証」
          * 理由: 教育分野という特定業界でのAI活用事例に関する記事であるため。
        * 「農業分野でのAI活用が進む、ドローンと画像認識技術で病害虫早期発見システムを実用化」
          * 理由: 農業という特定業界でのAI応用に関する記事であるため。
          
        **「市場・ビジネス動向」の正しい例:**
        * 「『AIは仕事を奪うのか？』に対する元マイクロソフト澤円さんの回答\u3000企業経営の中で"絶対に置き換わらないもの"とは」
          * 理由: AIがビジネスや雇用に与える影響という**市場・ビジネス動向**に関する識者の見解であるため。
        * 「国内AI市場、2027年には〇〇兆円規模に到達予測、年間成長率は25%超え」
          * 理由: AI業界の市場規模予測に関する記事であるため。
        * 「生成AI活用に関する企業意識調査〜導入障壁はコスト・人材不足・データ保護懸念」
          * 理由: AI市場の動向に関する調査結果についての記事であるため。
        * 「なぜ日本企業はAI導入で後れを取っているのか〜経営者の意識改革と人材育成の必要性」
          * 理由: 市場・ビジネスの全体的な動向分析に関する記事であるため。
          
        **「セキュリティ・倫理」の正しい例:**
        * 「AIの安全性を"攻撃者視点"で評価するガイドライン\u3000IPAなどが無料公開\u3000LLMへの8つの攻撃手法を紹介」
          * 理由: AIのセキュリティに関するガイドラインの公開記事であるため。
        * 「松江市、生成AIで"ゆるキャラ制作"→約2カ月で中止に　「著作権侵害のリスク払拭できない」」
          * 理由: AI利用に関する著作権やリスクの倫理的問題に関する記事であるため。
        * 「AIによる偽情報・ディープフェイク拡散への対策、専門家が警鐘を鳴らす」
          * 理由: AIのセキュリティ・倫理的問題に関する記事であるため。
        * 「顔認識AIの公共利用に法的制限を、プライバシー保護団体が規制強化を要求」
          * 理由: AIの倫理的問題とプライバシーリスクに関する記事であるため。
          
        **「政策・規制」の正しい例:**
        * 「政府、AI戦略を発表、重点分野への投資を強化、5年間で1兆円規模の支援へ」
          * 理由: 政府によるAI関連の政策や公的資金による支援に関する記事であるため。
        * 「EU、AI利用に関する包括的な規制案で合意、ハイリスクAIに厳格なルールを適用」
          * 理由: 公的機関によるAI規制に関する記事であるため。
        * 「公取委、「生成AIを巡る競争」について意見募集　法人・個人問わず　11月22日まで」
          * 理由: 公的機関によるAI規制に関する記事であるため。
        * 「ハローワーク、生成AI導入を検討　マッチングの効率化狙う　OpenAI Japanの協力も視野に」
          * 理由: 公的機関によるAI導入に関する記事であるため。
        * 「デジタル庁、AIガバナンスのガイドライン策定へ、企業の自主規制と行政指導のバランスを模索」
          * 理由: 政府機関によるAI規制・ガイドライン策定に関する記事であるため。
        
        **境界線上の難しいケースとその分類:**
        * 「Google、次世代AIモデル「Gemini Pro 1.5」をCloud APIとして提供開始」
          * 分類: 「AI技術基盤」（理由: 開発者向けAPIサービスとしての提供であるため）
        * 「Google、Bard (現Gemini)をChromeに統合、ウェブ閲覧支援機能を強化」
          * 分類: 「製品・サービス」（理由: 一般ユーザー向けの最終製品への機能追加であるため）
        * 「大手百貨店、売り場にAIカメラ導入、顧客行動分析で陳列改善と売上20%増」
          * 分類: 「社会実装・応用」（理由: 小売業界という特定分野でのAI活用事例であるため）
        * 「経理部門にAIアシスタント導入、データ入力作業を自動化し生産性30%向上」
          * 分類: 「業務効率化・自動化」（理由: 企業内部の業務プロセス改善であるため）
        
        **思考プロセス:**
        1. 記事のタイトルと内容から、学術的な研究論文や基礎研究段階の技術に関するものかどうかを判断
        2. 上記の「該当する特徴」と「該当しない特徴」を厳密に比較検討
        3. 判断例を参考に最終的な決定を行う
        
        <thinking>
        [ここに思考プロセスを記述してください]
        </thinking>
        
        <category>選択したカテゴリ</category>
        <confidence>0-100の数値</confidence>
        """
        
        # OpenAI APIを呼び出し
        client = openai.OpenAI(api_key=api_key)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたは日本のAIニュース記事を分析し、指定されたカテゴリに分類する専門家AIです。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2500,  # トークン数を増やして長い記事にも対応
                temperature=0.1
            )
            
            # レスポンステキストを抽出
            response_text = response.choices[0].message.content.strip()
            logger.debug(f"LLM Raw Response for final categorization:\n{response_text}")
            
            # カテゴリと信頼度を抽出
            category_match = re.search(r'<category>(.*?)</category>', response_text, re.DOTALL)
            confidence_match = re.search(r'<confidence>(.*?)</confidence>', response_text, re.DOTALL)
            
            final_category = None
            confidence = 0
            
            if category_match:
                final_category = category_match.group(1).strip()
                logger.info(f"LLM determined category: {final_category}")
                
            if confidence_match:
                try:
                    confidence = float(confidence_match.group(1).strip())  # 文字列の場合は浮動小数点数に変換
                except (ValueError, TypeError):
                    confidence = 0  # 変換できない場合は0とする
                
            # 信頼度スコアが低い場合、またはカテゴリが「研究動向」とは直接関連しないと判断される場合は
            # タイトルベースのヒューリスティックを適用
            confidence_threshold = 80  # 信頼度のしきい値を上げる
            if not final_category or confidence < confidence_threshold:
                logger.warning(f"Low confidence ({confidence}) for final categorization of '{title}'. Applying heuristics.")
                
                # タイトルベースのヒューリスティック
                product_service_keywords = ["発売", "提供開始", "リリース", "新製品", "新サービス", "搭載", "対応", "発表", 
                    "アップデート", "バージョンアップ", "機能追加", "新機能", "公開", "ベータ版", "正式版", "サブスク", 
                    "月額", "値下げ", "無料提供", "新アプリ", "iOS版", "Android版", "アプリ配信", "インストール"]
                tech_base_keywords = ["大規模言語モデル", "LLM", "プラットフォーム", "API", "基盤", "開発", "Gemini", "Claude", 
                    "GPT", "Takane", "Llama", "Mistral", "Mixtral", "ファインチューニング", "推論", "トレーニング", "学習", 
                    "モデル", "パラメータ", "トークナイザー", "エンベディング", "ベクトル検索", "RAG", "TGI", "vLLM", 
                    "開発キット", "SDK", "GitHub", "オープンソース", "開発者向け", "自社開発", "フレームワーク", 
                    "開発環境", "モデルマージ", "蒸留", "量子化", "プロンプトエンジニアリング", "微調整"]
                efficiency_keywords = ["業務効率", "自動化", "コスト削減", "生産性", "業務改善", "効率化", "工数削減", "人材不足", 
                    "人手不足", "省力化", "省人化", "RPA", "ワークフロー", "業務プロセス", "BPR", "バックオフィス", 
                    "社内業務", "内部業務", "業務改革", "ホワイトカラー", "事務作業", "経費精算", "会議議事録", "書類作成", 
                    "マニュアル作成", "ナレッジ管理", "顧客対応", "問い合わせ対応", "コールセンター", "チャットボット導入"]
                social_impl_keywords = ["社会実装", "応用", "実証", "活用事例", "導入事例", "接客", "売り子", "導入", 
                    "実用化", "商用化", "現場導入", "医療", "教育", "農業", "小売", "流通", "物流", "金融", "保険", 
                    "不動産", "建設", "製造", "エネルギー", "交通", "通信", "放送", "エンターテイメント", "スポーツ", 
                    "接客支援", "顧客体験", "UX改善", "店舗", "病院", "学校", "大学", "研究所", "実証実験"]
                market_keywords = ["市場", "予測", "動向", "調査", "トレンド", "シェア", "経営", "戦略", "投資", "競争", 
                    "業界", "ビジネスモデル", "収益", "決算", "四半期", "売上", "利益", "成長率", "分析", "レポート", 
                    "白書", "調査報告", "アンケート", "意識調査", "利用実態", "消費者", "ユーザー", "導入障壁", "課題", 
                    "人材育成", "仕事を奪う", "失業", "雇用", "働き方", "企業戦略", "経営戦略"]
                security_keywords = ["セキュリティ", "倫理", "著作権", "リスク", "安全性", "ガイドライン", "プライバシー", "無断", 
                    "脆弱性", "フェイク", "偽情報", "デマ", "ディープフェイク", "なりすまし", "改ざん", "漏洩", "情報漏洩", 
                    "攻撃", "防御", "対策", "保護", "コンプライアンス", "法的責任", "訴訟", "監査", "認証", "暗号化", 
                    "悪用", "誤用", "バイアス", "差別", "公平性", "透明性", "説明可能性", "XAI", "中止"]
                policy_keywords = ["政策", "規制", "法律", "ガイドライン", "政府", "省庁", "IPA", "公取委", "ハローワーク", 
                    "厚労省", "経産省", "総務省", "文科省", "デジタル庁", "内閣府", "国会", "法案", "条例", "自治体", 
                    "規則", "基準", "審議会", "検討会", "報告書", "パブコメ", "意見募集", "国際標準", "ISO", "予算", 
                    "補助金", "助成金", "税制優遇", "特区", "実証特区", "AI戦略", "デジタル戦略", "DX戦略"]
                
                # キーワードリストをまとめる
                category_keywords = {
                    "製品・サービス": product_service_keywords,
                    "AI技術基盤": tech_base_keywords,
                    "業務効率化・自動化": efficiency_keywords,
                    "社会実装・応用": social_impl_keywords,
                    "市場・ビジネス動向": market_keywords,
                    "セキュリティ・倫理": security_keywords,
                    "政策・規制": policy_keywords
                }
                
                # キーワードマッチスコアを計算
                keyword_match_scores = {}
                for category, keywords in category_keywords.items():
                    # 単純なキーワード一致数をカウント
                    simple_score = sum(1 for keyword in keywords if keyword in title)
                    
                    # 高重要度キーワードの定義（カテゴリ特有の明確な指標）
                    high_importance = []
                    if category == "製品・サービス":
                        high_importance = ["発売", "提供開始", "リリース", "新製品", "新サービス"]
                    elif category == "AI技術基盤":
                        high_importance = ["大規模言語モデル", "LLM", "API", "開発者向け", "モデル"]
                    elif category == "業務効率化・自動化":
                        high_importance = ["業務効率", "自動化", "コスト削減", "生産性", "RPA"]
                    elif category == "社会実装・応用":
                        high_importance = ["医療", "教育", "農業", "小売", "店舗", "病院", "学校"]
                    elif category == "市場・ビジネス動向":
                        high_importance = ["市場", "予測", "動向", "調査", "トレンド", "シェア"]
                    elif category == "セキュリティ・倫理":
                        high_importance = ["セキュリティ", "倫理", "著作権", "リスク", "脆弱性"]
                    elif category == "政策・規制":
                        high_importance = ["政策", "規制", "法律", "ガイドライン", "政府", "省庁"]
                    
                    # 高重要度キーワードのボーナススコア
                    importance_bonus = sum(3 for keyword in high_importance if keyword in title)
                    
                    # 最終スコア
                    final_score = simple_score + importance_bonus
                    keyword_match_scores[category] = final_score
                
                # ヒューリスティックベースのカテゴリ推定（最もスコアの高いカテゴリ）
                if any(score > 0 for score in keyword_match_scores.values()):
                    heuristic_category = max(keyword_match_scores.items(), key=lambda x: x[1])[0]
                    logger.info(f"Keyword-based scores: {keyword_match_scores}")
                else:
                    # 古い方法でのヒューリスティック（キーワードがマッチしない場合）
                    if any(keyword in title for keyword in product_service_keywords):
                        heuristic_category = "製品・サービス"
                    elif any(keyword in title for keyword in tech_base_keywords):
                        heuristic_category = "AI技術基盤"
                    elif any(keyword in title for keyword in efficiency_keywords):
                        heuristic_category = "業務効率化・自動化"
                    elif any(keyword in title for keyword in social_impl_keywords):
                        heuristic_category = "社会実装・応用"
                    elif any(keyword in title for keyword in market_keywords):
                        heuristic_category = "市場・ビジネス動向"
                    elif any(keyword in title for keyword in security_keywords):
                        heuristic_category = "セキュリティ・倫理"
                    elif any(keyword in title for keyword in policy_keywords):
                        heuristic_category = "政策・規制"
                    else:
                        # 特定のパターンに基づく分類
                        if "AI売り子" in title or "接客" in title:
                            heuristic_category = "社会実装・応用"
                        elif "カメラ" in title and ("発売" in title or "提供" in title):
                            heuristic_category = "製品・サービス"
                        elif "大規模言語モデル" in title or "LLM" in title or "Takane" in title:
                            heuristic_category = "AI技術基盤"
                        else:
                            heuristic_category = apply_heuristic_categorization(title)
                
                logger.info(f"Advanced heuristic-based categorization: '{heuristic_category}' for '{title}'")
                
                # 信頼度が非常に低い場合はヒューリスティックの結果を使用
                if confidence < 50:
                    final_category = heuristic_category
                    logger.info(f"Very low confidence score. Using heuristic category: {heuristic_category}")
                else:
                    # 中程度の信頼度の場合、LLMの結果とヒューリスティックの結果を比較
                    if final_category and heuristic_category != final_category:
                        logger.info(f"Conflict between LLM ({final_category}) and heuristic ({heuristic_category}). Reviewing.")
                        # ヒューリスティックを優先するキーワードがある場合
                        if any(keyword in title for keyword in product_service_keywords + tech_base_keywords):
                            final_category = heuristic_category
                            logger.info(f"Strong keywords detected. Overriding to: {heuristic_category}")
                    elif not final_category:
                        final_category = heuristic_category
            
            # 信頼度スコアに応じた3段階の処理ロジック
            if confidence < 50:
                # 信頼度が非常に低い場合はヒューリスティックの結果を使用
                final_category = heuristic_category
                logger.info(f"Very low confidence score ({confidence}). Using heuristic category: {heuristic_category}")
            elif 50 <= confidence < 70:
                # 信頼度が低〜中程度の場合、キーワードスコアが明確な場合はヒューリスティックの結果を採用
                best_match = max(keyword_match_scores.items(), key=lambda x: x[1])
                if best_match[1] >= 3 and final_category != best_match[0]:
                    logger.info(f"Adjusting low confidence categorization from {final_category} to {best_match[0]} based on keyword frequency (score: {best_match[1]})")
                    final_category = best_match[0]
                # 混同されやすいカテゴリペアの特別ルール
                elif final_category == "製品・サービス" and any(keyword in title.lower() for keyword in ["api", "開発者", "プラットフォーム", "sdk"]):
                    logger.info(f"Reclassifying from '製品・サービス' to 'AI技術基盤' based on technical indicators")
                    final_category = "AI技術基盤"
            elif 70 <= confidence < 80:
                # 信頼度が中〜高程度の場合、カテゴリ間の混同が頻繁に起こるペアのみチェック
                if final_category == "製品・サービス" and any(keyword in title.lower() for keyword in ["api", "開発者向け", "sdk"]):
                    # APIや開発者向けサービスは技術基盤に分類されるべき
                    logger.info(f"Correcting category from '製品・サービス' to 'AI技術基盤' based on developer-focused indicators")
                    final_category = "AI技術基盤"
                elif final_category == "社会実装・応用" and any(keyword in title.lower() for keyword in ["社内", "バックオフィス", "業務効率", "業務改善"]):
                    # 社内業務改善は業務効率化に分類されるべき
                    logger.info(f"Correcting category from '社会実装・応用' to '業務効率化・自動化' based on internal process indicators")
                    final_category = "業務効率化・自動化"
            else:
                # 中程度の信頼度の場合、LLMの結果とヒューリスティックの結果を比較
                if final_category and heuristic_category != final_category:
                    logger.info(f"Conflict between LLM ({final_category}) and heuristic ({heuristic_category}). Reviewing.")
                    # ヒューリスティックを優先するキーワードがある場合
                    if any(keyword in title for keyword in product_service_keywords + tech_base_keywords):
                        final_category = heuristic_category
                        logger.info(f"Strong keywords detected. Overriding to: {heuristic_category}")
                elif not final_category:
                    final_category = heuristic_category
            
            # 追加の混同されやすいカテゴリペア特別処理
            # 1. AI技術基盤 vs 製品・サービス（より詳細な条件）
            if final_category == "製品・サービス":
                tech_indicators = ["開発者向け", "api", "sdk", "プラットフォーム", "モデル開発", "クラウド基盤"]
                if any(indicator in title.lower() for indicator in tech_indicators):
                    logger.info(f"Additional check: '製品・サービス' → 'AI技術基盤' (technical indicators)")
                    final_category = "AI技術基盤"
            
            # 2. 社会実装・応用 vs 業務効率化・自動化（より詳細な条件）
            elif final_category == "社会実装・応用":
                efficiency_indicators = ["業務改善", "業務プロセス", "社内業務", "バックオフィス", "業務効率"]
                if any(indicator in title.lower() for indicator in efficiency_indicators):
                    logger.info(f"Additional check: '社会実装・応用' → '業務効率化・自動化' (efficiency indicators)")
                    final_category = "業務効率化・自動化"
            
            # 3. 市場・ビジネス動向 vs 政策・規制
            elif final_category == "市場・ビジネス動向":
                policy_indicators = ["政府", "省庁", "法律", "規制", "ガイドライン", "デジタル庁", "総務省"]
                if any(indicator in title for indicator in policy_indicators):
                    logger.info(f"Additional check: '市場・ビジネス動向' → '政策・規制' (policy indicators)")
                    final_category = "政策・規制"
            
            return final_category
            
        except openai.APIError as e:
            logger.error(f"OpenAI API Error: {str(e)}")
            # エラーの場合は、ヒューリスティックベースのカテゴリ推定を使用
            final_category = apply_heuristic_categorization(title)
            logger.info(f"Error occurred, falling back to heuristic categorization: {final_category}")
            return final_category
        except openai.RateLimitError as e:
            logger.error(f"OpenAI Rate Limit Error: {str(e)}")
            # エラーの場合は、ヒューリスティックベースのカテゴリ推定を使用
            final_category = apply_heuristic_categorization(title)
            logger.info(f"Error occurred, falling back to heuristic categorization: {final_category}")
            return final_category
        except openai.APIConnectionError as e:
            logger.error(f"OpenAI API Connection Error: {str(e)}")
            # エラーの場合は、ヒューリスティックベースのカテゴリ推定を使用
            final_category = apply_heuristic_categorization(title)
            logger.info(f"Error occurred, falling back to heuristic categorization: {final_category}")
            return final_category
        except openai.APITimeoutError as e:
            logger.error(f"OpenAI API Timeout Error: {str(e)}")
            # エラーの場合は、ヒューリスティックベースのカテゴリ推定を使用
            final_category = apply_heuristic_categorization(title)
            logger.info(f"Error occurred, falling back to heuristic categorization: {final_category}")
            return final_category
    
    except Exception as e:
        logger.error(f"Error in final categorization: {str(e)}")
        # エラーの場合は、ヒューリスティックベースのカテゴリ推定を使用
        final_category = apply_heuristic_categorization(title)
        logger.info(f"Error occurred, falling back to heuristic categorization: {final_category}")
        return final_category

def extract_companies_with_llm(content, title, api_key):
    """
    OpenAIのAPIを使用して記事の内容から企業名を抽出
    
    Args:
        content: 記事の内容
        title: 記事のタイトル
        api_key: OpenAI APIキー
        
    Returns:
        list: 抽出された企業名のリスト
    """
    if not api_key:
        logger.warning("APIキーが設定されていないため、LLMによる企業名抽出をスキップします")
        return []
        
    # LLM用のプロンプトを作成
    prompt = f"""
    以下の記事から、言及されているすべての企業名を抽出してください。
    子会社や関連会社も含めて抽出してください。
    
    タイトル: {title}
    
    内容:
    {content}
    
    【出力形式】
    企業名を1行に1社ずつ、以下のようにリストアップしてください：
    
    企業名:
    [企業名1]
    [企業名2]
    ...
    """
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは記事から企業名を抽出する専門家です。企業名は正式名称で抽出し、略称や通称は避けてください。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        
        # レスポンステキストを抽出
        response_text = response.choices[0].message.content.strip()
        
        # 企業名リストを抽出
        companies = []
        company_section = False
        
        for line in response_text.split('\n'):
            line = line.strip()
            if '企業名:' in line:
                company_section = True
                continue
            if company_section and line and line != '企業名:':
                companies.append(line)
        
        # 重複を削除し、ソートして返す
        return sorted(list(set(companies)))
            
    except Exception as e:
        logger.error(f"Error in extract_companies_with_llm: {str(e)}")
        return []
