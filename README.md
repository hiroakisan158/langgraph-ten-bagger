# Deep Research Assistant - テンバガー発見ツール

Deep Research技術を使用して潜在的な「テンバガー」（10倍成長する可能性のある株式）を発見し、包括的な市場分析を実施する包括的な研究アシスタントです。

## クイックスタート

### 方法1: 直接Streamlit実行
```bash
streamlit run streamlit_main.py
```

### 方法2: Dockerビルド＆実行
```bash
# Dockerイメージをビルド
docker build -t ten-baggers-app:latest .

# コンテナを実行
docker run -p 8501:8501 ten-baggers-app:latest
```

## セットアップ

### 1. 環境変数の設定

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

### 2. 依存関係のインストール

**pipを使用（推奨）**
```bash
pip install -e .
```

### 3. アプリケーションの実行

```bash
streamlit run streamlit_main.py
```

アプリケーションは `http://localhost:8501` で起動します。

## 機能

### メイン機能
- **チャットインターフェース**: ユーザーの質問を入力してDeep Researchを実行
- **リアルタイム研究**: 質問に対して包括的な研究を自動実行
- **結果表示**: 研究結果をマークダウン形式で表示

### サイドバー設定
- **Research Settings**: 並行研究ユニット数、研究イテレーション数、確認質問の許可
- **Model Settings**: 使用する研究モデルの選択
- **Search Settings**: 検索APIの選択

## 使用例

### 基本的な質問
```
"量子コンピューティングの最新動向について調べてください"
```

### 企業分析
```
"Apple社の最新の業績と成長戦略について調べてください"
```

### 技術調査
```
"AI技術の2024年の主要トレンドについて調べてください"
```

### 株式分析（テンバガー特化）
```
"AIセクターの潜在的なテンバガー株式を調べてください"
"Teslaの成長可能性と市場ポジションを分析してください"
"電気自動車市場の新興企業を調べてください"
```

## カスタマイズ

### プロンプトのカスタマイズ
株式分析用にカスタマイズする場合は、`src/open_deep_research/prompts.py`を編集してください：

- **`transform_messages_into_research_topic_prompt`**: 銘柄名と分析観点を抽出
- **`lead_researcher_prompt`**: 株式分析の観点（業績、財務、競合、成長性、リスク）を定義
- **`research_system_prompt`**: 株式特化の情報源を優先
- **`final_report_generation_prompt`**: 株式分析レポートの構成

### ツールの追加
新しいツールを追加する場合は、`src/open_deep_research/utils.py`を編集してください

### UIのカスタマイズ
StreamlitのUIをカスタマイズする場合は、`streamlit_main.py`を編集してください

## アーキテクチャ

### Deep Researchシステム
- **スーパーバイザーエージェント**: `lead_researcher_prompt`を使用して調査戦略を調整
- **研究エージェント**: `research_system_prompt`を使用して特定の調査タスクを実行
- **ツール統合**: Web検索、MCPツール、カスタムツール
- **レポート生成**: 発見事項を包括的なレポートに統合

### 主要コンポーネント
- `src/open_deep_research/deep_researcher.py`: メイン調査ワークフロー
- `src/open_deep_research/prompts.py`: システムプロンプト
- `src/open_deep_research/utils.py`: ツールとユーティリティ
- `streamlit_main.py`: Webインターフェース

## 注意事項
- 特定の投資信託、生命保険、株式、債券等の売買を推奨･勧誘するものではありません。
- 当システムの出力内容に基づいて取られた投資行動の結果については、責任を負いません。