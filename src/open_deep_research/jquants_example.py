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
        
        # デバッグ: 実際のレスポンス構造を確認
        print(f"DEBUG: 企業情報レスポンスのキー: {list(company_info.keys())}")
        if 'info' in company_info and company_info['info']:
            info = company_info['info'][0]  # 最初の結果を取得
            print(f"DEBUG: 企業情報のフィールド: {list(info.keys())}")
            # 実際のデータの一部を表示
            print(f"DEBUG: 最初の3つのフィールドの値:")
            for key in list(info.keys())[:3]:
                print(f"  {key}: {info[key]}")
            print(f"企業名: {info.get('company_name', info.get('CompanyName', 'N/A'))}")
            print(f"業種: {info.get('sector_name', info.get('SectorName', 'N/A'))}")
            print(f"市場: {info.get('market_name', info.get('MarketName', 'N/A'))}")
        else:
            print("企業基本情報が取得できませんでした")
        
        # 2. 財務諸表（最新）
        print("\n2. 財務諸表（最新）")
        print("-" * 30)
        financial_data = api.get_financial_statements(company_code)
        
        # デバッグ: 実際のレスポンス構造を確認
        print(f"DEBUG: 財務情報レスポンスのキー: {list(financial_data.keys())}")
        if 'statements' in financial_data and financial_data['statements']:
            latest_financial = financial_data['statements'][0]  # 最新のデータ
            print(f"DEBUG: 財務情報のフィールド: {list(latest_financial.keys())}")
            print(f"決算期: {latest_financial.get('fiscal_year', latest_financial.get('FiscalYear', 'N/A'))}")
            print(f"売上高: {latest_financial.get('net_sales', latest_financial.get('NetSales', 'N/A'))} 円")
            print(f"営業利益: {latest_financial.get('operating_income', latest_financial.get('OperatingIncome', 'N/A'))} 円")
            print(f"当期純利益: {latest_financial.get('net_income', latest_financial.get('NetIncome', 'N/A'))} 円")
        else:
            print("財務データが取得できませんでした")
        
        # 3. 株価情報（最新データ）
        print("\n3. 株価情報（最新データ）")
        print("-" * 30)
        # 企業コードを指定して最新データを取得
        try:
            stock_data = api.get_stock_price(code=company_code)
            
            # デバッグ: 実際のレスポンス構造を確認
            print(f"DEBUG: 株価情報レスポンスのキー: {list(stock_data.keys())}")
            if 'daily_quotes' in stock_data and stock_data['daily_quotes']:
                stock_prices = stock_data['daily_quotes']
                print(f"最新株価データ数: {len(stock_prices)} 件")
                
                if stock_prices:
                    latest_price = stock_prices[0]
                    print(f"DEBUG: 株価情報のフィールド: {list(latest_price.keys())}")
                    print(f"最新株価: {latest_price.get('Close', latest_price.get('close', 'N/A'))} 円")
                    print(f"取引日: {latest_price.get('Date', latest_price.get('date', 'N/A'))}")
                    print(f"始値: {latest_price.get('Open', latest_price.get('open', 'N/A'))} 円")
                    print(f"高値: {latest_price.get('High', latest_price.get('high', 'N/A'))} 円")
                    print(f"安値: {latest_price.get('Low', latest_price.get('low', 'N/A'))} 円")
                    
                    # データが複数ある場合、変化率を計算
                    if len(stock_prices) > 1:
                        older_price = stock_prices[-1]
                        try:
                            latest_close = float(latest_price.get('Close', latest_price.get('close', 0)))
                            older_close = float(older_price.get('Close', older_price.get('close', 0)))
                            if latest_close > 0 and older_close > 0:
                                change_rate = ((latest_close - older_close) / older_close) * 100
                                print(f"変化率: {change_rate:.2f}%")
                        except (ValueError, TypeError):
                            print("変化率の計算ができませんでした")
            else:
                print("株価データが取得できませんでした")
        except Exception as e:
            print(f"株価データ取得エラー: {e}")
            # 日付なしでも失敗した場合は、データがない可能性がある
            print("※ この銘柄の株価データが利用できない可能性があります")
        
        # 4. 決算発表予定日
        print("\n4. 決算発表予定日")
        print("-" * 30)
        forecast_data = api.get_earnings_forecast(company_code)
        
        # デバッグ: 実際のレスポンス構造を確認
        print(f"DEBUG: 決算情報レスポンスのキー: {list(forecast_data.keys())}")
        if 'announcement' in forecast_data and forecast_data['announcement']:
            announcements = forecast_data['announcement']
            print(f"発表予定データ数: {len(announcements)} 件")
            
            if announcements:
                announcement = announcements[0]
                print(f"DEBUG: 決算情報のフィールド: {list(announcement.keys())}")
            
            for announcement in announcements[:3]:  # 最新3件を表示
                print(f"銘柄コード: {announcement.get('Code', announcement.get('code', 'N/A'))}")
                print(f"発表予定日: {announcement.get('Date', announcement.get('date', 'N/A'))}")
                print(f"決算期: {announcement.get('FiscalYear', announcement.get('fiscal_year', 'N/A'))}")
                print("---")
        else:
            print("決算発表予定日データが取得できませんでした")
            
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
            
            # 企業名を取得
            if 'info' in company_info and company_info['info']:
                company_name = company_info['info'][0].get('company_name', f'企業{code}')
            else:
                company_name = f'企業{code}'
            
            # 株価情報を取得（最新）
            try:
                stock_data = api.get_stock_price(code=code)
                
                if 'daily_quotes' in stock_data and stock_data['daily_quotes']:
                    latest_price = stock_data['daily_quotes'][0]
                    print(f"{company_name} ({code}): {latest_price.get('close', 'N/A')} 円")
                else:
                    print(f"{company_name} ({code}): データなし")
            except Exception as e:
                print(f"{company_name} ({code}): 取得エラー - {e}")
                
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
            api = JQuantsAPI()
            calendar_data = api.get_market_info()
            if 'trading_calendar' in calendar_data:
                calendar_entries = calendar_data['trading_calendar']
                print(f"✅ 取引カレンダー情報の取得に成功: {len(calendar_entries)}件のデータ")
                
                # 最新の数件を表示
                for entry in calendar_entries[:5]:
                    date = entry.get('date', 'N/A')
                    holiday_division = entry.get('holiday_division', 'N/A')
                    print(f"  {date}: {holiday_division}")
            else:
                print("⚠️ 取引カレンダー情報の取得に成功しましたが、期待されるデータ形式ではありません")
        except Exception as e:
            print(f"❌ 取引カレンダー情報の取得でエラー: {e}")
        
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
