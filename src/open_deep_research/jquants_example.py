"""
J-Quants APIの使用例

このスクリプトは、J-Quants APIを使用して財務情報を取得する具体的な例を示します。
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jquants_api import JQuantsAPI


def analyze_company_financials(company_code: str, company_name: str):
    """企業の財務分析を実行"""
    print(f"\n{'='*50}")
    print(f"{company_name} ({company_code}) の財務分析")
    print(f"{'='*50}")
    
    try:
        api = JQuantsAPI()
        
        # 1. 企業基本情報
        print("\n1. 企業基本情報")
        print("-" * 30)
        company_info = api.get_company_info(company_code)
        print(f"企業名: {company_info.get('company_name', 'N/A')}")
        print(f"業種: {company_info.get('sector', 'N/A')}")
        print(f"市場: {company_info.get('market', 'N/A')}")
        
        # 2. 財務諸表（最新）
        print("\n2. 財務諸表（最新）")
        print("-" * 30)
        financial_data = api.get_financial_statements(company_code)
        
        if 'data' in financial_data and financial_data['data']:
            latest_financial = financial_data['data'][0]  # 最新のデータ
            print(f"決算期: {latest_financial.get('fiscal_year', 'N/A')}")
            print(f"売上高: {latest_financial.get('net_sales', 'N/A'):,} 円")
            print(f"営業利益: {latest_financial.get('operating_income', 'N/A'):,} 円")
            print(f"当期純利益: {latest_financial.get('net_income', 'N/A'):,} 円")
        else:
            print("財務データが取得できませんでした")
        
        # 3. 株価情報（過去1ヶ月）
        print("\n3. 株価情報（過去1ヶ月）")
        print("-" * 30)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        stock_data = api.get_stock_price(company_code, start_date, end_date)
        
        if 'data' in stock_data and stock_data['data']:
            stock_prices = stock_data['data']
            print(f"取得期間: {start_date} 〜 {end_date}")
            print(f"データ数: {len(stock_prices)} 件")
            
            if stock_prices:
                latest_price = stock_prices[0]
                oldest_price = stock_prices[-1]
                
                print(f"最新株価: {latest_price.get('close', 'N/A')} 円")
                print(f"1ヶ月前株価: {oldest_price.get('close', 'N/A')} 円")
                
                # 変化率を計算
                if latest_price.get('close') and oldest_price.get('close'):
                    change_rate = ((latest_price['close'] - oldest_price['close']) / oldest_price['close']) * 100
                    print(f"1ヶ月変化率: {change_rate:.2f}%")
        
        # 4. 業績予想
        print("\n4. 業績予想")
        print("-" * 30)
        forecast_data = api.get_earnings_forecast(company_code)
        
        if 'data' in forecast_data and forecast_data['data']:
            forecasts = forecast_data['data']
            print(f"予想データ数: {len(forecasts)} 件")
            
            for forecast in forecasts[:3]:  # 最新3件を表示
                print(f"決算期: {forecast.get('fiscal_year', 'N/A')}")
                print(f"予想売上高: {forecast.get('net_sales_forecast', 'N/A'):,} 円")
                print(f"予想営業利益: {forecast.get('operating_income_forecast', 'N/A'):,} 円")
                print(f"予想当期純利益: {forecast.get('net_income_forecast', 'N/A'):,} 円")
                print("---")
        else:
            print("業績予想データが取得できませんでした")
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")


def compare_companies(company_codes: list):
    """複数企業の比較分析"""
    print(f"\n{'='*60}")
    print("複数企業の比較分析")
    print(f"{'='*60}")
    
    try:
        api = JQuantsAPI()
        
        for code in company_codes:
            company_info = api.get_company_info(code)
            company_name = company_info.get('company_name', f'企業{code}')
            
            # 株価情報を取得（最新）
            stock_data = api.get_stock_price(code)
            
            if 'data' in stock_data and stock_data['data']:
                latest_price = stock_data['data'][0]
                print(f"{company_name} ({code}): {latest_price.get('close', 'N/A')} 円")
            else:
                print(f"{company_name} ({code}): データなし")
                
    except Exception as e:
        print(f"エラーが発生しました: {e}")


# 企業検索機能は Freeプランでは利用できない可能性があります
# def search_and_analyze(keyword: str):
#     """キーワードで企業を検索して分析"""
#     print(f"\n{'='*50}")
#     print(f"キーワード検索: '{keyword}'")
#     print(f"{'='*50}")
#     
#     try:
#         api = JQuantsAPI()
#         
#         # 企業検索（プラン制限あり）
#         search_results = api.search_companies(keyword)
#         
#         if 'data' in search_results and search_results['data']:
#             print(f"検索結果: {len(search_results['data'])} 件")
#             
#             for i, company in enumerate(search_results['data'][:5]):  # 上位5件を表示
#                 print(f"\n{i+1}. {company.get('company_name', 'N/A')} ({company.get('code', 'N/A')})")
#                 print(f"   業種: {company.get('sector', 'N/A')}")
#                 print(f"   市場: {company.get('market', 'N/A')}")
#                 
#                 # 最初の企業の詳細分析を実行
#                 if i == 0:
#                     company_code = company.get('code')
#                     if company_code:
#                         analyze_company_financials(company_code, company.get('company_name', 'N/A'))
#                         break
#         else:
#             print("検索結果が見つかりませんでした")
#             
#     except Exception as e:
#         print(f"エラーが発生しました: {e}")


def main():
    """メイン実行関数"""
    print("J-Quants API 財務情報取得サンプル")
    print("=" * 50)
    
    # 環境変数の確認
    if not os.getenv('JQUANTS_REFRESH_TOKEN'):
        print("エラー: JQUANTS_REFRESH_TOKENが設定されていません")
        print("以下の手順で設定してください:")
        print("1. .envファイルを作成")
        print("2. JQUANTS_REFRESH_TOKEN=your_token_here を追加")
        return
    
    try:
        # 1. 個別企業の詳細分析
        companies_to_analyze = [
            ("8697", "楽天"),
            ("7203", "トヨタ自動車"),
            ("6758", "ソニーグループ")
        ]
        
        for code, name in companies_to_analyze:
            analyze_company_financials(code, name)
        
        # 2. 複数企業の比較
        print("\n" + "="*60)
        compare_companies(["8697", "7203", "6758"])
        
        # 3. 取引カレンダー情報
        print("\n" + "="*60)
        print("取引カレンダー情報の取得")
        print("="*60)
        
        try:
            calendar_data = api.get_market_info()
            if 'trading_calendar' in calendar_data:
                print(f"✅ 取引カレンダー情報の取得に成功: {len(calendar_data['trading_calendar'])}件のデータ")
            else:
                print("⚠️ 取引カレンダー情報の取得に成功しましたが、期待されるデータ形式ではありません")
        except Exception as e:
            print(f"❌ 取引カレンダー情報の取得でエラー: {e}")
        
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
