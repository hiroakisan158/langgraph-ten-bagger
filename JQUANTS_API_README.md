# J-Quants API 財務情報取得ツール

このツールは、J-Quants APIを使用して日本の上場企業の財務情報を取得・分析するPythonスクリプトです。

## 機能

### Freeプラン以上で利用可能
- 企業基本情報の取得（上場銘柄一覧）
- 財務諸表の取得
- 株価情報の取得（四本値）
- 決算発表予定日の取得
- 取引カレンダー情報の取得
- 複数企業の比較分析

### 上位プランで利用可能（推測）
- セクター情報の取得
- 企業検索機能

## セットアップ

### 1. 環境変数の設定

プロジェクトルートに`.env`ファイルを作成し、以下の内容を追加してください：

```env
# J-Quants API Configuration
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
JQUANTS_API_BASE_URL=https://api.jquants.com

# Optional: API rate limiting
JQUANTS_RATE_LIMIT_DELAY=1.0
```

### 2. リフレッシュトークンの取得

1. [J-Quants](https://jquants.com/)にアカウント登録
2. API利用申請を行う
3. リフレッシュトークンを取得
4. `.env`ファイルの`JQUANTS_REFRESH_TOKEN`に設定

## 使用方法

### 基本的な使用方法

```python
from open_deep_research.jquants_api import JQuantsAPI

# APIクライアントを初期化
api = JQuantsAPI()

# 企業情報を取得
company_info = api.get_company_info("8697")  # 楽天
print(f"企業名: {company_info['company_name']}")

# 財務諸表を取得
financial_data = api.get_financial_statements("8697")
print(f"売上高: {financial_data['data'][0]['net_sales']:,} 円")

# 株価情報を取得
stock_data = api.get_stock_price("8697", "2024-01-01", "2024-12-31")
```

### サンプルスクリプトの実行

```bash
# 基本的な使用例
python src/open_deep_research/jquants_example.py

# 個別のAPIモジュール
python src/open_deep_research/jquants_api.py
```

## 利用可能なAPIエンドポイント

### 企業情報
- `get_company_info(code)`: 企業の基本情報
- `search_companies(keyword)`: キーワードで企業を検索

### 財務データ
- `get_financial_statements(code, year)`: 財務諸表
- `get_earnings_forecast(code)`: 業績予想

### 株価データ
- `get_stock_price(code, date_from, date_to)`: 株価情報

### 市場・セクター情報
- `get_market_info(market)`: 市場情報
- `get_sector_info(sector_code)`: セクター情報

## データ形式

### 企業情報
```json
{
  "company_name": "楽天グループ株式会社",
  "code": "8697",
  "sector": "サービス業",
  "market": "東証プライム"
}
```

### 財務諸表
```json
{
  "data": [
    {
      "fiscal_year": "2024",
      "net_sales": 2000000000000,
      "operating_income": 150000000000,
      "net_income": 100000000000
    }
  ]
}
```

### 株価情報
```json
{
  "data": [
    {
      "date": "2024-12-20",
      "open": 2500,
      "high": 2550,
      "low": 2480,
      "close": 2520,
      "volume": 1000000
    }
  ]
}
```

## エラーハンドリング

スクリプトは以下のエラーを適切に処理します：

- 認証エラー
- API制限エラー
- ネットワークエラー
- データ形式エラー

## レート制限

J-Quants APIにはレート制限があります。デフォルトでは1秒間隔でリクエストを送信しますが、`.env`ファイルの`JQUANTS_RATE_LIMIT_DELAY`で調整可能です。

## 注意事項

1. **API制限**: J-Quants APIには利用制限があります。詳細は公式ドキュメントを確認してください。
2. **データの正確性**: 取得したデータは投資判断の参考情報として使用してください。
3. **認証情報**: リフレッシュトークンは機密情報です。`.env`ファイルをGitにコミットしないでください。

## トラブルシューティング

### よくあるエラー

1. **認証エラー (403 Forbidden)**
   - リフレッシュトークンが正しく設定されているか確認
   - トークンの有効期限を確認
   - J-Quants Webサイトから新しいトークンを取得
   - エラーメッセージ「Missing Authentication Token」が表示される場合は、リフレッシュトークンが無効です

2. **API制限エラー**
   - レート制限の設定を調整
   - リクエスト頻度を下げる
   - APIプランの確認（Free/Light/Standard/Premium）

3. **データ取得エラー**
   - 企業コードが正しいか確認
   - 指定した期間にデータが存在するか確認

4. **設定エラー**
   - `.env`ファイルが正しく作成されているか確認
   - 環境変数名が正確か確認（`JQUANTS_REFRESH_TOKEN`）

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 参考リンク

- [J-Quants公式サイト](https://jquants.com/)
- [J-Quants API ドキュメント](https://jquants.com/api)
- [J-Quants API クイックスタート](https://jquants.com/api/quickstart)
