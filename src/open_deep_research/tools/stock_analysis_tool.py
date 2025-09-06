"""
株式分析ツール - 成長性と割安性判断に特化したツール群
LLMが企業の投資価値を効率的に判断するための2つの主要ツール
"""
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from jquants_api import JQuantsAPI
from dotenv import load_dotenv

load_dotenv()  # .envファイルから環境変数をロード


# ツールの説明
VALUATION_ANALYSIS_DESCRIPTION = (
    "企業の割安性を総合判定します。PER、PBR、ROE等の主要財務指標を一括計算し、"
    "現在の株価が割安・適正・割高かを判断するための包括的な財務分析を提供します。"
    "四半期指定可能（1Q, 2Q, 3Q, FY, Annual）、年度指定可能（例：2025）。"
    "戻り値：財務比率、割安性判定、投資魅力度スコア、リスク要因を含む投資判断データ。"
    "LLMがこの企業への投資を検討する際の主要判断材料となります。"
)

GROWTH_ANALYSIS_DESCRIPTION = (
    "企業の成長性を総合分析します。売上・利益の成長率、ROEトレンド、四半期推移等を分析し、"
    "将来の成長性を評価します。複数年度データから成長の持続性と加速度を判定します。"
    "四半期指定可能（1Q, 2Q, 3Q, FY, Annual）、分析年数指定可能（デフォルト3年）。"
    "戻り値：成長率（CAGR、前年比）、成長トレンド、成長の質、将来性評価を含む成長分析データ。"
    "LLMがこの企業の将来性を評価する際の主要判断材料となります。"
)

# Rate limiting management
_last_api_call_time = 0
_min_delay_between_calls = 2.0

async def rate_limit_delay():
    """API呼び出し間に適切な遅延を挿入"""
    global _last_api_call_time
    current_time = time.time()
    time_since_last_call = current_time - _last_api_call_time
    
    if time_since_last_call < _min_delay_between_calls:
        await asyncio.sleep(_min_delay_between_calls - time_since_last_call)
    
    _last_api_call_time = time.time()


def normalize_period(period: Optional[str]) -> Optional[str]:
    """四半期指定を正規化する。'Annual' や '4Q' は 'FY' に統一。

    Args:
        period: 指定四半期（例: '1Q', '2Q', '3Q', 'FY', 'Annual', '4Q', 'Q4'）

    Returns:
        正規化済み四半期（'1Q' | '2Q' | '3Q' | 'FY'）または None
    """
    if not period:
        return None
    p = str(period).strip().upper()
    mapping = {
        "ANNUAL": "FY",
        "FY": "FY",
        "4Q": "FY",
        "Q4": "FY",
        "1Q": "1Q",
        "2Q": "2Q",
        "3Q": "3Q",
    }
    return mapping.get(p, period)


def safe_float_conversion(value: Any) -> Optional[float]:
    """安全に文字列や数値をfloatに変換"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def get_latest_financial_data(financial_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """財務データから最新の決算データを取得"""
    if not financial_data or "statements" not in financial_data:
        return None
    
    statements = financial_data["statements"]
    if not statements:
        return None
    
    # 最新の決算データを取得（日付でソート）
    latest_statement = max(statements, key=lambda x: x.get("DisclosedDate", ""))
    return latest_statement


def get_quarterly_financial_data(financial_data: Dict[str, Any], quarter: Optional[str] = None, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """財務データから指定四半期・年度の決算データを取得"""
    if not financial_data or "statements" not in financial_data:
        return None
    
    statements = financial_data["statements"]
    if not statements:
        return None
    
    # 四半期・年度指定がない場合は最新データを返す
    if quarter is None and year is None:
        return get_latest_financial_data(financial_data)
    
    # 指定条件に合うデータを検索
    filtered_statements = statements
    
    # 四半期でフィルタ
    if quarter is not None:
        filtered_statements = [s for s in filtered_statements if s.get("TypeOfCurrentPeriod") == quarter]
    
    # 年度でフィルタ
    if year is not None:
        # 指定年度の決算データを検索
        # 年度は企業により決算期が異なるため、柔軟に対応
        # 例: 2024年度 → 2024年または2025年の決算期末日
        temp_filtered = []
        for s in filtered_statements:
            fiscal_year_end = s.get("CurrentFiscalYearEndDate", "")
            if fiscal_year_end:
                # 決算期末日から年度を判定
                if fiscal_year_end.startswith(str(year)) or fiscal_year_end.startswith(str(year + 1)):
                    # 期首日も確認して正確な年度を判定
                    fiscal_year_start = s.get("CurrentFiscalYearStartDate", "")
                    if fiscal_year_start.startswith(str(year)):
                        temp_filtered.append(s)
        filtered_statements = temp_filtered
    
    if not filtered_statements:
        return None
    
    # 指定条件の最新データを取得
    return max(filtered_statements, key=lambda x: x.get("DisclosedDate", ""))


def get_latest_stock_price(stock_data: Dict[str, Any]) -> Optional[float]:
    """株価データから最新の終値を取得"""
    if not stock_data or "daily_quotes" not in stock_data:
        return None
    
    quotes = stock_data["daily_quotes"]
    if not quotes:
        return None
    
    # 最新の株価データを取得（日付でソート）
    latest_quote = max(quotes, key=lambda x: x.get("Date", ""))
    return safe_float_conversion(latest_quote.get("Close"))


def get_period_end_stock_price(financial_statement: Dict[str, Any], api: JQuantsAPI, code: str) -> Optional[float]:
    """指定された決算期間の最終日の株価を取得"""
    if not financial_statement:
        return None
    
    # 決算期間の終了日を取得
    period_end = financial_statement.get("CurrentPeriodEndDate")
    if not period_end:
        return None
    
    try:
        # 期間終了日の前後の株価データを取得
        end_date = datetime.strptime(period_end, "%Y-%m-%d")
        start_date = end_date - timedelta(days=7)  # 営業日を考慮して1週間前から
        
        date_from = start_date.strftime("%Y-%m-%d")
        date_to = end_date.strftime("%Y-%m-%d")
        
        stock_data = api.get_stock_price(code=code, date_from=date_from, date_to=date_to)
        
        if not stock_data or "daily_quotes" not in stock_data:
            return None
        
        quotes = stock_data["daily_quotes"]
        if not quotes:
            return None
        
        # 期間終了日に最も近い営業日の株価を取得
        target_quote = max(quotes, key=lambda x: x.get("Date", ""))
        return safe_float_conversion(target_quote.get("Close"))
        
    except Exception:
        return None


def calculate_investment_attractiveness_score(ratios: Dict[str, Any], financials: Dict[str, Any]) -> Dict[str, Any]:
    """投資魅力度スコアを計算（100点満点）"""
    score = 0
    details = {}
    
    # PER評価（25点満点）
    per = ratios.get("per")
    if per is not None:
        if per < 10:
            score += 25
            details["per_score"] = 25
            details["per_comment"] = "割安（25点）"
        elif per < 15:
            score += 20
            details["per_score"] = 20
            details["per_comment"] = "やや割安（20点）"
        elif per < 25:
            score += 10
            details["per_score"] = 10
            details["per_comment"] = "適正（10点）"
        else:
            score += 0
            details["per_score"] = 0
            details["per_comment"] = "割高（0点）"
    
    # PBR評価（20点満点）
    pbr = ratios.get("pbr")
    if pbr is not None:
        if pbr < 1:
            score += 20
            details["pbr_score"] = 20
            details["pbr_comment"] = "割安（20点）"
        elif pbr < 1.5:
            score += 15
            details["pbr_score"] = 15
            details["pbr_comment"] = "やや割安（15点）"
        elif pbr < 3:
            score += 8
            details["pbr_score"] = 8
            details["pbr_comment"] = "適正（8点）"
        else:
            score += 0
            details["pbr_score"] = 0
            details["pbr_comment"] = "割高（0点）"
    
    # ROE評価（25点満点）
    roe = ratios.get("roe_percentage_annualized") or ratios.get("roe_percentage")
    if roe is not None:
        if roe > 20:
            score += 25
            details["roe_score"] = 25
            details["roe_comment"] = "優秀（25点）"
        elif roe > 15:
            score += 20
            details["roe_score"] = 20
            details["roe_comment"] = "良好（20点）"
        elif roe > 10:
            score += 12
            details["roe_score"] = 12
            details["roe_comment"] = "普通（12点）"
        else:
            score += 0
            details["roe_score"] = 0
            details["roe_comment"] = "低い（0点）"
    
    # 財務健全性評価（15点満点）
    equity_ratio = ratios.get("equity_ratio_percentage")
    if equity_ratio is not None:
        if equity_ratio > 50:
            score += 15
            details["stability_score"] = 15
            details["stability_comment"] = "安定（15点）"
        elif equity_ratio > 30:
            score += 10
            details["stability_score"] = 10
            details["stability_comment"] = "普通（10点）"
        else:
            score += 5
            details["stability_score"] = 5
            details["stability_comment"] = "やや不安（5点）"
    
    # 収益性評価（15点満点）
    operating_margin = ratios.get("operating_margin_percentage")
    if operating_margin is not None:
        if operating_margin > 15:
            score += 15
            details["profitability_score"] = 15
            details["profitability_comment"] = "高収益（15点）"
        elif operating_margin > 8:
            score += 10
            details["profitability_score"] = 10
            details["profitability_comment"] = "普通（10点）"
        else:
            score += 5
            details["profitability_score"] = 5
            details["profitability_comment"] = "低収益（5点）"
    
    # 総合評価
    if score >= 80:
        overall_rating = "投資魅力度：非常に高い"
    elif score >= 60:
        overall_rating = "投資魅力度：高い"
    elif score >= 40:
        overall_rating = "投資魅力度：中程度"
    else:
        overall_rating = "投資魅力度：低い"
    
    return {
        "total_score": score,
        "max_score": 100,
        "score_percentage": round((score / 100) * 100, 1),
        "overall_rating": overall_rating,
        "score_details": details
    }


@tool(description=VALUATION_ANALYSIS_DESCRIPTION)
async def analyze_stock_valuation_tool(
    code: str,
    quarter: Optional[str] = None,
    year: Optional[int] = None,
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """
    企業の割安性を総合判定するメインツール。
    LLMが投資判断を行うための包括的な財務分析を提供します。
    
    Args:
        code (str): 企業コード（4桁）
        quarter (Optional[str]): 四半期指定 ("1Q", "2Q", "3Q", "FY", "Annual")
        year (Optional[int]): 年度指定 (例: 2025)
        
    Returns:
        Dict[str, Any]: 割安性分析結果
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
    """
    try:
        await rate_limit_delay()
        api = JQuantsAPI()
        
        # 財務データを取得
        financial_data = api.get_financial_statements(code, year)
        # 四半期指定を正規化（Annual/4Q/Q4 → FY）
        normalized_quarter = normalize_period(quarter)
        latest_financial = get_quarterly_financial_data(financial_data, normalized_quarter, year)
        
        if not latest_financial:
            return {
                "error": "財務データの取得に失敗しました",
                "code": code,
                "quarter": quarter,
                "year": year
            }
        
        # 決算期間終了日の株価を取得
        period_end_price = get_period_end_stock_price(latest_financial, api, code)
        
        if period_end_price is None:
            # 現在の株価を取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=10)
            date_from = start_date.strftime("%Y-%m-%d")
            date_to = end_date.strftime("%Y-%m-%d")
            
            stock_data = api.get_stock_price(code=code, date_from=date_from, date_to=date_to)
            period_end_price = get_latest_stock_price(stock_data)
        
        if period_end_price is None:
            return {
                "error": "株価データの取得に失敗しました",
                "code": code
            }
        
        # 基本財務数値を取得
        net_sales = safe_float_conversion(latest_financial.get("NetSales"))
        operating_profit = safe_float_conversion(latest_financial.get("OperatingProfit"))
        profit = safe_float_conversion(latest_financial.get("Profit"))
        total_assets = safe_float_conversion(latest_financial.get("TotalAssets"))
        equity = safe_float_conversion(latest_financial.get("Equity"))
        eps = safe_float_conversion(latest_financial.get("EarningsPerShare"))
        bps = safe_float_conversion(latest_financial.get("BookValuePerShare"))
        
        # 財務比率計算
        ratios = {}
        
        # PER計算
        if eps and eps > 0:
            ratios["per"] = round(period_end_price / eps, 2)
        
        # PBR計算
        if bps and bps > 0:
            ratios["pbr"] = round(period_end_price / bps, 2)
        elif equity and eps and profit and profit != 0:
            shares_outstanding = profit / eps
            calculated_bps = equity / shares_outstanding
            ratios["pbr"] = round(period_end_price / calculated_bps, 2)
        
        # ROE計算
        if profit and equity and equity > 0:
            roe = (profit / equity) * 100
            ratios["roe_percentage"] = round(roe, 2)
            
            # 四半期データの場合は年率換算（累計データから年率推定）
            period_type = latest_financial.get("TypeOfCurrentPeriod", "")
            if quarter and period_type in ["1Q", "2Q", "3Q"]:
                # 四半期累計データから年率を推定
                if period_type == "1Q":
                    # 1Qは3ヶ月累計なので4倍
                    ratios["roe_percentage_annualized"] = round(roe * 4, 2)
                elif period_type == "2Q":
                    # 2Qは6ヶ月累計なので2倍
                    ratios["roe_percentage_annualized"] = round(roe * 2, 2)
                elif period_type == "3Q":
                    # 3Qは9ヶ月累計なので4/3倍
                    ratios["roe_percentage_annualized"] = round(roe * 4/3, 2)
        
        # その他の比率計算
        if profit and total_assets and total_assets > 0:
            ratios["roa_percentage"] = round((profit / total_assets) * 100, 2)
        
        if operating_profit and net_sales and net_sales > 0:
            ratios["operating_margin_percentage"] = round((operating_profit / net_sales) * 100, 2)
        
        if profit and net_sales and net_sales > 0:
            ratios["net_margin_percentage"] = round((profit / net_sales) * 100, 2)
        
        if equity and total_assets and total_assets > 0:
            ratios["equity_ratio_percentage"] = round((equity / total_assets) * 100, 2)
        
        # 評価判定
        valuation_assessment = {}
        
        # PER評価
        if "per" in ratios:
            per_value = ratios["per"]
            if per_value < 10:
                valuation_assessment["per_assessment"] = "割安"
            elif per_value > 25:
                valuation_assessment["per_assessment"] = "割高"
            else:
                valuation_assessment["per_assessment"] = "適正範囲"
        
        # PBR評価
        if "pbr" in ratios:
            pbr_value = ratios["pbr"]
            if pbr_value < 1:
                valuation_assessment["pbr_assessment"] = "割安"
            elif pbr_value > 3:
                valuation_assessment["pbr_assessment"] = "割高"
            else:
                valuation_assessment["pbr_assessment"] = "適正範囲"
        
        # ROE評価
        roe_value = ratios.get("roe_percentage_annualized") or ratios.get("roe_percentage")
        if roe_value:
            if roe_value > 15:
                valuation_assessment["roe_assessment"] = "優秀"
            elif roe_value > 10:
                valuation_assessment["roe_assessment"] = "良好"
            else:
                valuation_assessment["roe_assessment"] = "改善余地あり"
        
        # 投資魅力度スコア計算
        financials = {
            "net_sales": net_sales,
            "operating_profit": operating_profit,
            "profit": profit,
            "total_assets": total_assets,
            "equity": equity
        }
        investment_score = calculate_investment_attractiveness_score(ratios, financials)
        
        # リスク要因分析
        risk_factors = []
        if ratios.get("per", 0) > 30:
            risk_factors.append("PER高水準（成長期待値高、下落リスク）")
        if ratios.get("pbr", 0) < 0.8:
            risk_factors.append("PBR低水準（業績悪化リスク可能性）")
        if ratios.get("equity_ratio_percentage", 0) < 30:
            risk_factors.append("自己資本比率低（財務安定性リスク）")
        if ratios.get("operating_margin_percentage", 0) < 5:
            risk_factors.append("営業利益率低（収益性リスク）")
        
        # 投資推奨度
        score = investment_score["total_score"]
        if score >= 80:
            recommendation = "強く推奨"
        elif score >= 60:
            recommendation = "推奨"
        elif score >= 40:
            recommendation = "中立"
        else:
            recommendation = "非推奨"
        
        # 主要洞察
        key_insights = []
        if ratios.get("per", 0) < 15 and roe_value and roe_value > 12:
            key_insights.append("割安かつ高ROE企業として魅力的")
        if ratios.get("operating_margin_percentage", 0) > 15:
            key_insights.append("高い営業利益率で競争優位性を示唆")
        if ratios.get("equity_ratio_percentage", 0) > 60:
            key_insights.append("財務安定性が高く、リスク耐性良好")
        
        # 総合評価
        if len([v for v in valuation_assessment.values() if "割安" in str(v)]) >= 2:
            overall_valuation = "割安"
        elif len([v for v in valuation_assessment.values() if "割高" in str(v)]) >= 2:
            overall_valuation = "割高"
        else:
            overall_valuation = "適正"
        
        valuation_assessment["overall_valuation"] = overall_valuation
        
        return {
            "code": code,
            "analysis_target": f"{year or '最新'}年度 {normalized_quarter or '最新期'}",
            "stock_price": period_end_price,
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "period": f"{latest_financial.get('CurrentPeriodStartDate')} - {latest_financial.get('CurrentPeriodEndDate')}",
            "fundamental_metrics": ratios,
            "valuation_assessment": valuation_assessment,
            "investment_score": investment_score,
            "risk_factors": risk_factors,
            "investment_recommendation": recommendation,
            "key_insights": key_insights
        }
        
    except Exception as e:
        return {
            "error": f"割安性分析エラー: {str(e)}",
            "code": code,
            "quarter": quarter,
            "year": year
        }


@tool(description=GROWTH_ANALYSIS_DESCRIPTION)
async def analyze_growth_potential_tool(
    code: str,
    analysis_years: int = 3,
    quarter: Optional[str] = "Annual",
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """
    企業の成長性を総合分析するメインツール。
    LLMが将来性を評価するための成長トレンド分析を提供します。
    
    Args:
        code (str): 企業コード（4桁）
        analysis_years (int): 分析対象年数（デフォルト3年）
        quarter (Optional[str]): 対象四半期 ("1Q", "2Q", "3Q", "FY", "Annual") デフォルトは"Annual"
        
    Returns:
        Dict[str, Any]: 成長性分析結果
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
                    "efficiency_trend": "効率性改善傾向",
                    "margin_expansion": "利益率拡大状況"
                },
                "future_outlook": {
                    "growth_sustainability": "成長持続性評価",
                    "acceleration_potential": "成長加速可能性",
                    "competitive_position": "競争力評価"
                },
                "growth_score": {
                    "total_score": "成長性スコア（100点満点）",
                    "growth_rating": "成長性レーティング"
                },
                "investment_timing": "投資タイミング評価",
                "growth_catalysts": "成長の推進要因",
                "growth_risks": "成長リスク要因"
            }
    """
    try:
        await rate_limit_delay()
        api = JQuantsAPI()
        
        # 複数年のデータを取得
        current_year = datetime.now().year
        yearly_data = []
        
        # 四半期指定を正規化（Annual/4Q/Q4 → FY）
        normalized_quarter = normalize_period(quarter)
        
        for i in range(analysis_years):
            year = current_year - i
            financial_data = api.get_financial_statements(code, year)
            if financial_data and "statements" in financial_data and financial_data["statements"]:
                # 正規化された四半期のデータを取得
                target_statement = get_quarterly_financial_data(financial_data, normalized_quarter, year)
                if not target_statement and normalized_quarter == "FY":
                    # FYがない場合は最新の通期データを取得
                    annual_statements = [s for s in financial_data["statements"] 
                                       if s.get("TypeOfCurrentPeriod") in ["FY", "Annual"] or 
                                       s.get("TypeOfCurrentPeriod") is None]
                    if annual_statements:
                        target_statement = max(annual_statements, key=lambda x: x.get("DisclosedDate", ""))
                
                if target_statement:
                    yearly_data.append({
                        "year": year,
                        "quarter": normalized_quarter or "FY",  # 正規化された四半期を使用
                        "data": target_statement
                    })
        
        if len(yearly_data) < 2:
            return {
                "error": f"成長性分析には最低2年分の{normalized_quarter or quarter}データが必要です",
                "code": code,
                "quarter": quarter,
                "normalized_quarter": normalized_quarter,
                "available_years": len(yearly_data)
            }
        
        # 時系列順にソート（古い年から新しい年へ）
        yearly_data.sort(key=lambda x: x["year"])
        
        # 各年のメトリクスを収集
        metrics_by_year = []
        for year_info in yearly_data:
            year = year_info["year"]
            data = year_info["data"]
            
            metrics = {
                "year": year,
                "quarter": year_info["quarter"],
                "period_type": data.get("TypeOfCurrentPeriod", "Unknown"),
                "net_sales": safe_float_conversion(data.get("NetSales")),
                "operating_profit": safe_float_conversion(data.get("OperatingProfit")),
                "profit": safe_float_conversion(data.get("Profit")),
                "total_assets": safe_float_conversion(data.get("TotalAssets")),
                "equity": safe_float_conversion(data.get("Equity")),
                "eps": safe_float_conversion(data.get("EarningsPerShare"))
            }
            
            # ROE計算
            if metrics["profit"] and metrics["equity"] and metrics["equity"] > 0:
                metrics["roe"] = (metrics["profit"] / metrics["equity"]) * 100
            
            # 利益率計算
            if metrics["operating_profit"] and metrics["net_sales"] and metrics["net_sales"] > 0:
                metrics["operating_margin"] = (metrics["operating_profit"] / metrics["net_sales"]) * 100
            
            metrics_by_year.append(metrics)
        
        # CAGR計算
        first_year = metrics_by_year[0]
        last_year = metrics_by_year[-1]
        years_span = last_year["year"] - first_year["year"]
        
        growth_metrics = {}
        if years_span > 0:
            for metric in ["net_sales", "profit", "eps"]:
                first_value = first_year.get(metric)
                last_value = last_year.get(metric)
                
                if (first_value is not None and last_value is not None and 
                    first_value > 0 and last_value > 0):
                    cagr = ((last_value / first_value) ** (1/years_span) - 1) * 100
                    growth_metrics[f"{metric}_cagr"] = round(cagr, 2)
        
        # 最新年の成長率計算
        if len(metrics_by_year) >= 2:
            latest = metrics_by_year[-1]
            previous = metrics_by_year[-2]
            
            for metric in ["net_sales", "profit"]:
                current_value = latest.get(metric)
                previous_value = previous.get(metric)
                
                if (current_value is not None and previous_value is not None and 
                    previous_value != 0):
                    growth_rate = ((current_value - previous_value) / previous_value) * 100
                    growth_metrics[f"latest_{metric}_growth"] = round(growth_rate, 2)
        
        # 成長トレンド分析
        growth_trend = {}
        
        # 売上トレンド
        revenue_values = [m.get("net_sales") for m in metrics_by_year if m.get("net_sales")]
        if len(revenue_values) >= 3:
            recent_growth = revenue_values[-1] / revenue_values[-2] - 1 if revenue_values[-2] > 0 else 0
            past_growth = revenue_values[-2] / revenue_values[-3] - 1 if revenue_values[-3] > 0 else 0
            
            if recent_growth > past_growth * 1.1:
                growth_trend["revenue_trend"] = "加速"
            elif recent_growth < past_growth * 0.9:
                growth_trend["revenue_trend"] = "減速"
            else:
                growth_trend["revenue_trend"] = "安定"
        
        # 利益トレンド
        profit_values = [m.get("profit") for m in metrics_by_year if m.get("profit")]
        if len(profit_values) >= 3:
            recent_profit_growth = profit_values[-1] / profit_values[-2] - 1 if profit_values[-2] > 0 else 0
            past_profit_growth = profit_values[-2] / profit_values[-3] - 1 if profit_values[-3] > 0 else 0
            
            if recent_profit_growth > past_profit_growth * 1.1:
                growth_trend["profit_trend"] = "加速"
            elif recent_profit_growth < past_profit_growth * 0.9:
                growth_trend["profit_trend"] = "減速"
            else:
                growth_trend["profit_trend"] = "安定"
        
        # ROEトレンド
        roe_values = [m.get("roe") for m in metrics_by_year if m.get("roe")]
        if len(roe_values) >= 2:
            roe_improving = roe_values[-1] > roe_values[-2]
            growth_trend["roe_trend"] = "改善" if roe_improving else "悪化"
        
        # 成長の一貫性評価
        consistent_growth = 0
        total_comparisons = 0
        
        for metric in ["net_sales", "profit"]:
            values = [m.get(metric) for m in metrics_by_year if m.get(metric)]
            if len(values) >= 2:
                for i in range(1, len(values)):
                    total_comparisons += 1
                    if values[i] > values[i-1]:
                        consistent_growth += 1
        
        if total_comparisons > 0:
            consistency_rate = consistent_growth / total_comparisons
            if consistency_rate >= 0.8:
                growth_trend["consistency"] = "高い一貫性"
            elif consistency_rate >= 0.6:
                growth_trend["consistency"] = "中程度の一貫性"
            else:
                growth_trend["consistency"] = "不安定"
        
        # 成長の質分析
        growth_quality = {}
        
        # 利益率改善傾向
        margin_values = [m.get("operating_margin") for m in metrics_by_year if m.get("operating_margin")]
        if len(margin_values) >= 2:
            margin_improving = margin_values[-1] > margin_values[0]
            growth_quality["profitability_trend"] = "改善" if margin_improving else "悪化"
        
        # ROA改善傾向
        roa_values = []
        for m in metrics_by_year:
            if m.get("profit") and m.get("total_assets") and m.get("total_assets") > 0:
                roa_values.append((m["profit"] / m["total_assets"]) * 100)
        
        if len(roa_values) >= 2:
            roa_improving = roa_values[-1] > roa_values[0]
            growth_quality["efficiency_trend"] = "改善" if roa_improving else "悪化"
        
        # 成長性スコア計算（100点満点）
        growth_score = 0
        
        # CAGR評価（40点満点）
        revenue_cagr = growth_metrics.get("net_sales_cagr", 0)
        profit_cagr = growth_metrics.get("profit_cagr", 0)
        
        if revenue_cagr > 15:
            growth_score += 20
        elif revenue_cagr > 10:
            growth_score += 15
        elif revenue_cagr > 5:
            growth_score += 10
        
        if profit_cagr > 20:
            growth_score += 20
        elif profit_cagr > 15:
            growth_score += 15
        elif profit_cagr > 10:
            growth_score += 10
        
        # 一貫性評価（20点満点）
        if growth_trend.get("consistency") == "高い一貫性":
            growth_score += 20
        elif growth_trend.get("consistency") == "中程度の一貫性":
            growth_score += 12
        
        # 質的改善評価（20点満点）
        if growth_quality.get("profitability_trend") == "改善":
            growth_score += 10
        if growth_quality.get("efficiency_trend") == "改善":
            growth_score += 10
        
        # トレンド評価（20点満点）
        if growth_trend.get("revenue_trend") == "加速":
            growth_score += 10
        if growth_trend.get("profit_trend") == "加速":
            growth_score += 10
        
        # 成長性レーティング
        if growth_score >= 80:
            growth_rating = "高成長企業"
        elif growth_score >= 60:
            growth_rating = "成長企業"
        elif growth_score >= 40:
            growth_rating = "安定成長"
        else:
            growth_rating = "成長鈍化"
        
        # 将来見通し
        future_outlook = {}
        
        # 成長持続性
        if revenue_cagr > 10 and growth_trend.get("consistency") == "高い一貫性":
            future_outlook["growth_sustainability"] = "高い"
        elif revenue_cagr > 5:
            future_outlook["growth_sustainability"] = "中程度"
        else:
            future_outlook["growth_sustainability"] = "低い"
        
        # 成長加速可能性
        if (growth_trend.get("revenue_trend") == "加速" and 
            growth_quality.get("profitability_trend") == "改善"):
            future_outlook["acceleration_potential"] = "高い"
        else:
            future_outlook["acceleration_potential"] = "限定的"
        
        # 投資タイミング評価
        if (growth_score >= 70 and 
            growth_trend.get("revenue_trend") == "加速"):
            investment_timing = "絶好のタイミング"
        elif growth_score >= 60:
            investment_timing = "良いタイミング"
        elif growth_score >= 40:
            investment_timing = "慎重に検討"
        else:
            investment_timing = "見送り推奨"
        
        # 成長推進要因
        growth_catalysts = []
        if revenue_cagr > 15:
            growth_catalysts.append("高い売上成長率")
        if profit_cagr > revenue_cagr:
            growth_catalysts.append("利益成長率が売上を上回る")
        if growth_quality.get("profitability_trend") == "改善":
            growth_catalysts.append("収益性継続改善")
        
        # 成長リスク
        growth_risks = []
        if growth_trend.get("consistency") == "不安定":
            growth_risks.append("成長の不安定性")
        if growth_trend.get("profit_trend") == "減速":
            growth_risks.append("利益成長の減速傾向")
        if growth_quality.get("profitability_trend") == "悪化":
            growth_risks.append("収益性悪化傾向")
        
        return {
            "code": code,
            "analysis_period": f"{yearly_data[0]['year']}-{yearly_data[-1]['year']}",
            "quarter": quarter,
            "normalized_quarter": normalized_quarter,
            "data_consistency": f"全て{normalized_quarter or quarter}データで比較",
            "growth_metrics": growth_metrics,
            "growth_trend": growth_trend,
            "growth_quality": growth_quality,
            "future_outlook": future_outlook,
            "growth_score": {
                "total_score": growth_score,
                "max_score": 100,
                "growth_rating": growth_rating
            },
            "investment_timing": investment_timing,
            "growth_catalysts": growth_catalysts,
            "growth_risks": growth_risks,
            "yearly_data": metrics_by_year
        }
        
    except Exception as e:
        return {
            "error": f"成長性分析エラー: {str(e)}",
            "code": code,
            "quarter": quarter,
            "normalized_quarter": normalize_period(quarter)
        }




# テスト用のヘルパー関数（LangChainツールラッパーを回避）
async def test_valuation_analysis(code: str, quarter: Optional[str] = None, year: Optional[int] = None) -> Dict[str, Any]:
    """割安性分析の実装を直接呼び出す（テスト用）"""
    # @toolデコレータの有無に関係なく動作するように修正
    if hasattr(analyze_stock_valuation_tool, 'func') and analyze_stock_valuation_tool.func is not None:
        # LangChainツールオブジェクトの場合
        return await analyze_stock_valuation_tool.func(code=code, quarter=quarter, year=year)
    else:
        # 普通の関数の場合
        return await analyze_stock_valuation_tool(code=code, quarter=quarter, year=year)

async def test_growth_analysis(code: str, analysis_years: int = 3, quarter: Optional[str] = "Annual") -> Dict[str, Any]:
    """成長性分析の実装を直接呼び出す（テスト用）"""
    # @toolデコレータの有無に関係なく動作するように修正
    if hasattr(analyze_growth_potential_tool, 'func') and analyze_growth_potential_tool.func is not None:
        # LangChainツールオブジェクトの場合
        return await analyze_growth_potential_tool.func(code=code, analysis_years=analysis_years, quarter=quarter)
    else:
        # 普通の関数の場合
        return await analyze_growth_potential_tool(code=code, analysis_years=analysis_years, quarter=quarter)


async def main():
    """
    メイン関数 - 実際の銘柄コードを使用してツールをテスト
    @tool デコレータをコメントアウトして直接関数を呼び出す
    """
    import json
    import logging
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    
    print("=" * 80)
    print("📊 株式分析ツール テスト実行")
    print("=" * 80)
    
    # テスト対象の銘柄コード（日本の大手企業）
    test_companies = [
        {"code": "7203", "name": "トヨタ自動車"},
        {"code": "6758", "name": "ソニーグループ"},
        {"code": "9984", "name": "ソフトバンクグループ"},
    ]
    
    for company in test_companies:
        code = company["code"]
        name = company["name"]
        
        print(f"\n🏢 テスト企業: {name} ({code})")
        print("-" * 60)
        
        try:
            # 1. 割安性分析のテスト
            print("📈 割安性分析実行中...")
            valuation_result = await test_valuation_analysis(
                code=code,
                quarter="Annual",
                year=2024
            )
            
            if "error" in valuation_result:
                print(f"❌ 割安性分析エラー: {valuation_result['error']}")
            else:
                print("✅ 割安性分析結果:")
                print(f"  分析対象: {valuation_result.get('analysis_target')}")
                print(f"  株価: ¥{valuation_result.get('stock_price'):,}")
                
                if 'fundamental_metrics' in valuation_result:
                    metrics = valuation_result['fundamental_metrics']
                    print("  📊 財務指標:")
                    print(f"    PER: {metrics.get('per')}")
                    print(f"    PBR: {metrics.get('pbr')}")
                    print(f"    ROE: {metrics.get('roe_percentage')}%")
                    print(f"    営業利益率: {metrics.get('operating_margin_percentage')}%")
                    print(f"    自己資本比率: {metrics.get('equity_ratio_percentage')}%")
                
                if 'investment_score' in valuation_result:
                    score = valuation_result['investment_score']
                    print(f"  💎 投資魅力度: {score.get('total_score')}/100 ({score.get('overall_rating')})")
                
                if 'investment_recommendation' in valuation_result:
                    print(f"  📝 投資推奨: {valuation_result['investment_recommendation']}")
            
            print()
            
            # 2. 成長性分析のテスト
            print("📊 成長性分析実行中...")
            growth_result = await test_growth_analysis(
                code=code,
                analysis_years=3,
                quarter="Annual"
            )
            
            if "error" in growth_result:
                print(f"❌ 成長性分析エラー: {growth_result['error']}")
            else:
                print("✅ 成長性分析結果:")
                print(f"  分析期間: {growth_result.get('analysis_period')}")
                
                if 'growth_metrics' in growth_result:
                    metrics = growth_result['growth_metrics']
                    print("  📈 成長指標:")
                    print(f"    売上CAGR: {metrics.get('net_sales_cagr')}%")
                    print(f"    利益CAGR: {metrics.get('profit_cagr')}%")
                    print(f"    EPS CAGR: {metrics.get('eps_cagr')}%")
                
                if 'growth_score' in growth_result:
                    score = growth_result['growth_score']
                    print(f"  🚀 成長スコア: {score.get('total_score')}/100 ({score.get('growth_rating')})")
                
                if 'investment_timing' in growth_result:
                    print(f"  ⏰ 投資タイミング: {growth_result['investment_timing']}")
            
            # 詳細結果をJSONファイルに出力
            output_data = {
                "company": {"code": code, "name": name},
                "valuation_analysis": valuation_result,
                "growth_analysis": growth_result,
                "test_timestamp": datetime.now().isoformat()
            }
            
            filename = f"test_result_{code}_{name}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"📁 詳細結果を {filename} に保存しました")
            
        except Exception as e:
            logger.error(f"テスト実行エラー ({code}): {str(e)}")
            print(f"❌ テスト実行エラー: {str(e)}")
        
        print("-" * 60)
        
        # API制限を考慮して少し待機
        print("⏳ API制限回避のため5秒待機...")
        await asyncio.sleep(5)
    
    print("\n" + "=" * 80)
    print("🎉 全テスト完了!")
    print("=" * 80)


def test_normalize_period():
    """normalize_period関数の簡単テスト"""
    print("\n🔧 normalize_period関数テスト:")
    test_cases = [
        "Annual", "4Q", "Q4", "FY", "1Q", "2Q", "3Q", None, "invalid"
    ]
    
    for case in test_cases:
        result = normalize_period(case)
        print(f"  '{case}' -> '{result}'")


if __name__ == "__main__":
    print("🔧 関数レベルテスト実行:")
    test_normalize_period()
    
    print("\n" + "=" * 80)
    print("📊 実際のAPI呼び出しテストを開始しますか？")
    print("注意: J-Quants APIキーが必要です")
    print("=" * 80)
    
    import sys
    response = input("実行しますか？ (y/N): ")
    if response.lower() in ['y', 'yes']:
        asyncio.run(main())
    else:
        print("テスト終了")
        sys.exit(0)
