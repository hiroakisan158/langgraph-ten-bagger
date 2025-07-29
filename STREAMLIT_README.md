# Deep Research Streamlit App

このアプリケーションは、Streamlitを使用してDeep ResearchシステムをWebインターフェースで利用できるようにしたものです。

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
ANTHROPIC_API_KEY=your_actual_anthropic_api_key
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

### 表示機能
- **研究結果**: 最終レポートの表示
- **詳細情報**: 研究プロセスの詳細を展開可能なセクションで表示
- **チャット履歴**: 過去の質問と回答の履歴

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

## トラブルシューティング

### よくある問題

1. **APIキーエラー**
   - `.env`ファイルに正しいAPIキーが設定されているか確認
   - APIキーの有効性を確認

2. **研究が完了しない**
   - サイドバーで研究設定を調整
   - より具体的な質問を試す

3. **エラーが発生する**
   - ログを確認してエラーの詳細を確認
   - 設定をリセットして再試行

## カスタマイズ

### プロンプトのカスタマイズ
銘柄調査用にカスタマイズする場合は、`src/open_deep_research/prompts.py`を編集してください。

### ツールの追加
新しいツールを追加する場合は、`src/open_deep_research/utils.py`を編集してください。

### UIのカスタマイズ
StreamlitのUIをカスタマイズする場合は、`streamlit_main.py`を編集してください。

## 注意事項

- 研究には時間がかかる場合があります
- API使用量に注意してください
- 機密情報は含めないでください 