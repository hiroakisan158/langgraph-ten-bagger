"""
J-Quants APIの動作確認用テストスクリプト

このスクリプトは、J-Quants APIが正しく動作するかを確認するために使用します。
環境変数が正しく設定されているか、API接続が可能かをチェックします。
"""

import os
import sys
from dotenv import load_dotenv

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_environment():
    """環境変数の設定をテスト"""
    print("=== 環境変数テスト ===")
    
    # .envファイルの読み込み
    load_dotenv()
    
    # 必要な環境変数の確認
    required_vars = {
        'JQUANTS_REFRESH_TOKEN': 'リフレッシュトークン',
        'JQUANTS_API_BASE_URL': 'APIベースURL'
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {description}: {var} = {value[:20]}{'...' if len(value) > 20 else ''}")
        else:
            print(f"✗ {description}: {var} が設定されていません")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ 以下の環境変数が設定されていません: {', '.join(missing_vars)}")
        print("   .envファイルを作成して設定してください")
        return False
    else:
        print("\n✅ すべての環境変数が正しく設定されています")
        return True


def test_api_connection():
    """API接続をテスト"""
    print("\n=== API接続テスト ===")
    
    try:
        from jquants_api import JQuantsAPI
        
        print("J-Quants APIクライアントを初期化中...")
        api = JQuantsAPI()
        print("✅ APIクライアントの初期化が完了しました")
        
        # 簡単なAPI呼び出しをテスト
        print("企業情報の取得をテスト中...")
        test_company_code = "8697"  # 楽天
        
        company_info = api.get_company_info(test_company_code)
        if company_info and 'company_name' in company_info:
            print(f"✅ 企業情報の取得に成功: {company_info['company_name']}")
        else:
            print("⚠️ 企業情報の取得に成功しましたが、期待されるデータ形式ではありません")
        
        return True
        
    except ImportError as e:
        print(f"❌ モジュールのインポートに失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ API接続テストに失敗: {e}")
        # より詳細なエラー情報を表示
        if hasattr(e, '__cause__') and e.__cause__:
            print(f"   詳細: {e.__cause__}")
        return False


def test_basic_functionality():
    """基本的な機能をテスト"""
    print("\n=== 基本機能テスト ===")
    
    try:
        from jquants_api import JQuantsAPI
        
        api = JQuantsAPI()
        
        # 1. 企業情報取得（楽天: 8697）
        print("1. 企業情報取得機能をテスト中...")
        company_info = api.get_company_info("8697")
        if company_info and 'info' in company_info:
            companies = company_info['info']
            if companies:
                print(f"✅ 企業情報の取得に成功: {companies[0].get('company_name', 'N/A')}")
            else:
                print("⚠️ 企業情報の取得に成功しましたが、データが空です")
        else:
            print("⚠️ 企業情報の取得に成功しましたが、期待されるデータ形式ではありません")
        
        # 2. 財務諸表
        print("2. 財務諸表取得機能をテスト中...")
        financial_data = api.get_financial_statements("8697")
        if financial_data and 'statements' in financial_data:
            print(f"✅ 財務諸表の取得に成功: {len(financial_data['statements'])}件のデータ")
        else:
            print("⚠️ 財務諸表の取得に成功しましたが、期待されるデータ形式ではありません")
        
        # 3. 株価情報
        print("3. 株価情報取得機能をテスト中...")
        stock_data = api.get_stock_price("8697")
        if stock_data and 'daily_quotes' in stock_data:
            print(f"✅ 株価情報の取得に成功: {len(stock_data['daily_quotes'])}件のデータ")
        else:
            print("⚠️ 株価情報の取得に成功しましたが、期待されるデータ形式ではありません")
        
        return True
        
    except Exception as e:
        print(f"❌ 基本機能テストに失敗: {e}")
        return False


def main():
    """メインテスト実行関数"""
    print("J-Quants API 動作確認テスト")
    print("=" * 50)
    
    # 1. 環境変数テスト
    env_ok = test_environment()
    
    if not env_ok:
        print("\n❌ 環境変数の設定に問題があります。先に設定を完了してください。")
        return
    
    # 2. API接続テスト
    connection_ok = test_api_connection()
    
    if not connection_ok:
        print("\n❌ API接続に問題があります。設定を確認してください。")
        return
    
    # 3. 基本機能テスト
    functionality_ok = test_basic_functionality()
    
    if functionality_ok:
        print("\n🎉 すべてのテストが完了しました！")
        print("J-Quants APIが正常に動作しています。")
    else:
        print("\n⚠️ 一部の機能に問題があります。詳細を確認してください。")


if __name__ == "__main__":
    main()
