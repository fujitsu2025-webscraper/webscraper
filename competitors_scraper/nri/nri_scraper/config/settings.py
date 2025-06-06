"""
NRIスクレイパーの設定ファイル
"""
import os
from pathlib import Path

# ベースディレクトリの設定
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 出力ディレクトリの設定
OUTPUT_BASE_DIR = os.path.join(BASE_DIR, 'output')

# スクレイピング対象のURL
TARGET_URL = "https://www.nri.com/jp/service/solution/index.html"

# WebDriverの設定
WEBDRIVER_OPTIONS = {
    'no_sandbox': True,
    'disable_dev_shm_usage': True,
    'window_size': (1920, 1080),
    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'enable_javascript': True,
    'exclude_switches': ['enable-automation'],
    'use_automation_extension': False
}

# インダストリーリスト
INDUSTRY_LIST = [
    "自動車",
    "重工業・エンジニアリング",
    "産業機械",
    "素材・化学",
    "エネルギー・資源・鉱業",
    "建設",
    "運輸・物流",
    "消費財・小売・流通",
    "テクノロジー",
    "情報通信",
    "エンタテイメント&メディア",
    "ホスピタリティ&レジャー",
    "総合商社",
    "金融サービス",
    "銀行・証券",
    "資産運用",
    "保険",
    "不動産",
    "プライベート・エクイティ（PE）",
    "都市・インフラストラクチャー",
    "官公庁・地方自治体・公的機関",
    "農林水産・食・バイオ",
    "人材サービス",
    "ヘルスケア・医薬ライフサイエンス"
]

# NRIの業種分類マッピング
NRI_INDUSTRY_MAPPING = {
    "自動車": "自動車",
    "重工業・エンジニアリング": "重工業・エンジニアリング",
    "産業機械": "産業機械",
    "素材・化学": "素材・化学",
    "エネルギー・資源・鉱業": "エネルギー・資源・鉱業",
    "建設": "建設",
    "運輸・物流": "運輸・物流",
    "消費財・小売・流通": "消費財・小売・流通",
    "テクノロジー": "テクノロジー",
    "情報通信": "情報通信",
    "エンタテイメント&メディア": "エンタテイメント&メディア",
    "ホスピタリティ&レジャー": "ホスピタリティ&レジャー",
    "総合商社": "総合商社",
    "金融サービス": "金融サービス",
    "銀行・証券": "銀行・証券",
    "資産運用": "資産運用",
    "保険": "保険",
    "不動産": "不動産",
    "プライベート・エクイティ（PE）": "プライベート・エクイティ（PE）",
    "都市・インフラストラクチャー": "都市・インフラストラクチャー",
    "官公庁・地方自治体・公的機関": "官公庁・地方自治体・公的機関",
    "農林水産・食・バイオ": "農林水産・食・バイオ",
    "人材サービス": "人材サービス",
    "ヘルスケア・医薬ライフサイエンス": "ヘルスケア・医薬ライフサイエンス",
    
    # 旧分類から新分類へのマッピング
    "製造・プロセス": "産業機械",
    "流通": "消費財・小売・流通",
    "金融機関": "銀行・証券",
    "電力・エネルギー": "エネルギー・資源・鉱業",
    "通信": "情報通信",
    "建設・不動産": "不動産",
    "医療・ヘルスケア": "ヘルスケア・医薬ライフサイエンス",
    "文教・教育": "官公庁・地方自治体・公的機関",
    "サービス": "ホスピタリティ&レジャー",
    "IT・情報サービス": "テクノロジー",
    "農林水産": "農林水産・食・バイオ",
    "官公庁": "官公庁・地方自治体・公的機関",
    "地方公共団体": "官公庁・地方自治体・公的機関",
    "卸売・小売業・飲食店": "消費財・小売・流通",
    "製造業": "産業機械",
    "情報処理": "テクノロジー",
    "医療": "ヘルスケア・医薬ライフサイエンス",
    "教育": "官公庁・地方自治体・公的機関",
    "公共": "官公庁・地方自治体・公的機関"
}

# 特定の企業名マッピング
EXPLICIT_COMPANY_MAPPING = {
    "銀行": "銀行・証券",
    "信用金庫": "銀行・証券",
    "信用組合": "銀行・証券",
    "証券": "銀行・証券",
    "保険": "保険",
    "生命保険": "保険",
    "損害保険": "保険",
    "自動車": "自動車",
    "電機": "テクノロジー",
    "電力": "エネルギー・資源・鉱業",
    "ガス": "エネルギー・資源・鉱業",
    "石油": "エネルギー・資源・鉱業",
    "化学": "素材・化学",
    "製薬": "ヘルスケア・医薬ライフサイエンス",
    "病院": "ヘルスケア・医薬ライフサイエンス",
    "小売": "消費財・小売・流通",
    "百貨店": "消費財・小売・流通",
    "スーパー": "消費財・小売・流通",
    "コンビニ": "消費財・小売・流通",
    "飲食": "消費財・小売・流通",
    "レストラン": "消費財・小売・流通",
    "ホテル": "ホスピタリティ&レジャー",
    "旅館": "ホスピタリティ&レジャー",
    "旅行": "ホスピタリティ&レジャー",
    "航空": "運輸・物流",
    "鉄道": "運輸・物流",
    "バス": "運輸・物流",
    "タクシー": "運輸・物流",
    "物流": "運輸・物流",
    "運送": "運輸・物流",
    "建設": "建設",
    "不動産": "不動産",
    "住宅": "不動産",
    "マンション": "不動産",
    "トヨタ": "自動車",
    "住友電装": "自動車",
    "SUBARU": "自動車",
    "戸田建設": "建設",
    "国分グループ": "消費財・小売・流通",
    "国分": "消費財・小売・流通",
    "医療センター": "ヘルスケア・医薬ライフサイエンス",
    "中部電力": "エネルギー・資源・鉱業",
    "オムロン": "産業機械",
    "JapanBluStellar": "テクノロジー",
    "好生館": "ヘルスケア・医薬ライフサイエンス"
}

# ソリューションカテゴリ定義
SOLUTION_CATEGORIES = {
    "戦略・コンサルティング": [
        "経営戦略コンサルティング",
        "DX戦略策定",
        "IT戦略・ロードマップ策定",
        "業務改革コンサルティング",
        "デジタルマーケティング戦略",
        "顧客体験(CX)設計",
        "PMO・プロジェクト管理",
        "IT投資評価・最適化",
        "デジタル人材育成",
        "テクノロジーアドバイザリー"
    ],
    "システムインテグレーション": [
        "基幹システム構築",
        "ERP導入・カスタマイズ",
        "SCM・物流システム構築",
        "CRM・SFA導入",
        "会計・人事・給与システム",
        "生産管理システム",
        "販売管理システム",
        "在庫管理システム",
        "レガシーシステム刷新",
        "システム統合・マイグレーション"
    ],
    "クラウドソリューション": [
        "クラウド移行・最適化",
        "クラウドネイティブ開発",
        "マルチクラウド戦略・実装",
        "ハイブリッドクラウド構築",
        "SaaS導入・活用支援",
        "PaaS基盤構築・運用",
        "IaaS基盤構築・運用",
        "クラウドセキュリティ",
        "コンテナ化・Kubernetes",
        "サーバーレスアーキテクチャ"
    ],
    "セキュリティソリューション": [
        "サイバーセキュリティ対策",
        "セキュリティアセスメント",
        "情報セキュリティ管理",
        "認証基盤構築",
        "脆弱性診断・対策",
        "セキュリティ監視",
        "インシデント対応",
        "ゼロトラスト実装"
    ],
    "データマネジメント・分析": [
        "データ戦略策定",
        "データ分析基盤構築",
        "ビッグデータ基盤構築",
        "データウェアハウス/レイクハウス",
        "BIソリューション",
        "データガバナンス",
        "マスターデータ管理"
    ],
    "AI・先端技術": [
        "AI導入・活用支援",
        "機械学習/ディープラーニング",
        "自然言語処理",
        "画像・音声認識",
        "生成AI活用",
        "ロボティクス"
    ],
    "IoT・エッジコンピューティング": [
        "IoTプラットフォーム構築",
        "センサーネットワーク",
        "エッジコンピューティング",
        "デジタルツイン",
        "スマートファクトリー",
        "スマートシティ",
        "コネクテッドカー"
    ],
    "業務アプリケーション": [
        "業務アプリケーション開発",
        "モバイルアプリ開発",
        "Webアプリケーション開発",
        "ローコード/ノーコード開発",
        "API開発・管理",
        "UIUXデザイン"
    ],
    "インフラストラクチャ": [
        "ITインフラ設計・構築",
        "ネットワーク最適化",
        "データセンターソリューション",
        "サーバー・ストレージ最適化",
        "仮想化・コンテナ化",
        "バックアップ・災害対策",
        "ITインフラ監視・運用"
    ],
    "運用・保守サービス": [
        "マネージドサービス",
        "システム運用管理",
        "監視・障害対応",
        "ヘルプデスク・サポート",
        "ITアウトソーシング",
        "DevOps/SRE"
    ],
    "業務プロセス自動化": [
        "RPA導入・活用",
        "ビジネスプロセス自動化",
        "ワークフロー最適化",
        "業務効率化ツール",
        "インテリジェントオートメーション"
    ],
    "デジタルワークプレイス": [
        "テレワーク環境構築",
        "コラボレーションツール導入",
        "働き方改革支援",
        "オフィスDX",
        "ペーパーレス化",
        "デジタル人材育成"
    ],
    "業界特化ソリューション": [
        "金融業界向けソリューション",
        "製造業向けソリューション",
        "流通・小売業向けソリューション",
        "医療・ヘルスケア向けソリューション",
        "公共・自治体向けソリューション",
        "エネルギー業界向けソリューション",
        "物流・運輸向けソリューション",
        "建設・不動産向けソリューション"
    ],
    "ブロックチェーン・分散技術": [
        "ブロックチェーン導入",
        "スマートコントラクト開発",
        "分散型アプリケーション",
        "NFT・トークン開発",
        "暗号資産ソリューション"
    ],
    "サステナビリティ・グリーンIT": [
        "カーボンニュートラル支援",
        "グリーンITソリューション",
        "ESG対応システム",
        "環境モニタリング",
        "エネルギー最適化"
    ]
}

# ソリューション分類用のシステムメッセージ
SOLUTION_SYSTEM_MESSAGE = f"""あなたはITソリューション分類の専門家です。
与えられたITサービス・ソリューションの説明を分析し、最も適切なカテゴリを選択してください。

以下のカテゴリから1つだけ選んでください：
- 戦略・コンサルティング
- システムインテグレーション
- クラウドソリューション
- セキュリティソリューション
- データマネジメント・分析
- AI・先端技術
- IoT・エッジコンピューティング
- 業務アプリケーション
- インフラストラクチャ
- 運用・保守サービス
- 業務プロセス自動化
- デジタルワークプレイス
- 業界特化ソリューション
- ブロックチェーン・分散技術
- サステナビリティ・グリーンIT

回答は以下の形式で返してください：
ソリューション: [選択したカテゴリ]

各カテゴリの選択基準:
- 戦略・コンサルティング: 経営戦略、DX戦略、IT戦略の策定など、上流工程のコンサルティングが中心
- システムインテグレーション: 基幹システム構築、ERP導入、レガシーシステム刷新など
- クラウドソリューション: クラウド移行、ハイブリッドクラウド構築など、クラウド関連技術
- セキュリティソリューション: サイバーセキュリティ対策、認証基盤など、セキュリティ関連
- データマネジメント・分析: データ基盤構築、BI、データガバナンスなど
- AI・先端技術: AI、機械学習、自然言語処理、画像認識など
- IoT・エッジコンピューティング: IoT、センサー、エッジコンピューティングなど
- 業務アプリケーション: 業務アプリ開発、モバイルアプリ、ローコード開発など
- インフラストラクチャ: ネットワーク、データセンター、サーバー・ストレージなど
- 運用・保守サービス: システム運用、監視、ヘルプデスク、アウトソーシングなど
- 業務プロセス自動化: RPA、ビジネスプロセス自動化、ワークフロー最適化など
- デジタルワークプレイス: テレワーク、コラボレーションツール、働き方改革など
- 業界特化ソリューション: 特定業界向けの専用ソリューション
- ブロックチェーン・分散技術: ブロックチェーン、スマートコントラクト、分散アプリなど
- サステナビリティ・グリーンIT: カーボンニュートラル、ESG対応、エネルギー最適化など

与えられた事例を分析し、最も適切なカテゴリを1つだけ選んでください。
"""

# GPT-4o-miniのシステムメッセージ
SUMMARY_SYSTEM_MESSAGE = """あなたは専門的な要約者です。与えられたテキストを約200-300文字で要約してください。
要約は以下の要素を含めるようにしてください：
1. 導入背景と課題
2. 導入された技術やソリューション
3. 得られた効果や成果
4. 今後の展望（もし言及があれば）

要約は日本語で、簡潔かつ具体的に作成してください。数値や固有名詞は可能な限り保持してください。
"""

TITLE_SYSTEM_MESSAGE = """あなたはタイトル生成の専門家です。提供された要約内容に基づいて、非常に具体的で内容を的確に表現するタイトルを生成してください。
タイトルは50文字以内で、以下の要素を可能な限り含めてください：
1) 導入企業名
2) 製品・技術名
3) 具体的な数値成果（例：40%削減、2倍向上など）
4) 解決された課題や実現した価値

「〜事例」「〜導入事例」などの一般的な表現は避け、読者が一目でその事例の価値を理解できる具体的な表現を使用してください。
"""

INDUSTRY_SYSTEM_MESSAGE = f"""あなたは企業のインダストリー分類の専門家です。
与えられた企業名とお客様プロフィールのテキストを分析し、以下のインダストリーカテゴリのうち、最も適切なものを1つだけ選んでください。
選択肢: {', '.join(INDUSTRY_LIST)}

各インダストリーの特徴を踏まえ、テキストから読み取れる業種情報に基づいて判断してください。
回答は選択肢の中から1つのカテゴリ名のみを返してください。それ以外の説明は不要です。
"""
