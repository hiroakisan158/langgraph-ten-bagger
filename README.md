# Deep Research Assistant - 株式投資分析ツール

J-Quants APIと高度なDeep Research技術を活用した包括的な株式投資分析システムです。現在の株価情報取得から詳細な企業分析まで、投資判断に必要な情報を自動収集・分析します。

## 主要機能

### 株式分析特化機能
- **現在株価取得**: J-Quants APIで直近の株価・出来高データを自動取得
- **財務分析**: 売上・利益・ROE等の詳細財務指標分析
- **割安・割高判断**: PER/PBR等の指標による客観的評価
- **業界分析**: 競合他社との比較分析
- **リスク評価**: 事業・財務・市場リスクの包括的評価

### J-Quants APIツール
- **get_recent_stock_price_tool**: 企業コードから現在の株価情報を取得
- **get_financial_statements_tool**: 財務諸表データの詳細分析

## クイックスタート

### 方法1: Docker Compose（推奨）
最も簡単で確実な方法です。

```bash
# 1. 環境変数ファイルを作成
cp .env.template .env

# 2. .envファイルを編集して実際のAPIキーを設定
# OPENAI_API_KEY=your_actual_openai_api_key
# JQUANTS_REFRESH_TOKEN=your_actual_jquants_refresh_token
# など

# 3. アプリケーションをビルド・起動
docker-compose up

# バックグラウンドで起動する場合
docker-compose up -d

# ログを確認
docker-compose logs -f
```

アプリケーションは `http://localhost:8501` で起動します。

### 方法2: シンプルデプロイスクリプト
```bash
# 自動デプロイスクリプトを実行
./deploy.sh
```

### 方法3: 直接Streamlit実行
```bash
streamlit run streamlit_main.py
```

### 方法4: Dockerビルド＆実行
```bash
# Dockerイメージをビルド
docker build -t ten-baggers-app:latest .

# コンテナを実行
docker run -p 8501:8501 ten-baggers-app:latest
```

## セットアップ

### 1. Python仮想環境の構築

```bash
# 仮想環境を作成
python -m venv .venv

# 仮想環境をアクティベート 
source .venv/bin/activate
```

### 2. 環境変数の設定

`.env`ファイルを作成し、必要なAPIキーを設定してください：

```bash
# .envファイルを作成
cp streamlit_env_example.txt .env
```

`.env`ファイルを編集して、実際のAPIキーを設定：

```bash
OPENAI_API_KEY=your_actual_openai_api_key
TAVILY_API_KEY=your_actual_tavily_api_key
```

#### J-Quants API設定

J-Quants APIを使用して日本株の株価・財務データを取得します。

- **何に使うか**: 日本の上場企業の現在の株価、財務諸表、業績データの取得
- **取得方法**: [J-Quants](https://jpx-jquants.com/)でアカウント登録後、リフレッシュトークンを発行 (最新の株価と過去5年分の財務情報取得のためにライトプランへ課金登録が必要)
- **設定方法**: `.env`に以下を追加

```bash
JQUANTS_REFRESH_TOKEN=your_actual_jquants_refresh_token
```

### 3. 依存関係のインストール

**方法1: pip（通常）**
```bash
pip install -e .
```

**方法2: uv（高速、推奨）**
```bash
# uvをインストール（まだの場合）
pip install uv

# 依存関係をインストール
uv pip install -e .
```

### 4. アプリケーションの実行

```bash
streamlit run streamlit_main.py
```

アプリケーションは `http://localhost:8501` で起動します。

## Docker Composeを使用したデプロイ

### 📋 事前準備

1. **環境変数ファイルの作成**
   ```bash
   cp .env.template .env
   ```

2. **.envファイルの編集**
   ```bash
   # 必須設定項目
   OPENAI_API_KEY=your_actual_openai_api_key
   JQUANTS_REFRESH_TOKEN=your_actual_jquants_refresh_token
   
   # オプション設定
   LANGFUSE_SECRET_KEY=your_langfuse_secret_key
   LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
   LANGFUSE_HOST=https://cloud.langfuse.com
   TAVILY_API_KEY=your_tavily_api_key
   GROQ_API_KEY=your_groq_api_key
   ```

### 🚀 基本操作

```bash
# アプリケーションを起動（フォアグラウンド）
docker-compose up

# アプリケーションを起動（バックグラウンド）
docker-compose up -d

# ビルドから実行まで一括
docker-compose up --build

# 停止
docker-compose down

# 停止してボリュームも削除
docker-compose down -v
```

### 📊 ログとモニタリング

```bash
# リアルタイムログの確認
docker-compose logs -f

# 特定サービスのログ
docker-compose logs -f app

# コンテナの状態確認
docker-compose ps

# ヘルスチェックの確認
docker-compose ps
```

### 🔧 トラブルシューティング

```bash
# コンテナに入ってデバッグ
docker-compose exec app bash

# イメージを完全にリビルド
docker-compose down
docker-compose build --no-cache
docker-compose up

# ボリュームをクリア
docker system prune -f
docker volume prune -f
```

### 🌐 Azure App Serviceでのデプロイ

Azure App ServiceでWebアプリとしてデプロイする場合：

1. **docker-compose.ymlをそのまま使用**
2. **環境変数をApp ServiceのApplication Settingsで設定**
   - App Service側の環境変数が優先されます
   - `.env`ファイルの値は上書きされます

```bash
# Azure CLI example
az webapp config appsettings set \
  --resource-group <resource-group> \
  --name <app-name> \
  --settings \
    OPENAI_API_KEY="<your-key>" \
    JQUANTS_REFRESH_TOKEN="<your-token>" \
    WEBSITES_PORT="8501"
```

### 📁 ファイル構成

Docker関連のファイル構成：
```
├── Dockerfile              # アプリケーションイメージ定義
├── docker-compose.yml      # サービス構成定義
├── .dockerignore           # Dockerビルド時の除外ファイル
├── .env.template           # 環境変数テンプレート
├── .env                    # 実際の環境変数（作成必要）
├── deploy.sh               # 自動デプロイスクリプト
└── .streamlit/config.toml  # Streamlit設定
```

## 機能

### メイン機能
- **チャットインターフェース**: ユーザーの質問を入力してDeep Researchを実行
- **リアルタイム調査**: 質問に対して包括的な調査を自動実行
- **結果表示**: 調査結果をマークダウン形式で表示

## 使用例

### 株式分析の例

```
"トヨタ自動車（7203）の投資妙味を分析してください"
"ソフトバンクグループ（9984）の現在の株価水準は割安ですか？"
"半導体関連銘柄で成長性の高い企業を教えてください"
"楽天（4755）の事業モデルと競争優位性を分析してください"
```

### 分析に含まれる項目
- 現在の株価情報（終値、出来高、高値・安値）
- 財務指標分析（売上、利益、ROE、ROA等）
- 事業分析（収益構造、競争優位性）
- 業界環境（市場規模、競合状況）
- 投資判断（割安・割高・適正の評価）

## システム設計

### 株式分析に特化したプロンプト設計

最新のプロンプト設計では、現在の株価情報取得を最優先とし、包括的な投資分析を行います：

#### lead_researcher_prompt
- **最優先タスク**: 現在の株価情報の取得を必須化
- **分析観点**: 財務・事業・業界・リスク・割安割高判断を体系化
- **実行順序**: ConductResearchツールの必須実行を明記

#### stock_analysis_researcher_system_prompt  
- **必須の初期ステップ**: get_recent_stock_price_toolの最優先実行
- **J-Quantsツール優先**: 株価・財務データ取得を他ツールより優先
- **ResearchComplete制御**: 十分な調査完了後のみ実行を許可

#### 最終レポート生成
- **現在株価セクション**: 直近の株価動向を独立章として追加
- **投資判断**: 現在株価を基準とした割安・割高・適正の明確な判定
- **適正株価推定**: 将来成長性を考慮した価格レンジ算出

### J-Quants APIツール統合

#### get_recent_stock_price_tool
- **機能**: 企業コード（4桁）から直近1週間の株価データを取得
- **優先度**: 全ツール中で最優先実行
- **データ**: 終値、出来高、高値・安値、変動率等

#### get_financial_statements_tool
- **機能**: 企業の財務諸表データを取得・分析
- **データ**: 売上、利益、ROE、ROA、財務比率等
- **年度指定**: 特定年度または最新データの取得が可能

### アーキテクチャ概要

- **スーパーバイザーエージェント**: 株価取得を最優先とした調査戦略を制御
- **調査エージェント**: J-Quants APIツールを活用した専門的株式分析
- **レポート生成**: 現在株価を基準とした投資判断レポートを自動生成

### 主要ファイル
- `src/open_deep_research/deep_researcher.py`: メイン分析ワークフロー
- `src/open_deep_research/prompts_jp.py`: 株式分析特化プロンプト
- `src/open_deep_research/utils.py`: J-Quants APIツール実装
- `src/open_deep_research/jquants_api.py`: J-Quants API接続クライアント
- `streamlit_main.py`: Webインターフェース

## J-Quants APIテスト

企業コードでの株価取得をテストする場合：

```python
# test_stock_price.py
from src.open_deep_research.jquants_api import JQuantsAPI

api = JQuantsAPI()
result = api.get_stock_price(code="7203")  # トヨタ
print(result)
```

```bash
python test_stock_price.py
```

## think_tool について

### 概要
`think_tool`は、調査プロセスの各段階で戦略的思考・計画・評価を行うための専用ツールです。AIエージェントが調査開始前・各ツール実行後・調査完了前に必ず呼び出し、現状の分析・課題・次のアクションを明確化します。

### 主な役割
- 調査開始時：調査方針・優先事項の計画
- ツール実行後：得られた情報の評価・残る課題の整理
- 調査完了前：情報の十分性・追加調査の必要性の最終判断

### 使い方
AIエージェントは、以下のタイミングで`think_tool`を必ず呼び出します：
1. 調査計画立案（最初）
2. 各ツール実行後の評価
3. 調査完了前の最終確認

#### 例
```
think_tool(reflection="今回の調査では株価情報を最優先で取得し、次に財務分析を行う。現時点で競合情報が不足しているため、追加調査が必要。")
```

### 重要ポイント
- `think_tool`の呼び出しは調査品質・網羅性・戦略性を担保するため必須です。
- スキップすると調査の抜け漏れや非効率が発生します。
- 実行時にはログ出力され、調査の思考過程が記録されます。

### 実装ファイル
- `src/open_deep_research/utils.py`（ツール本体）
- `src/open_deep_research/prompts_jp.py`（プロンプトでの利用指示）

## 免責事項

このシステムは投資判断の参考情報提供を目的としており、特定の投資を推奨するものではありません。投資の最終判断は利用者の責任で行ってください。システムの分析結果に基づく投資行動の結果について、開発者は責任を負いません。
