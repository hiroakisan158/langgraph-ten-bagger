# 株式分析ツール - LLM投資判断支援ツール

LLMが企業の投資価値を効率的に判断するための2つの主要ツール群です。

## 📊 概要

このツールセットは、LLMが日本株投資の意思決定を行う際に必要な情報を提供します：

1. **割安性分析ツール** (`analyze_stock_valuation_tool`) - 企業が現在割安かどうかの総合判定
2. **成長性分析ツール** (`analyze_growth_potential_tool`) - 企業の将来性と成長トレンドの評価

## 🎯 設計思想

- **LLM-Friendly**: 複雑な計算は内部で行い、LLMが判断しやすい形で結果を提供
- **総合判定**: 個別指標ではなく、投資判断に直結する総合評価を重視
- **シンプル**: ツール選択に迷わないよう、用途別に2つのメインツールに集約

## 🛠️ 主要ツール

### 1. 割安性分析ツール (`analyze_stock_valuation_tool`)

企業の現在の株価が割安・適正・割高かを総合判定します。

#### 入力パラメータ
```python
code: str                    # 企業コード（4桁）
quarter: Optional[str]       # 四半期指定 ("1Q", "2Q", "3Q", "4Q", "Annual")
year: Optional[int]          # 年度指定 (例: 2025)
```

#### 出力データ構造
```python
{
    "code": "企業コード",
    "analysis_target": "分析対象（四半期・年度）",
    "stock_price": "現在株価",
    "fundamental_metrics": {
        "per": "PER値",
        "pbr": "PBR値", 
        "roe_percentage": "ROE率（%）",
        "roa_percentage": "ROA率（%）",
        "operating_margin_percentage": "営業利益率（%）",
        "net_margin_percentage": "純利益率（%）",
        "equity_ratio_percentage": "自己資本比率（%）"
    },
    "valuation_assessment": {
        "per_assessment": "PER評価（割安/適正/割高）",
        "pbr_assessment": "PBR評価",
        "roe_assessment": "ROE評価",
        "overall_valuation": "総合評価"
    },
    "investment_score": {
        "total_score": "投資魅力度スコア（100点満点）",
        "score_percentage": "スコア率（%）",
        "overall_rating": "総合レーティング",
        "score_details": "項目別詳細スコア"
    },
    "risk_factors": "リスク要因リスト",
    "investment_recommendation": "投資推奨度",
    "key_insights": "主要な洞察・注意点"
}
```

#### 使用例
```python
# 基本的な割安性分析
result = await analyze_stock_valuation_tool(code="7203")

# 特定四半期の分析
result = await analyze_stock_valuation_tool(code="7203", quarter="2Q", year=2024)

# LLMでの活用例
if result["investment_score"]["total_score"] >= 70:
    print(f"投資推奨: {result['investment_recommendation']}")
    print(f"主要ポイント: {', '.join(result['key_insights'])}")
```

### 2. 成長性分析ツール (`analyze_growth_potential_tool`)

企業の将来性と成長トレンドを総合分析します。

#### 入力パラメータ
```python
code: str                    # 企業コード（4桁）
analysis_years: int          # 分析対象年数（デフォルト3年）
```

#### 出力データ構造
```python
{
    "code": "企業コード",
    "analysis_period": "分析期間",
    "growth_metrics": {
        "revenue_cagr": "売上高年平均成長率（%）",
        "profit_cagr": "利益年平均成長率（%）",
        "eps_cagr": "EPS年平均成長率（%）",
        "latest_revenue_growth": "最新年売上成長率（%）",
        "latest_profit_growth": "最新年利益成長率（%）"
    },
    "growth_trend": {
        "revenue_trend": "売上トレンド（加速/安定/減速）",
        "profit_trend": "利益トレンド", 
        "roe_trend": "ROEトレンド",
        "consistency": "成長の一貫性評価"
    },
    "growth_quality": {
        "profitability_trend": "収益性改善傾向",
        "efficiency_trend": "効率性改善傾向"
    },
    "future_outlook": {
        "growth_sustainability": "成長持続性評価",
        "acceleration_potential": "成長加速可能性"
    },
    "growth_score": {
        "total_score": "成長性スコア（100点満点）",
        "growth_rating": "成長性レーティング"
    },
    "investment_timing": "投資タイミング評価",
    "growth_catalysts": "成長の推進要因",
    "growth_risks": "成長リスク要因"
}
```

#### 使用例
```python
# 基本的な成長性分析（3年間）
result = await analyze_growth_potential_tool(code="7203")

# 5年間での長期成長トレンド分析
result = await analyze_growth_potential_tool(code="7203", analysis_years=5)

# LLMでの活用例
if result["growth_score"]["total_score"] >= 70:
    print(f"成長性評価: {result['growth_score']['growth_rating']}")
    print(f"投資タイミング: {result['investment_timing']}")
```

## 📈 LLM投資判断フロー

### 1. 基本的な投資判断パターン
```python
# Step 1: 割安性チェック
valuation = await analyze_stock_valuation_tool(code="7203")
is_undervalued = valuation["investment_score"]["total_score"] >= 60

# Step 2: 成長性チェック  
growth = await analyze_growth_potential_tool(code="7203")
has_growth_potential = growth["growth_score"]["total_score"] >= 60

# Step 3: 総合判断
if is_undervalued and has_growth_potential:
    decision = "強く推奨"
elif is_undervalued:
    decision = "バリュー投資として推奨"
elif has_growth_potential:
    decision = "グロース投資として検討"
else:
    decision = "投資見送り"
```

### 2. リスク考慮判断パターン
```python
valuation = await analyze_stock_valuation_tool(code="7203")

# 高リスク要因のチェック
high_risk_factors = [
    risk for risk in valuation["risk_factors"] 
    if "高" in risk or "リスク" in risk
]

if len(high_risk_factors) > 2:
    decision = "リスクが高いため慎重に検討"
else:
    decision = valuation["investment_recommendation"]
```

## 🔧 技術仕様

### データソース
- **J-Quants API**: 財務諸表、株価データ
- **期間指定**: 四半期別・年度別の詳細分析
- **株価取得**: 決算期間終了日の正確な株価

### 計算方法
- **PER**: 株価 ÷ EPS（四半期は年率換算）
- **PBR**: 株価 ÷ BPS
- **ROE**: 当期純利益 ÷ 自己資本（四半期は年率換算）
- **CAGR**: 年平均成長率（複利計算）

### スコアリング
- **投資魅力度スコア**: 100点満点（PER 25点、PBR 20点、ROE 25点、財務健全性 15点、収益性 15点）
- **成長性スコア**: 100点満点（CAGR 40点、一貫性 20点、質的改善 20点、トレンド 20点）

## 🧪 テスト

```bash
# 全テスト実行
pytest test_stock_analysis.py -v

# 特定テストクラス実行
pytest test_stock_analysis.py::TestStockValuationTool -v

# カバレッジレポート
pytest test_stock_analysis.py --cov=stock_analysis_tool
```

## 📝 使用上の注意

1. **API制限**: J-Quants APIの呼び出し制限に注意（2秒間隔）
2. **データ可用性**: 決算発表前は最新データが取得できない場合があります
3. **四半期指定**: 四半期データは年率換算して表示されます
4. **エラーハンドリング**: データ取得失敗時は適切なエラーメッセージを返します

## 🚀 今後の拡張予定

- [ ] セクター比較機能
- [ ] ESG評価統合
- [ ] テクニカル分析要素
- [ ] ポートフォリオ最適化支援

---

## 📞 サポート

質問や提案がありましたら、開発チームまでご連絡ください。
