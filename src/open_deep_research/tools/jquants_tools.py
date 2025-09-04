import time
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from .jquants_api import JQuantsAPI


JQUANTS_FINANCIAL_DESCRIPTION = (
    "J-Quants APIを使って企業コードと年度から財務情報（売上高、営業利益、当期純利益など）を取得します。過去5年分のデータが取得可能です。"
)

JQUANTS_STOCK_PRICE_DESCRIPTION = (
    "【最優先ツール】J-Quants APIを使って企業コードから現在の株価情報を取得します。"
    "株式分析では必ず最初に実行してください。直近1週間の株価データが取得できます。"
)

# Rate limiting management
_last_api_call_time = 0
_min_delay_between_calls = 2.0  # 最小2秒間隔

async def rate_limit_delay():
    """API呼び出し間に適切な遅延を挿入"""
    global _last_api_call_time
    current_time = time.time()
    time_since_last_call = current_time - _last_api_call_time
    
    if time_since_last_call < _min_delay_between_calls:
        delay = _min_delay_between_calls - time_since_last_call
        # ランダムな要素を追加してリクエストを分散
        delay += random.uniform(0.5, 1.5)
        await asyncio.sleep(delay)
    
    _last_api_call_time = time.time()

def remove_empty_values(data):
    """
    辞書から値が空（None, 空文字, 空リスト, 空辞書）のキーを再帰的に削除する
    
    Args:
        data: 処理対象のデータ（辞書、リスト、その他）
    
    Returns:
        空値が削除されたデータ
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            # 再帰的に処理
            cleaned_value = remove_empty_values(value)
            # 空でない値のみ保持
            if cleaned_value not in (None, "", [], {}):
                cleaned[key] = cleaned_value
        return cleaned
    elif isinstance(data, list):
        # リストの場合、各要素を再帰的に処理
        cleaned_list = []
        for item in data:
            cleaned_item = remove_empty_values(item)
            if cleaned_item not in (None, "", [], {}):
                cleaned_list.append(cleaned_item)
        return cleaned_list
    else:
        # プリミティブ型はそのまま返す
        return data

@tool(description=JQUANTS_FINANCIAL_DESCRIPTION)
async def get_financial_statements_tool(
    code: str,
    year: Optional[int] = None,
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """
    J-Quants APIを使って財務情報を取得します。

    Args:
        code (str): 企業コード
        year (Optional[int]): 年度（指定しない場合は最新）
    Returns:
        財務情報の辞書
    """
    # レート制限対応の遅延
    await rate_limit_delay()
    
    api = JQuantsAPI()
    raw_data = api.get_financial_statements(code, year)
    # 空の値を削除
    cleaned_data = remove_empty_values(raw_data)
    return cleaned_data

@tool(description=JQUANTS_STOCK_PRICE_DESCRIPTION)
async def get_recent_stock_price_tool(
    code: str,
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """
    【重要】株式分析で最初に実行すべきツール
    J-Quants APIを使って企業コードから現在の株価情報を取得します。
    投資判断には現在の株価情報が必須です。

    Args:
        code (str): 企業コード（4桁の数字）例：7203（トヨタ）、8697（楽天）
    Returns:
        現在の株価情報を含む辞書（終値、出来高、高値・安値等）
    """
    # 企業コードの検証
    if not code.isdigit() or len(code) != 4:
        return {
            "error": f"無効な企業コード: {code}（4桁の数字である必要があります）",
            "valid_format": "例: 7203（トヨタ）, 6502（東芝）, 9984（ソフトバンク）"
        }
    
    try:
        # レート制限対応の遅延
        await rate_limit_delay()
        
        # 直近1週間の日付を計算（土日を考慮して営業日のみ）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)  # 土日を考慮して10日前から
        
        date_from = start_date.strftime("%Y-%m-%d")
        date_to = end_date.strftime("%Y-%m-%d")
        
        api = JQuantsAPI()
        result = api.get_stock_price(code=code, date_from=date_from, date_to=date_to)
        
        # 結果に企業コード情報を追加
        result["requested_code"] = code
        result["date_range"] = f"{date_from} to {date_to}"
        
        return result
        
    except Exception as e:
        return {
            "error": f"株価取得エラー: {str(e)}",
            "code": code,
            "suggestion": "企業コードが正しいか、または企業が東証上場しているかを確認してください"
        }
