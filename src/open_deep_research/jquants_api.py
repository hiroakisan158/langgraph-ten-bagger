"""
J-Quants APIを使用して財務情報を取得するモジュール

このモジュールは、J-Quants APIを使用して以下の情報を取得できます：
- 企業の財務情報
- 株価情報
- 財務諸表
- 業績予想
"""

import os
import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数を読み込み
load_dotenv()


class JQuantsAPI:
    """J-Quants APIクライアントクラス"""
    
    def __init__(self):
        """J-Quants APIクライアントを初期化"""
        self.base_url = os.getenv('JQUANTS_API_BASE_URL', 'https://api.jquants.com')
        self.refresh_token = os.getenv('JQUANTS_REFRESH_TOKEN')
        self.rate_limit_delay = float(os.getenv('JQUANTS_RATE_LIMIT_DELAY', '1.0'))
        
        if not self.refresh_token:
            raise ValueError("JQUANTS_REFRESH_TOKENが設定されていません。.envファイルを確認してください。")
        
        self.id_token = None
        self.session = requests.Session()
        
        # トークンを取得
        self._authenticate()
    
    def _authenticate(self) -> None:
        """認証を行い、IDトークンを取得"""
        try:
            # デバッグ用: リフレッシュトークンの確認
            if self.refresh_token and len(self.refresh_token) > 10:
                logger.info(f"リフレッシュトークン（最初の10文字）: {self.refresh_token[:10]}...")
            else:
                logger.error("リフレッシュトークンが空または短すぎます")
                raise ValueError("有効なリフレッシュトークンが設定されていません")
            
            # リフレッシュトークンを使用してIDトークンを取得
            url = f"{self.base_url}/v1/token/auth_refresh?refreshtoken={self.refresh_token}"
            logger.info("IDトークン取得リクエストを送信中...")
            
            # まずPOSTを試行
            refresh_response = self.session.post(url)
            
            # POSTで失敗した場合、GETを試行
            if refresh_response.status_code == 403:
                logger.info("POSTが失敗しました。GETを試行します...")
                refresh_response = self.session.get(url)
            refresh_response.raise_for_status()
            
            refresh_data = refresh_response.json()
            self.id_token = refresh_data.get('idToken')
            
            if not self.id_token:
                raise ValueError("IDトークンの取得に失敗しました")
            
            # セッションにヘッダーを設定（IDトークンを直接使用）
            self.session.headers.update({
                'Authorization': f'Bearer {self.id_token}'
            })
            
            logger.info("認証が完了しました")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"認証エラー: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"レスポンステキスト: {e.response.text}")
                logger.error(f"ステータスコード: {e.response.status_code}")
            raise
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """APIリクエストを実行"""
        url = f"{self.base_url}/v1{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # レート制限対応
            time.sleep(self.rate_limit_delay)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"APIリクエストエラー ({endpoint}): {e}")
            raise
    
    def get_company_info(self, code: str) -> Dict[str, Any]:
        """
        企業情報を取得
        
        Args:
            code: 企業コード（例: '8697' for 楽天）
            
        Returns:
            企業情報の辞書
        """
        endpoint = "/listed/info"
        params = {"code": code}
        return self._make_request(endpoint, params)
    
    def get_financial_statements(self, code: str, year: Optional[int] = None) -> Dict[str, Any]:
        """
        財務諸表を取得
        
        Args:
            code: 企業コード
            year: 年度（指定しない場合は最新）
            
        Returns:
            財務諸表の辞書
        """
        endpoint = "/fins/statements"
        params = {"code": code}
        if year:
            params['year'] = year
        
        return self._make_request(endpoint, params)
    
    def get_stock_price(self, code: Optional[str] = None, date: Optional[str] = None, 
                       date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
        """
        株価情報を取得
        
        Args:
            code: 企業コード（codeまたはdateが必須）
            date: 特定の日付（YYYY-MM-DD形式、codeまたはdateが必須）
            date_from: 開始日（YYYY-MM-DD形式、範囲指定時）
            date_to: 終了日（YYYY-MM-DD形式、範囲指定時）
            
        Returns:
            株価情報の辞書
        """
        endpoint = "/prices/daily_quotes"
        params = {}
        
        if code:
            params['code'] = code
        if date:
            params['date'] = date
        if date_from:
            params['from'] = date_from
        if date_to:
            params['to'] = date_to
            
        # codeまたはdateのどちらかが必須
        if not code and not date:
            raise ValueError("codeまたはdateのどちらかを指定してください")
        
        return self._make_request(endpoint, params)
    
    def get_earnings_forecast(self, code: str) -> Dict[str, Any]:
        """
        業績予想を取得
        
        Args:
            code: 企業コード
            
        Returns:
            業績予想の辞書
        """
        endpoint = "/fins/announcement"
        params = {"code": code}
        return self._make_request(endpoint, params)
    
    def get_market_info(self, date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
        """
        取引カレンダー情報を取得
        
        Args:
            date_from: 開始日（YYYY-MM-DD形式）
            date_to: 終了日（YYYY-MM-DD形式）
            
        Returns:
            取引カレンダー情報の辞書
        """
        endpoint = "/markets/trading_calendar"
        params = {}
        if date_from:
            params['from'] = date_from
        if date_to:
            params['to'] = date_to
        return self._make_request(endpoint, params)
    
    # 以下のメソッドはFreeプランでは利用できない可能性があります
    # 必要に応じてAPIプランを確認してください
    
    def get_sector_info(self, sector_code: str) -> Dict[str, Any]:
        """
        セクター情報を取得（プラン制限あり）
        
        Args:
            sector_code: セクターコード
            
        Returns:
            セクター情報の辞書
        """
        # このエンドポイントは推測です。実際のAPIドキュメントを確認してください
        endpoint = "/listed/sectors"
        params = {"sector_code": sector_code}
        return self._make_request(endpoint, params)
    
    def search_companies(self, keyword: str) -> Dict[str, Any]:
        """
        企業を検索（プラン制限あり）
        
        Args:
            keyword: 検索キーワード（企業名、コード等）
            
        Returns:
            検索結果の辞書
        """
        # このエンドポイントは推測です。実際のAPIドキュメントを確認してください
        endpoint = "/listed/search"
        params = {"keyword": keyword}
        return self._make_request(endpoint, params)


def main():
    """メイン実行関数（サンプル）"""
    try:
        # J-Quants APIクライアントを初期化
        api = JQuantsAPI()
        
        # 楽天（8697）の企業情報を取得
        print("=== 楽天の企業情報 ===")
        company_info = api.get_company_info("8697")
        print(f"企業名: {company_info.get('company_name', 'N/A')}")
        print(f"業種: {company_info.get('sector', 'N/A')}")
        
        # 財務諸表を取得
        print("\n=== 財務諸表 ===")
        financial_data = api.get_financial_statements("8697")
        print(f"取得データ数: {len(financial_data.get('data', []))}")
        
        # 株価情報を取得（過去1週間）
        print("\n=== 株価情報 ===")
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        stock_data = api.get_stock_price("8697", start_date, end_date)
        print(f"取得データ数: {len(stock_data.get('data', []))}")
        
        # 業績予想を取得
        print("\n=== 業績予想 ===")
        forecast_data = api.get_earnings_forecast("8697")
        print(f"取得データ数: {len(forecast_data.get('data', []))}")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        print(f"エラー: {e}")


if __name__ == "__main__":
    main()
