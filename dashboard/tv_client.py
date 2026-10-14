import os
import subprocess
import time
import requests
from typing import Optional
import pandas as pd
import logging

logger = logging.getLogger('tv_client')
TV_SERVICE_URL = "http://localhost:7788"

# Mapping Sàn → Prefix TradingView
EXCHANGE_MAP = {
    'HOSE': 'HOSE',
    'HNX': 'HNX',
    'UPCOM': 'UPCOM',
    'BINANCE': 'BINANCE',
    'FX': 'FX',
    'OANDA': 'OANDA'
}

def is_tv_service_alive() -> bool:
    """Kiểm tra tv_service có đang phản hồi không."""
    try:
        r = requests.get(f"{TV_SERVICE_URL}/candles", params={"symbol": "HOSE:VCB", "count": 1}, timeout=2.0)
        return r.status_code == 200 and r.json().get('ok', False)
    except Exception:
        return False

def ensure_tv_service() -> bool:
    """Đảm bảo tv_service đang chạy. Nếu chưa chạy, tự động khởi động process ngầm."""
    if is_tv_service_alive():
        return True
    
    # Tìm đường dẫn thư mục tv_service
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tv_service_dir = os.path.join(base_dir, "tv_service")
    server_js = os.path.join(tv_service_dir, "server.js")
    
    if os.path.exists(server_js):
        try:
            logger.info("[TV Client] Đang khởi động tv_service ngầm...")
            subprocess.Popen(
                ["node", "server.js"],
                cwd=tv_service_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            # Chờ tối đa 5 giây để service sẵn sàng
            for _ in range(10):
                time.sleep(0.5)
                if is_tv_service_alive():
                    logger.info("[TV Client] tv_service đã sẵn sàng!")
                    return True
        except Exception as e:
            logger.error(f"[TV Client] Không thể tự khởi động tv_service: {e}")
    
    return is_tv_service_alive()

def to_tv_symbol(symbol: str, exchange: str = 'HOSE') -> str:
    """Chuyển mã VN sang định dạng TradingView."""
    sym_clean = symbol.strip().upper()
    if ":" in sym_clean:
        return sym_clean
    ex = EXCHANGE_MAP.get(exchange.upper(), 'HOSE')
    return f"{ex}:{sym_clean}"

def _fetch_candles_from_service(tv_sym: str, timeframe: str = 'D', count: int = 250) -> Optional[pd.DataFrame]:
    """Helper nội bộ gọi endpoint /candles."""
    for attempt in range(2):
        try:
            r = requests.get(
                f"{TV_SERVICE_URL}/candles",
                params={"symbol": tv_sym, "timeframe": timeframe, "count": count},
                timeout=10
            )
            if r.status_code != 200:
                if attempt == 0:
                    time.sleep(0.3)
                    continue
                return None
            data = r.json()
            if not data.get('ok') or not data.get('data'):
                if attempt == 0:
                    time.sleep(0.3)
                    continue
                return None

            df = pd.DataFrame(data['data'])
            if df.empty or 'time' not in df.columns:
                return None

            # Chuẩn hóa thời gian: UNIX seconds UTC → datetime Asia/Ho_Chi_Minh
            df['time'] = pd.to_datetime(df['time'], unit='s', utc=True) \
                           .dt.tz_convert('Asia/Ho_Chi_Minh') \
                           .dt.tz_localize(None)
            df.set_index('time', inplace=True)
            cols = ['open', 'high', 'low', 'close', 'volume']
            df = df[[c for c in cols if c in df.columns]].astype(float)
            return df
        except Exception as e:
            if attempt == 0:
                time.sleep(0.3)
                continue
            logger.debug(f"[TV Client] fetch error for {tv_sym}: {e}")
            return None
    return None

def get_ohlcv(
    symbol: str,
    exchange: str = 'HOSE',
    timeframe: str = 'D',
    count: int = 250,
) -> Optional[pd.DataFrame]:
    """
    Lấy OHLCV từ TradingView Service với cơ chế tự động thử nhiều tiền tố sàn (HOSE, HNX, raw symbol).
    """
    sym = symbol.strip().upper()
    
    # 1. Thử symbol với exchange chỉ định
    candidates = []
    if ':' in sym:
        candidates.append(sym)
    else:
        ex_up = exchange.upper()
        candidates.append(f'{ex_up}:{sym}')
        for ex in ['HOSE', 'HNX', 'UPCOM']:
            c = f'{ex}:{sym}'
            if c not in candidates:
                candidates.append(c)
        candidates.append(sym)  # fallback không có tiền tố sàn

    for tv_sym in candidates:
        df = _fetch_candles_from_service(tv_sym, timeframe, count)
        if df is not None and len(df) >= 5:
            return df

    return None

def get_indicators(symbol: str, exchange: str = 'HOSE', indicator: str = 'STD;RSI') -> Optional[list]:
    """Lấy giá trị Indicator từ TradingView."""
    tv_sym = to_tv_symbol(symbol, exchange)
    try:
        r = requests.post(
            f"{TV_SERVICE_URL}/indicators",
            json={"symbol": tv_sym, "indicator": indicator, "timeframe": "D"},
            timeout=10
        )
        data = r.json()
        return data.get('data') if data.get('ok') else None
    except Exception as e:
        logger.error(f"[TV Client] get_indicators error: {e}")
        return None

def get_multiple_indicators(symbol: str, exchange: str = 'HOSE', indicators: list = None) -> Optional[list]:
    """Lấy nhiều Indicators cùng lúc thông qua TradingView Service để tối ưu tốc độ."""
    if not indicators:
        indicators = ["STD;RSI", "STD;MACD"]
    tv_sym = to_tv_symbol(symbol, exchange)
    try:
        r = requests.post(
            f"{TV_SERVICE_URL}/indicators",
            json={"symbol": tv_sym, "indicators": indicators, "timeframe": "D"},
            timeout=15
        )
        data = r.json()
        return data.get('data') if data.get('ok') else None
    except Exception as e:
        logger.error(f"[TV Client] get_multiple_indicators error: {e}")
        return None

def get_ohlcv_with_fallback(symbol: str, exchange: str = 'HOSE', **kwargs) -> Optional[pd.DataFrame]:
    """
    Ưu tiên tuyệt đối TradingView. Không tự động gọi vnstock để tránh rate-limit API.
    """
    df = get_ohlcv(symbol, exchange, **kwargs)
    if df is not None and len(df) >= 20:
        return df

    logger.warning(f"[TV Client] {symbol}: TradingView không trả về đủ dữ liệu.")
    return df
