# NRIサービススクレイパー

## 概要

このプロジェクトは、野村総合研究所（NRI）の公式ウェブサイトからサービス情報を自動的に収集し、構造化されたデータとして保存するためのスクレイピングツールです。高度なインダストリー分類機能を備え、サービスの正確な業界分類と要約生成を行います。

## 主な機能

1. NRIの公式ウェブサイトからサービス情報の自動収集
2. 高度なインダストリー分類アルゴリズムによる正確な業界分類
3. GPT-4o-miniを活用したサービス要約の自動生成（200-300文字）
4. ソリューションカテゴリの自動判定
5. 具体的なケーススタディタイトルの生成
6. JSON形式でのデータ保存

## 技術的特徴

### 高度なインダストリー分類

1. 複数の分類手法を組み合わせた複合判定アプローチ
2. コンテキスト抽出による業界特有の表現の認識
3. サービス機能からの業界推定
4. 業界ごとの共起語分析（20業界以上の専門用語辞書）
5. 否定表現パターンの検出による誤分類防止
6. 複数の分類結果を重み付けして最終判定

### データ処理

1. Seleniumを使用した動的ウェブページのスクレイピング
2. BeautifulSoupによるHTML解析
3. OpenAI APIを活用した自然言語処理
4. 構造化データの生成と保存

## 必要条件

1. Python 3.8以上
2. Chrome/Chromiumブラウザ
3. OpenAI APIキー

## 依存ライブラリ

1. selenium
2. beautifulsoup4
3. openai
4. python-dotenv
5. tqdm
6. pandas
7. requests
8. logging

## インストール方法

1. リポジトリをクローン

   ```bash
   git clone <repository-url>
   cd WebScrapingTool/competitors_scraper/nri
   ```

2. 必要なパッケージをインストール

   ```bash
   pip install -r requirements.txt
   ```

3. `.env`ファイルを作成し、OpenAI APIキーを設定

   ```plaintext
   OPENAI_API_KEY=your_api_key_here
   ```

## 使用方法

### 基本的な実行方法

```bash
python run_nri_service_scraper.py
```

### オプション

- `--headless`: ヘッドレスモードで実行（ブラウザを表示しない）

  ```bash
  python run_nri_service_scraper.py --headless
  ```

- `--use-html`: 提供されたHTMLコードを使用（ウェブサイトにアクセスしない）

  ```bash
  python run_nri_service_scraper.py --use-html
  ```

- `--no-summary`: 要約機能を使用しない

  ```bash
  python run_nri_service_scraper.py --no-summary
  ```

## 出力

スクレイピング結果は以下の形式で保存されます：

1. JSONファイル: `output/YYYYMMDD_HHMMSS/nri_cases_YYYYMMDD_HHMMSS.json`
2. CSVファイル: `output/YYYYMMDD_HHMMSS/nri_cases_YYYYMMDD_HHMMSS.csv`

## プロジェクト構造

```plaintext
nri/
├── README.md
├── requirements.txt
├── run_nri_service_scraper.py
├── .env
├── output/
│   └── YYYYMMDD_HHMMSS/
│       ├── nri_cases_YYYYMMDD_HHMMSS.json
│       └── nri_cases_YYYYMMDD_HHMMSS.csv
└── nri_scraper/
    ├── config/
    │   └── settings.py
    ├── models/
    │   └── service_scraper.py
    └── utils/
        ├── advanced_industry_classifier.py
        ├── industry_classifier.py
        ├── data_processor.py
        ├── logger.py
        └── webdriver_manager.py
```

## 高度なインダストリー分類の仕組み

このスクレイパーは以下の手法を組み合わせて高精度な業界分類を実現しています：

1. **コンテキスト抽出**: 正規表現パターンを使用して業界特有のコンテキストを抽出
2. **サービス機能マッピング**: サービスの機能から関連する業界を推定
3. **共起語分析**: 業界ごとの専門用語辞書（20業界以上）を用いて関連スコアを計算
4. **否定表現の検出**: 誤分類を防ぐための否定パターンの認識
5. **複合判定**: 複数の分類結果を重み付けして最終判定

### 業界カテゴリ

1. 金融サービス
2. 銀行・証券
3. 資産運用
4. 保険
5. テクノロジー
6. 情報通信
7. 自動車
8. 消費財・小売・流通
9. 運輸・物流
10. ヘルスケア・医薬ライフサイエンス
11. エネルギー・資源・鉱業
12. 不動産
13. 重工業・エンジニアリング
14. 産業機械
15. 素材・化学
16. 建設
17. エンタテイメント&メディア
18. ホスピタリティ&レジャー
19. 総合商社
20. プライベート・エクイティ（PE）
21. 都市・インフラストラクチャー
22. 官公庁・地方自治体・公的機関
23. 農林水産・食・バイオ
24. 人材サービス

## 注意事項

- このスクレイパーは教育・研究目的で作成されています
- 過度な頻度でのスクレイピングは避け、ウェブサイトのサーバーに負荷をかけないようにしてください
- 収集したデータの利用については、関連する法律や規制に従ってください

## ライセンス

このプロジェクトは社内利用を目的としており、権利は所有者に帰属します。
