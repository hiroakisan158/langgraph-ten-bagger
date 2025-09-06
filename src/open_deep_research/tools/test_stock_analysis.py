"""
株式分析ツールのテストケース
"""
import pytest
import asyncio
import logging
from unittest.mock import Mock, patch
from open_deep_research.tools.stock_analysis_tool import (
    analyze_stock_valuation_tool,
    analyze_growth_potential_tool,
    safe_float_conversion,
    get_latest_financial_data,
    get_quarterly_financial_data,
    calculate_investment_attractiveness_score,
    normalize_period,
)

# ログ設定を詳細に
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class TestStockAnalysisTools:
    """株式分析ツールのテストクラス"""
    
    def test_safe_float_conversion(self):
        """safe_float_conversion関数のテスト"""
        logger.info("=" * 60)
        logger.info("Testing safe_float_conversion function")
        logger.info("=" * 60)
        
        test_cases = [
            ("123.45", 123.45, "文字列の小数"),
            (123.45, 123.45, "浮動小数点数"),
            (123, 123.0, "整数"),
            (0, 0.0, "ゼロ"),
            (0.0, 0.0, "浮動小数点ゼロ"),
            ("", None, "空文字列"),
            (None, None, "None値"),
            ("abc", None, "無効文字列"),
        ]
        
        for input_val, expected, description in test_cases:
            result = safe_float_conversion(input_val)
            logger.info(f"  {description}: {input_val} -> {result} (期待値: {expected})")
            assert result == expected, f"Failed for {input_val}: got {result}, expected {expected}"
        
        logger.info("✅ safe_float_conversion test completed successfully")
    
    def test_get_latest_financial_data(self):
        """get_latest_financial_data関数のテスト"""
        logger.info("=" * 60)
        logger.info("Testing get_latest_financial_data function")
        logger.info("=" * 60)
        
        # 正常ケース
        financial_data = {
            "statements": [
                {"DisclosedDate": "2024-01-01", "NetSales": 1000},
                {"DisclosedDate": "2024-06-01", "NetSales": 1200},
                {"DisclosedDate": "2024-03-01", "NetSales": 1100}
            ]
        }
        logger.info(f"入力データ: {len(financial_data['statements'])} statements")
        for i, stmt in enumerate(financial_data['statements']):
            logger.info(f"  Statement {i+1}: {stmt['DisclosedDate']}, NetSales: {stmt['NetSales']}")
        
        result = get_latest_financial_data(financial_data)
        logger.info(f"最新データ: {result}")
        assert result["DisclosedDate"] == "2024-06-01", f"Expected 2024-06-01, got {result['DisclosedDate']}"
        assert result["NetSales"] == 1200, f"Expected 1200, got {result['NetSales']}"
        
        # データなしケース
        logger.info("Testing edge cases...")
        result_empty = get_latest_financial_data({})
        logger.info(f"空データ結果: {result_empty}")
        assert result_empty is None
        
        result_no_statements = get_latest_financial_data({"statements": []})
        logger.info(f"空statements結果: {result_no_statements}")
        assert result_no_statements is None
        
        logger.info("✅ get_latest_financial_data test completed successfully")
    
    def test_get_quarterly_financial_data(self):
        """get_quarterly_financial_data関数のテスト"""
        financial_data = {
            "statements": [
                {
                    "DisclosedDate": "2024-01-01",
                    "TypeOfCurrentPeriod": "1Q",
                    "CurrentFiscalYearStartDate": "2023-04-01",
                    "CurrentFiscalYearEndDate": "2024-03-31",
                    "NetSales": 1000
                },
                {
                    "DisclosedDate": "2024-06-01", 
                    "TypeOfCurrentPeriod": "2Q",
                    "CurrentFiscalYearStartDate": "2023-04-01",
                    "CurrentFiscalYearEndDate": "2024-03-31",
                    "NetSales": 1200
                },
                {
                    "DisclosedDate": "2024-03-01",
                    "TypeOfCurrentPeriod": "1Q", 
                    "CurrentFiscalYearStartDate": "2024-04-01",
                    "CurrentFiscalYearEndDate": "2025-03-31",
                    "NetSales": 1100
                }
            ]
        }
        
        # 1Q指定
        result = get_quarterly_financial_data(financial_data, quarter="1Q")
        logger.info(f"Latest 1Q: {result}")
        assert result["DisclosedDate"] == "2024-03-01"  # 最新の1Q
        
        # 2024年度指定（期首が2024年開始のFY）
        result = get_quarterly_financial_data(financial_data, year=2024)
        logger.info(f"FY 2024 latest: {result}")
        assert result["DisclosedDate"] == "2024-06-01"  # 2024年度の最新

    def test_get_quarterly_financial_data_non_march_year_end(self):
        """3月決算以外（12月決算など）でも年度フィルタが機能するかを検証"""
        financial_data = {
            "statements": [
                {
                    "DisclosedDate": "2023-12-31",
                    "TypeOfCurrentPeriod": "FY",
                    "CurrentFiscalYearStartDate": "2023-01-01",
                    "CurrentFiscalYearEndDate": "2023-12-31",
                    "NetSales": 100
                },
                {
                    "DisclosedDate": "2024-12-31",
                    "TypeOfCurrentPeriod": "FY",
                    "CurrentFiscalYearStartDate": "2024-01-01",
                    "CurrentFiscalYearEndDate": "2024-12-31",
                    "NetSales": 120
                },
                {
                    # 2024年開始の別四半期（2Q）
                    "DisclosedDate": "2024-06-30",
                    "TypeOfCurrentPeriod": "2Q",
                    "CurrentFiscalYearStartDate": "2024-01-01",
                    "CurrentFiscalYearEndDate": "2024-12-31",
                    "NetSales": 60
                },
            ]
        }
        # 2024年度のFYを取得できること
        result_2024 = get_quarterly_financial_data(financial_data, quarter="FY", year=2024)
        assert result_2024 is not None
        assert result_2024["DisclosedDate"] == "2024-12-31"
        # 四半期指定なしで年指定のみ → 最新FYを返す（年の範囲内）
        result_2023 = get_quarterly_financial_data(financial_data, year=2023)
        assert result_2023 is not None
        assert result_2023["DisclosedDate"] == "2023-12-31"

    def test_normalize_period(self):
        """四半期指定の正規化を確認"""
        logger.info("=" * 60)
        logger.info("Testing normalize_period function")
        logger.info("=" * 60)
        
        test_cases = [
            (None, None, "None値"),
            ("Annual", "FY", "Annual -> FY"),
            ("annual", "FY", "annual (小文字) -> FY"),
            ("4Q", "FY", "4Q -> FY"),
            ("4q", "FY", "4q (小文字) -> FY"),
            ("Q4", "FY", "Q4 -> FY"),
            ("FY", "FY", "FY -> FY (変更なし)"),
            ("1Q", "1Q", "1Q -> 1Q (変更なし)"),
            ("2Q", "2Q", "2Q -> 2Q (変更なし)"),
            ("3Q", "3Q", "3Q -> 3Q (変更なし)"),
        ]
        
        for input_val, expected, description in test_cases:
            result = normalize_period(input_val)
            logger.info(f"  {description}: '{input_val}' -> '{result}' (期待値: '{expected}')")
            assert result == expected, f"Failed for {input_val}: got {result}, expected {expected}"
        
        logger.info("✅ normalize_period test completed successfully")
    
    def test_calculate_investment_attractiveness_score(self):
        """calculate_investment_attractiveness_score関数のテスト"""
        logger.info("=" * 60)
        logger.info("Testing calculate_investment_attractiveness_score function")
        logger.info("=" * 60)
        
        # 高スコアケース
        logger.info("🔹 Testing high score case")
        ratios = {
            "per": 8,  # 25点
            "pbr": 0.8,  # 20点
            "roe_percentage": 25,  # 25点
            "equity_ratio_percentage": 60,  # 15点
            "operating_margin_percentage": 20  # 15点
        }
        financials = {}
        
        logger.info(f"入力ratios: {ratios}")
        result = calculate_investment_attractiveness_score(ratios, financials)
        logger.info(f"高スコア結果:")
        logger.info(f"  総合スコア: {result['total_score']}/100")
        logger.info(f"  総合レーティング: {result['overall_rating']}")
        logger.info(f"  詳細スコア: {result['score_details']}")
        
        assert result["total_score"] == 100, f"Expected 100, got {result['total_score']}"
        assert result["overall_rating"] == "投資魅力度：非常に高い"
        
        logger.info("✅ High score test passed")
        
        # 低スコアケース
        logger.info("🔹 Testing low score case")
        low_ratios = {
            "per": 35,  # 0点
            "pbr": 4,  # 0点
            "roe_percentage": 5,  # 0点
            "equity_ratio_percentage": 20,  # 5点
            "operating_margin_percentage": 3  # 5点
        }
        
        logger.info(f"入力ratios: {low_ratios}")
        result = calculate_investment_attractiveness_score(low_ratios, financials)
        logger.info(f"低スコア結果:")
        logger.info(f"  総合スコア: {result['total_score']}/100")
        logger.info(f"  総合レーティング: {result['overall_rating']}")
        logger.info(f"  詳細スコア: {result['score_details']}")
        
        assert result["total_score"] == 10, f"Expected 10, got {result['total_score']}"
        assert result["overall_rating"] == "投資魅力度：低い"
        
        logger.info("✅ Low score test passed")
        logger.info("✅ calculate_investment_attractiveness_score test completed successfully")


class TestStockValuationTool:
    """株式割安性分析ツールのテスト"""
    
    @pytest.mark.asyncio
    @patch('open_deep_research.tools.stock_analysis_tool.JQuantsAPI')
    async def test_analyze_stock_valuation_tool_success(self, mock_api_class):
        """割安性分析ツールの正常ケーステスト"""
        logger.info("=" * 80)
        logger.info("🔥 Testing analyze_stock_valuation_tool - SUCCESS CASE")
        logger.info("=" * 80)
        
        # モックAPIの設定
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        # 財務データのモック
        mock_financial_data = {
            "statements": [
                {
                    "DisclosedDate": "2024-06-01",
                    "TypeOfCurrentPeriod": "FY",
                    "CurrentPeriodStartDate": "2023-04-01",
                    "CurrentPeriodEndDate": "2024-03-31",
                    "CurrentFiscalYearStartDate": "2023-04-01",
                    "CurrentFiscalYearEndDate": "2024-03-31",
                    "NetSales": 100000000000,
                    "OperatingProfit": 15000000000,
                    "Profit": 10000000000,
                    "TotalAssets": 200000000000,
                    "Equity": 80000000000,
                    "EarningsPerShare": 100,
                    "BookValuePerShare": 800
                }
            ]
        }
        
        # 株価データのモック
        mock_stock_data = {
            "daily_quotes": [
                {"Date": "2024-03-31", "Close": 1200}
            ]
        }
        
        logger.info("📊 Mock data setup:")
        logger.info(f"  企業コード: 1234")
        logger.info(f"  売上高: ¥{mock_financial_data['statements'][0]['NetSales']:,}")
        logger.info(f"  営業利益: ¥{mock_financial_data['statements'][0]['OperatingProfit']:,}")
        logger.info(f"  純利益: ¥{mock_financial_data['statements'][0]['Profit']:,}")
        logger.info(f"  EPS: ¥{mock_financial_data['statements'][0]['EarningsPerShare']}")
        logger.info(f"  BPS: ¥{mock_financial_data['statements'][0]['BookValuePerShare']}")
        logger.info(f"  株価: ¥{mock_stock_data['daily_quotes'][0]['Close']}")
        
        mock_api.get_financial_statements.return_value = mock_financial_data
        mock_api.get_stock_price.return_value = mock_stock_data
        
        # テスト実行
        logger.info("📈 Executing analyze_stock_valuation_tool...")
        result = await analyze_stock_valuation_tool(code="7203", year=2024, quarter="Annual")
        
        logger.info("📊 Analysis Results:")
        logger.info(f"  企業コード: {result.get('code')}")
        logger.info(f"  分析対象: {result.get('analysis_target')}")
        logger.info(f"  株価: ¥{result.get('stock_price')}")
        
        if 'fundamental_metrics' in result:
            metrics = result['fundamental_metrics']
            logger.info("  財務指標:")
            logger.info(f"    PER: {metrics.get('per')}")
            logger.info(f"    PBR: {metrics.get('pbr')}")
            logger.info(f"    ROE: {metrics.get('roe_percentage')}%")
            logger.info(f"    ROA: {metrics.get('roa_percentage')}%")
            logger.info(f"    営業利益率: {metrics.get('operating_margin_percentage')}%")
            logger.info(f"    自己資本比率: {metrics.get('equity_ratio_percentage')}%")
        
        if 'investment_score' in result:
            score = result['investment_score']
            logger.info("  投資魅力度:")
            logger.info(f"    スコア: {score.get('total_score')}/100")
            logger.info(f"    レーティング: {score.get('overall_rating')}")
        
        # 結果検証
        assert result["code"] == "7203", f"Expected 7203, got {result['code']}"
        assert "fundamental_metrics" in result, "fundamental_metrics missing"
        assert "valuation_assessment" in result, "valuation_assessment missing"
        assert "investment_score" in result, "investment_score missing"
        
        # 計算結果の検証
        expected_per = 12.0  # 1200 / 100
        expected_pbr = 1.5   # 1200 / 800  
        expected_roe = 12.5  # (10B / 80B) * 100
        
        assert result["fundamental_metrics"]["per"] == expected_per, f"PER: expected {expected_per}, got {result['fundamental_metrics']['per']}"
        assert result["fundamental_metrics"]["pbr"] == expected_pbr, f"PBR: expected {expected_pbr}, got {result['fundamental_metrics']['pbr']}"
        assert result["fundamental_metrics"]["roe_percentage"] == expected_roe, f"ROE: expected {expected_roe}, got {result['fundamental_metrics']['roe_percentage']}"
        
        logger.info("✅ analyze_stock_valuation_tool success test completed")
    
    @pytest.mark.asyncio 
    @patch('open_deep_research.tools.stock_analysis_tool.JQuantsAPI')
    async def test_analyze_stock_valuation_tool_no_data(self, mock_api_class):
        """データなしケースのテスト"""
        logger.info("=" * 80)
        logger.info("🔥 Testing analyze_stock_valuation_tool - NO DATA CASE")
        logger.info("=" * 80)
        
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_api.get_financial_statements.return_value = None
        
        logger.info("📊 Testing with no financial data (code: 9999)")
        result = await analyze_stock_valuation_tool(code="9999")
        
        logger.info("📊 Error case result:")
        logger.info(f"  Error message: {result.get('error')}")
        logger.info(f"  Code: {result.get('code')}")
        
        assert "error" in result, "Error key missing in result"
        assert result["code"] == "9999", f"Expected 9999, got {result['code']}"
        logger.info("✅ No data error test completed")


class TestGrowthPotentialTool:
    """株式成長性分析ツールのテスト"""
    
    @pytest.mark.asyncio
    @patch('open_deep_research.tools.stock_analysis_tool.JQuantsAPI')
    async def test_analyze_growth_potential_tool_success(self, mock_api_class):
        """成長性分析ツールの正常ケーステスト"""
        logger.info("=" * 80)
        logger.info("🔥 Testing analyze_growth_potential_tool - SUCCESS CASE")
        logger.info("=" * 80)
        
        # モックAPIの設定
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        # 複数年の財務データを模擬
        def mock_get_financial_statements(code, year):
            financial_data_by_year = {
                2025: {
                    "statements": [
                        {
                            "DisclosedDate": "2025-06-01",
                            "TypeOfCurrentPeriod": "FY",
                            "CurrentFiscalYearStartDate": "2024-04-01",
                            "CurrentFiscalYearEndDate": "2025-03-31",
                            "NetSales": 120000000000,
                            "OperatingProfit": 20000000000,
                            "Profit": 15000000000,
                            "TotalAssets": 250000000000,
                            "Equity": 100000000000,
                            "EarningsPerShare": 150
                        }
                    ]
                },
                2024: {
                    "statements": [
                        {
                            "DisclosedDate": "2024-06-01",
                            "TypeOfCurrentPeriod": "FY",
                            "CurrentFiscalYearStartDate": "2023-04-01",
                            "CurrentFiscalYearEndDate": "2024-03-31",
                            "NetSales": 100000000000,
                            "OperatingProfit": 15000000000,
                            "Profit": 10000000000,
                            "TotalAssets": 200000000000,
                            "Equity": 80000000000,
                            "EarningsPerShare": 100
                        }
                    ]
                },
                2023: {
                    "statements": [
                        {
                            "DisclosedDate": "2023-06-01",
                            "TypeOfCurrentPeriod": "FY",
                            "CurrentFiscalYearStartDate": "2022-04-01",
                            "CurrentFiscalYearEndDate": "2023-03-31",
                            "NetSales": 90000000000,
                            "OperatingProfit": 12000000000,
                            "Profit": 8000000000,
                            "TotalAssets": 180000000000,
                            "Equity": 70000000000,
                            "EarningsPerShare": 80
                        }
                    ]
                }
            }
            return financial_data_by_year.get(year)
        
        mock_api.get_financial_statements.side_effect = mock_get_financial_statements
        
        logger.info("📊 Mock growth data setup:")
        logger.info("  2025年: 売上 ¥100B, 利益 ¥10B")
        logger.info("  2024年: 売上 ¥95B,  利益 ¥9B")
        logger.info("  2023年: 売上 ¥90B,  利益 ¥8B")
        
        # テスト実行
        logger.info("📈 Executing analyze_growth_potential_tool...")
        result = await analyze_growth_potential_tool(code="7203", analysis_years=3)
        
        logger.info("📊 Growth Analysis Results:")
        logger.info(f"  企業コード: {result.get('code')}")
        logger.info(f"  分析期間: {result.get('analysis_period')}")
        
        if 'growth_metrics' in result:
            metrics = result['growth_metrics']
            logger.info("  成長指標:")
            logger.info(f"    売上CAGR: {metrics.get('net_sales_cagr')}%")
            logger.info(f"    利益CAGR: {metrics.get('profit_cagr')}%")
            logger.info(f"    最新年売上成長率: {metrics.get('latest_net_sales_growth')}%")
            logger.info(f"    最新年利益成長率: {metrics.get('latest_profit_growth')}%")
        
        if 'growth_score' in result:
            score = result['growth_score']
            logger.info("  成長スコア:")
            logger.info(f"    スコア: {score.get('total_score')}/100")
            logger.info(f"    レーティング: {score.get('growth_rating')}")
        
        # 結果検証
        assert result["code"] == "7203", f"Expected 7203, got {result['code']}"
        assert "growth_metrics" in result, "growth_metrics missing"
        assert "growth_trend" in result, "growth_trend missing"
        assert "growth_score" in result, "growth_score missing"
        
        # CAGR計算の検証（2023-2025の2年間）
        assert "net_sales_cagr" in result["growth_metrics"], "net_sales_cagr missing"
        assert "profit_cagr" in result["growth_metrics"], "profit_cagr missing"
        
        # 成長スコアの検証
        assert result["growth_score"]["total_score"] > 0, f"Growth score should be > 0, got {result['growth_score']['total_score']}"
        
        logger.info("✅ analyze_growth_potential_tool success test completed")
        assert result["growth_score"]["max_score"] == 100
    
    @pytest.mark.asyncio
    @patch('open_deep_research.tools.stock_analysis_tool.JQuantsAPI')
    async def test_analyze_growth_potential_tool_insufficient_data(self, mock_api_class):
        """データ不足ケースのテスト"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_api.get_financial_statements.return_value = None
        
        result = await analyze_growth_potential_tool(code="9999")
        logger.info(f"Growth insufficient data result: {result}")
        
        assert "error" in result
        assert "最低2年分のデータが必要" in result["error"]


if __name__ == "__main__":
    # 簡単なテスト実行
    test_instance = TestStockAnalysisTools()
    test_instance.test_safe_float_conversion()
    test_instance.test_get_latest_financial_data()
    test_instance.test_calculate_investment_attractiveness_score()
    print("基本機能テスト完了")
    
    # 非同期テストの例
    async def run_async_tests():
        valuation_test = TestStockValuationTool()
        growth_test = TestGrowthPotentialTool()
        
        print("非同期テストはpytestで実行してください")
        print("コマンド: pytest src/open_deep_research/tools/test_stock_analysis.py -v")
    
    asyncio.run(run_async_tests())
