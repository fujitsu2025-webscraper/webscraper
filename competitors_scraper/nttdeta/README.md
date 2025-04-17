# NTTデータスクレイパー

NTTデータの事例ページから情報を自動収集し、要約・分類するツールです。

## 概要

このツールは、NTTデータの事例ページから以下の情報を自動的に収集します：

1. 事例タイトル
2. URL
3. 顧客企業名
4. インダストリー分類
5. ソリューションカテゴリ
6. 要約文

また、GPT-4o-miniを活用して、以下の機能も提供します：

1. 事例内容の要約生成
2. 具体的なタイトルの生成
3. ソリューションカテゴリの分類
4. 生成タイトルからの顧客企業名抽出
5. Google検索APIを使用したインダストリー分類

## 前提条件

1. Python 3.8以上
2. Google Custom Search API（インダストリー分類用）
3. OpenAI API（要約・タイトル生成用）

## インストール方法

1. リポジトリをクローンします

   ```bash
   git clone https://github.com/your-username/WebScrapingTool.git
   cd WebScrapingTool/competitors_scraper/nttdeta
   ```

2. 必要なパッケージをインストールします

   ```bash
   pip install -r requirements.txt
   ```

3. 環境変数を設定します

   `.env`ファイルを作成し、以下の内容を記載します：

   ```env
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_API_KEY=your_google_api_key
   GOOGLE_CSE_ID=your_google_cse_id
   ```

## 使用方法

### 基本的な実行方法

```bash
python run_nttdata_scraper.py
```

### オプション

- `--max-clicks`: 「もっと見る」ボタンの最大クリック回数を指定します（デフォルト: 無制限）
- `--no-summary`: 要約生成を無効にします

例：

```bash
python run_nttdata_scraper.py --max-clicks 3 --no-summary
```

## 出力形式

スクレイピング結果は以下の形式で保存されます：

1. JSON形式（詳細データ）
2. CSV形式（表形式データ）

出力ファイルは `output/YYYYMMDD_HHMMSS/` ディレクトリに保存されます。

## 主な機能

### 1. 事例データの収集

NTTデータの事例ページから事例データを収集します。「もっと見る」ボタンをクリックして、全ての事例を表示します。

### 2. 要約生成

GPT-4o-miniを使用して、事例の内容を200-300文字程度に要約します。

### 3. タイトル生成

要約に基づいて、具体的で内容を的確に表現するタイトルを生成します。
可能な限り数値や固有名詞を含め、50文字以内で作成します。

### 4. 企業名抽出

生成されたタイトルから顧客企業名を抽出します。
例：「旭化成、Salesforce活用で営業データ入力8倍増加の改革実現」→「旭化成」

### 5. インダストリー分類

Google Custom Search APIを使用して、抽出した企業名の業種情報を検索し、インダストリーを分類します。
初期値は「テクノロジー」で、企業名抽出後に再分類されます。

### 6. ソリューションカテゴリ分類

GPT-4o-miniを使用して、事例のソリューションカテゴリを分類します。

## ディレクトリ構造

```text
nttdeta/
├── README.md
├── requirements.txt
├── run_nttdata_scraper.py
├── output/
│   └── YYYYMMDD_HHMMSS/
│       ├── nttdata_cases_YYYYMMDD_HHMMSS.json
│       ├── nttdata_cases_YYYYMMDD_HHMMSS.csv
│       └── scraper.log
└── nttdeta_scraper/
    ├── config/
    │   └── settings.py
    ├── models/
    │   └── scraper.py
    └── utils/
        ├── openai_client.py
        └── web_industry_classifier.py
```

## 注意事項

- Google APIには1日あたりのクエリ制限（100回）があります。制限に達した場合、インダストリーは「その他」に分類されます。
- スクレイピングは対象サイトに負荷をかける可能性があるため、適切な間隔を空けて実行してください。
- APIキーは`.env`ファイルで管理し、リポジトリにコミットしないでください。

## ライセンス

このプロジェクトはMITライセンスのもとで公開されています。
