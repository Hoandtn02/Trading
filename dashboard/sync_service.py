"""
Sync Engine v9 - Database-First Architecture (FULL SYNC)
- Uses vnstock_data for Fundamental data (like single-stock analyzer)
- Adds VWAP, Ichimoku, SuperTrend, MFI indicators
- Fixes Change% calculation
- Adds F-Score
- Applies consistent veto rules across all stocks
"""
import math
import os
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from time import sleep
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd

# Standard vnstock venv resolution (AGENTS.md)
for _venv_candidate in [
    os.path.expanduser('~/.venv/Lib/site-packages'),
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.venv', 'Lib', 'site-packages')),
]:
    if os.path.exists(_venv_candidate) and _venv_candidate not in sys.path:
        sys.path.insert(0, _venv_candidate)

from django.utils import timezone
from dashboard.models import StockData, StockAnalysis, SyncStatus, IndustryValuation, VN30_SYMBOLS

MAX_WORKERS = 3

# ============== INDUSTRY CONFIG (SHARED - Fallback) ==============
# Dùng chung cho cả Live scan và Backtest (chỉ là fallback khi không có Dynamic data)
INDUSTRY_CONFIG = {
    'Banking': {'type': 'PB', 'target': 1.65},
    'Real Estate': {'type': 'PB', 'target': 1.8},
    'Securities': {'type': 'PB', 'target': 2.0},
    'Technology': {'type': 'PE', 'target': 18.0},
    'Retail': {'type': 'PE', 'target': 15.0},
    'FMCG': {'type': 'PE', 'target': 14.0},
    'Oil & Gas': {'type': 'PE', 'target': 9.0},
    'Steel': {'type': 'PE', 'target': 8.5},
    'Rubber': {'type': 'PE', 'target': 10.0},
    'Conglomerate': {'type': 'PE', 'target': 10.0},
    'Default': {'type': 'PE', 'target': 11.0}
}

# Wealth Guard Cap multiplier
WEALTH_GUARD_CAP = 1.25  # Không cho phép P/E vượt quá 25% so với ngưỡng tĩnh

# Sector group mapping for scoring/exit differentiation
SECTOR_GROUP_MAP = {
    'cyclical': [
        'bất động sản', 'real estate', 'xây dựng', 'construction',
        'thép', 'steel', 'dầu', 'oil', 'gas', 'năng lượng', 'power',
        'rubber', 'tire', 'xi măng', 'cement', 'khoáng sản', 'mining',
        'tập đoàn', 'conglomerate', 'điện', 'electricity'
    ],
    'banking': [
        'ngân hàng', 'bank', 'bảo hiểm', 'insurance', 'tín dụng',
        'chứng khoán', 'securities', 'tài chính', 'finance'
    ],
    'growth_defensive': [
        'công nghệ', 'technology', 'bán lẻ', 'retail', 'tiêu dùng',
        'fmcg', 'consumer', 'dược', 'pharma', 'mỹ phẩm', 'cosmetic',
        'phân phối', 'distribution', 'thương mại', 'trading',
        'tiện ích', 'utilities', 'beverage', 'thực phẩm', 'food'
    ]
}

SECTOR_GROUP_LABELS = {
    'cyclical': 'Tài sản/Chu kỳ',
    'banking': 'Tài chính/Ngân hàng',
    'growth_defensive': 'Tăng trưởng/Phòng thủ',
    'general': 'Chung'
}


def get_sector_group(industry: str, sector_category: str = "") -> str:
    if not industry:
        return "general"
    industry_lower = industry.lower()
    for group, keywords in SECTOR_GROUP_MAP.items():
        if any(keyword in industry_lower for keyword in keywords):
            return group
    if sector_category:
        mapping = {
            'real_estate': 'cyclical',
            'manufacturing': 'cyclical',
            'retail': 'growth_defensive',
            'banking': 'banking',
            'general': 'general'
        }
        return mapping.get(sector_category, 'general')
    return "general"


# ============== DYNAMIC SECTOR VALUATION ==============

def sync_sector_benchmarks() -> Dict[str, Any]:
    """
    Đồng bộ P/E và P/B Median theo ngành từ Screener API.
    Sử dụng Median thay vì Mean để loại bỏ outliers.
    
    Returns:
        Dict với thông tin sync sector
    """
    from dashboard.models import IndustryValuation
    import traceback
    
    result = {
        "success": False,
        "sectors_synced": 0,
        "errors": [],
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        print("[Sector Sync] Bắt đầu sync sector benchmarks...")
        
        # Import vnstock_data
        try:
            from vnstock_data import Insights
            ins = Insights()
        except ImportError:
            result["errors"].append("vnstock_data not installed")
            print("[Sector Sync] ❌ vnstock_data not installed")
            return result
        
        # Lấy dữ liệu screener
        try:
            print("[Sector Sync] Đang lấy dữ liệu screener...")
            df_screener = ins.screener().filter()
            
            if df_screener is None or len(df_screener) == 0:
                result["errors"].append("Empty screener data")
                return result
                
        except Exception as e:
            result["errors"].append(f"Screener API error: {str(e)}")
            print(f"[Sector Sync] ❌ Screener API error: {e}")
            return result
        
        # Chuẩn hóa columns (screener có: pe, pb, market_cap, vi_sector hoặc industry_en)
        df = df_screener.copy()
        
        # Rename columns nếu cần
        if 'pe' in df.columns:
            df = df.rename(columns={'pe': 'ttm_pe'})
        if 'pb' in df.columns:
            df = df.rename(columns={'pb': 'ttm_pb'})
        
        # Kiểm tra columns
        print(f"[Sector Sync] Columns: {df.columns.tolist()[:10]}...")
        
        # Filter: chỉ lấy mã có vốn hóa > 100 tỷ
        df = df[df['market_cap'].notna() & (df['market_cap'] > 100)]
        
        # Filter P/E hợp lệ (> 0 và < 1000 để loại outliers)
        df_valid_pe = df[df['ttm_pe'].notna() & (df['ttm_pe'] > 0) & (df['ttm_pe'] < 1000)]
        
        # Filter P/B hợp lệ (> 0 và < 50 để loại outliers)
        df_valid_pb = df[df['ttm_pb'].notna() & (df['ttm_pb'] > 0) & (df['ttm_pb'] < 50)]
        
        print(f"[Sector Sync] Tổng cổ phiếu: {len(df)}, Hợp lệ: {len(df_valid_pe)}")
        
        # Xác định column ngành (ưu tiên vi_sector, fallback sang industry_en)
        sector_col = 'vi_sector' if 'vi_sector' in df.columns else 'industry_en'
        
        if sector_col not in df.columns:
            result["errors"].append(f"No sector column found. Available: {df.columns.tolist()}")
            return result
        
        # Nhóm theo sector và tính Median bằng pandas (vectorized)
        sector_stats = df_valid_pe.groupby(sector_col).agg(
            median_pe=('ttm_pe', 'median'),
            stock_count_pe=('symbol', 'count'),
            market_cap_avg=('market_cap', 'mean')
        ).reset_index()
        
        # Tính median P/B theo sector
        sector_pb_stats = df_valid_pb.groupby(sector_col).agg(
            median_pb=('ttm_pb', 'median'),
            stock_count_pb=('symbol', 'count')
        ).reset_index()
        
        # Merge P/E và P/B
        sector_stats = sector_stats.merge(sector_pb_stats, on=sector_col, how='outer')
        
        # Lấy stock_count = min của PE và PB count
        sector_stats['stock_count'] = sector_stats[['stock_count_pe', 'stock_count_pb']].min(axis=1)
        
        # Rename sector column
        sector_stats = sector_stats.rename(columns={sector_col: 'sector_name'})
        
        # Fill NaN values
        sector_stats = sector_stats.fillna(0)
        
        # Map sector name sang industry name
        SECTOR_NAME_MAP = {
            'Ngân hàng': 'Banking',
            'Bảo hiểm': 'Insurance',
            'Chứng khoán': 'Securities',
            'Bất động sản': 'Real Estate',
            'Công nghệ': 'Technology',
            'Bán lẻ': 'Retail',
            'Tiêu dùng': 'FMCG',
            'Dầu khí': 'Oil & Gas',
            'Điện': 'Power & Energy',
            'Xây dựng': 'Construction',
            'Công nghiệp': 'Industrial',
            'Vận tải': 'Transportation',
            'Y tế': 'Healthcare',
            'Viễn thông': 'Telecommunications',
            'Tiện ích': 'Utilities',
            'Truyền thông': 'Media',
            'Du lịch': 'Travel',
            'Thép': 'Steel',
            'Hóa chất': 'Chemicals',
            'Nông nghiệp': 'Agriculture',
            'Cao su': 'Rubber',
            'Ô tô': 'Automobiles',
            'Tập đoàn': 'Conglomerate',
            'Tài nguyên': 'Basic Resources',
            'Thực phẩm': 'Food',
        }
        
        # Sync vào database
        synced_count = 0
        for _, row in sector_stats.iterrows():
            sector_name = str(row['sector_name']) if pd.notna(row['sector_name']) else 'Unknown'
            industry_name = SECTOR_NAME_MAP.get(sector_name, sector_name)
            
            # Skip nếu stock_count < 3 (không đủ mẫu)
            if row['stock_count'] < 3:
                continue
            
            obj, created = IndustryValuation.objects.update_or_create(
                name=industry_name,
                defaults={
                    'sector_code': sector_name,
                    'median_pe': round(row['median_pe'], 2),
                    'median_pb': round(row['median_pb'], 2),
                    'stock_count': int(row['stock_count']),
                    'market_cap_avg': round(row['market_cap_avg'], 2),
                    'is_active': True
                }
            )
            synced_count += 1
        
        result["success"] = True
        result["sectors_synced"] = synced_count
        print(f"[Sector Sync] ✅ Đã sync {synced_count} sectors thành công!")
        
        # Print sample
        for _, row in sector_stats.head(5).iterrows():
            print(f"  - {row['sector_name']}: PE={row['median_pe']:.1f}, PB={row['median_pb']:.1f}, Count={row['stock_count']}")
        
    except Exception as e:
        result["errors"].append(str(e))
        print(f"[Sector Sync] ❌ Lỗi: {e}")
        traceback.print_exc()
    
    return result


def get_target_valuation(industry_name: str) -> Dict:
    """
    Lấy P/E và P/B target cho một ngành.
    
    Priority:
    1. Dynamic Median từ IndustryValuation (database)
    2. Fallback sang INDUSTRY_CONFIG (static)
    3. Wealth Guard Cap: Final = min(Dynamic, Static * 1.25)
    
    Returns:
        Dict với 'type' (PE/PB), 'target' (float), 'source' (dynamic/static)
    """
    # Tìm industry trong database
    try:
        iv = IndustryValuation.objects.filter(name=industry_name, is_active=True).first()
        
        if iv and iv.median_pe > 0:
            # Lấy static config để apply cap
            static_config = INDUSTRY_CONFIG.get(industry_name, INDUSTRY_CONFIG['Default'])
            
            # Determine valuation type
            val_type = static_config.get('type', 'PE')
            static_target = static_config.get('target', 11.0)
            
            if val_type == 'PB':
                # P/B: Apply Wealth Guard Cap
                final_target = min(iv.median_pb, static_target * WEALTH_GUARD_CAP)
                return {
                    'type': 'PB',
                    'target': round(final_target, 2),
                    'dynamic': round(iv.median_pb, 2),
                    'static': static_target,
                    'source': 'dynamic',
                    'cap_applied': final_target != iv.median_pb
                }
            else:
                # P/E: Apply Wealth Guard Cap
                final_target = min(iv.median_pe, static_target * WEALTH_GUARD_CAP)
                return {
                    'type': 'PE',
                    'target': round(final_target, 2),
                    'dynamic': round(iv.median_pe, 2),
                    'static': static_target,
                    'source': 'dynamic',
                    'cap_applied': final_target != iv.median_pe
                }
    except Exception:
        pass
    
    # Fallback: Sử dụng INDUSTRY_CONFIG
    static_config = INDUSTRY_CONFIG.get(industry_name, INDUSTRY_CONFIG['Default'])
    return {
        'type': static_config.get('type', 'PE'),
        'target': static_config.get('target', 11.0),
        'dynamic': 0.0,
        'static': static_config.get('target', 11.0),
        'source': 'static',
        'cap_applied': False
    }


# ============== CONSTANTS ==============
MAX_WORKERS = 3
UNIVERSE_SIZE = 100
MIN_LIQUIDITY_BILLION = 15  # Giá trị giao dịch TB phải > 15 tỷ/phiên
MIN_PRICE = 10000


def _get_top_100_by_liquidity() -> List[str]:
    """
    Lấy Top 100 mã thanh khoản cao nhất sàn HOSE một cách ĐỘNG.
    
    Logic:
    1. Lấy danh sách tất cả mã HOSE từ vnstock
    2. Với mỗi mã, tính thanh khoản = avg_volume(20 ngày) * avg_close(5 ngày)
    3. Lọc: price > 10,000 VND AND avg_value > 15 tỷ VND
    4. Sắp xếp giảm dần và trả về Top 100
    
    Fallback: Nếu API lỗi, trả về VN30 + Midcap phổ biến
    """
    warnings.filterwarnings('ignore')
    
    # VN30 + Midcap phổ biến (Fallback an toàn)
    FALLBACK_SYMBOLS = [
        # VN30 & Bluechips
        "VNM", "VCB", "VHM", "VIC", "VPB", "BID", "TCB", "CTG", "MBB", "ACB",
        "STB", "HPG", "FPT", "MWG", "PNJ", "TPB", "SHB", "SSI", "MSN", "GAS",
        "PLX", "VRE", "VIB", "SAB", "HDB", "LPB", "SSB", "GVR", "BCM", "VJC",
        # Midcap - Ngân hàng
        "OCB", "EIB", "MSB", "NAB", "KLB", "BAB", "PGB", "VBB", "ABB", "BVH",
        # Midcap - Bất động sản
        "NVL", "DIG", "DXG", "KDH", "HDG", "IDJ", "SJS", "DPG", "CRE", "NLG",
        "ASM", "IJC", "DPR", "VPH", "PDR", "HII", "SRA", "VIG", "NRC",
        # Midcap - Chứng khoán
        "VND", "HCM", "CTS", "VCI", "SHS", "VDS", "BVS", "TVS", "VIX", "APG",
        "BSI", "CSI", "EVS", "FTS", "HBS", "IVS", "MBS", "PHS", "SGB",
        # Midcap - Sản xuất & Vật liệu
        "DGC", "GMD", "SBT", "DGW", "CMG", "IMP", "VHC", "REE", "NT2", "DRC",
        "AAA", "ALT", "AMC", "BMC", "CSV", "DCL", "DHC", "DPM", "DVP", "HAP",
        # Midcap - Năng lượng & Dịch vụ
        "POW", "HAG", "BSR", "PVD", "PVC", "OGC", "ASP", "CAV", "CLC", "PLT",
        # Midcap - Bán lẻ & Tiêu dùng
        "ELC", "GCC", "HAX", "PET", "QNS", "SAT", "STK", "TMT", "FRT", "MWG",
        # Midcap - Công nghiệp & Khác
        "BMI", "CII", "CSM", "DXP", "HHS", "HT1", "KSB", "LIX", "LM8", "MSR",
        "VGC", "HHV", "LHG", "PVT", "GEX", "TTE", "SZC", "HLD", "NKG", "KHC",
    ]
    
    # Loại bỏ trùng lặp và lấy universe tiêu chuẩn (VN30 + Top Midcaps thanh khoản lớn)
    symbols = list(dict.fromkeys(FALLBACK_SYMBOLS))
    
    try:
        from dashboard.models import StockData
        db_symbols = list(StockData.objects.values_list('symbol', flat=True))
        for sym in db_symbols:
            sym_clean = str(sym).strip().upper()
            if sym_clean and sym_clean not in symbols:
                symbols.append(sym_clean)
            if len(symbols) >= UNIVERSE_SIZE:
                break
    except Exception:
        pass

    target_symbols = symbols[:UNIVERSE_SIZE]
    print(f"[Sync] Universe phân tích gồm {len(target_symbols)} mã (VN30 + Top Midcaps thanh khoản cao sàn HOSE)", flush=True)
    return target_symbols


def get_top_symbols_by_liquidity() -> List[str]:
    """Lấy Top 100 mã thanh khoản cao nhất - SỬ DỤNG LOGIC ĐỘNG"""
    return _get_top_100_by_liquidity()


def get_market_rsi() -> float:
    """Lấy RSI của VNIndex trực tiếp từ TradingView (tv_service)"""
    try:
        from dashboard.tv_client import get_ohlcv
        df = get_ohlcv("VNINDEX", count=60)
        if df is not None and len(df) >= 15 and 'close' in df.columns:
            close = df['close']
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
    except Exception:
        pass
    return 50.0


def _get_market_regime_from_etf_flow(default_regime: str = "NORMAL") -> str:
    """
    Macro/ETF foreign-flow sentiment hook.
    Ưu tiên đọc từ DB StockAnalysis của E1VFVN30 để tránh gọi API mạng.

    Returns:
        "NORMAL", "DEFENSE", hoặc "FREEZE"
    """
    try:
        from .models import StockAnalysis
        etf_analysis = StockAnalysis.objects.filter(symbol__symbol="E1VFVN30").first()
        if etf_analysis and etf_analysis.latest_net_val is not None:
            if etf_analysis.latest_net_val < 0 or etf_analysis.foreign_accumulated_trend == "DISTRIBUTING":
                return "DEFENSE"
    except Exception:
        pass
    return default_regime

def get_company_name(symbol: str) -> str:
    """Lấy tên công ty từ DB StockData, không gọi vnstock để tránh rate-limit"""
    try:
        from dashboard.models import StockData
        stock = StockData.objects.filter(symbol=symbol.upper()).first()
        if stock and stock.company_name and stock.company_name.strip():
            return stock.company_name.strip()
    except Exception:
        pass
    return symbol


def get_industry(symbol: str) -> str:
    """Lấy ngành từ DB StockData hoặc mapping tĩnh, không gọi mạng khi sync."""
    try:
        from dashboard.models import StockData, INDUSTRY_MAP
        stock = StockData.objects.filter(symbol=symbol.upper()).first()
        if stock and stock.industry and stock.industry.strip() and stock.industry.strip() != "Default":
            return stock.industry.strip()
        mapped = INDUSTRY_MAP.get(symbol.upper())
        if mapped:
            return mapped
    except Exception:
        pass
    return "Other"


def get_fundamental_data(symbol: str, fast_mode: bool = False, vnindex_df=None, df=None) -> Dict[str, Any]:
    """
    Lấy dữ liệu cơ bản với ưu tiên Database-First để tránh rate-limit vnstock:
    1. Đọc từ StockData và QuarterlyFinancial trong DB
    2. Chỉ gọi vnstock_data nếu DB thiếu dữ liệu
    """
    result = {
        'roe': None,
        'pe': None,
        'pb': None,
        'f_score': 0,
        'f_score_grade': 'F',
        'profit_growth': None,
        'profit_growth_note': 'N/A',
        'is_new_listing': False,
        'industry_performance': 0.0,
        'is_industry_leader': False,
        'foreign_buy_streak': 0,
        'latest_net_val': 0.0,
        'foreign_absorption_ratio': 0.0,
        'latest_net_val_2': 0.0,
        'foreign_buy_val': 0.0,
        'foreign_sell_val': 0.0,
        'foreign_trading_share': 0.0,
        'foreign_accumulated_trend': 'NEUTRAL',
        'foreign_accumulated_slope': 0.0,
    }

    def safe_float(val):
        if val is None or pd.isna(val):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    # 1. Đọc từ Database (StockData & QuarterlyFinancial) trước
    try:
        from dashboard.models import StockData, QuarterlyFinancial
        stock_db = StockData.objects.filter(symbol=symbol.upper()).first()
        if stock_db:
            if stock_db.pe is not None and stock_db.pe > 0:
                result['pe'] = stock_db.pe
            if stock_db.pb is not None and stock_db.pb > 0:
                result['pb'] = stock_db.pb
            if stock_db.roe is not None:
                result['roe'] = stock_db.roe
            if stock_db.f_score and stock_db.f_score > 0:
                result['f_score'] = stock_db.f_score
                result['f_score_grade'] = get_f_score_grade(stock_db.f_score)
            if stock_db.profit_growth is not None:
                result['profit_growth'] = stock_db.profit_growth
                result['profit_growth_note'] = stock_db.profit_growth_note or 'DB'
                result['is_new_listing'] = stock_db.is_new_listing

        qf = QuarterlyFinancial.objects.filter(symbol=symbol.upper()).order_by('-year', '-quarter').first()
        if qf:
            if result['roe'] is None and qf.roe is not None:
                result['roe'] = qf.roe
            if result['f_score'] == 0 and qf.f_score is not None and qf.f_score > 0:
                result['f_score'] = qf.f_score
                result['f_score_grade'] = get_f_score_grade(qf.f_score)
    except Exception:
        pass

    # 2. Nếu thiếu PE/PB/ROE, sử dụng cấu hình mặc định ngành, không gọi vnstock để tránh rate-limit
    industry = result.get('industry') or get_industry(symbol)
    ind_cfg = INDUSTRY_CONFIG.get(industry, INDUSTRY_CONFIG.get('Default', {}))
    if result['pe'] is None and ind_cfg.get('type') == 'PE':
        result['pe'] = ind_cfg.get('target', 12.0)
    if result['pb'] is None and ind_cfg.get('type') == 'PB':
        result['pb'] = ind_cfg.get('target', 1.8)
    if result['roe'] is None and result['pe'] and result['pb'] and result['pe'] > 0:
        result['roe'] = round((result['pb'] / result['pe']) * 100, 2)

    # 3. Luôn đọc dữ liệu giao dịch khối ngoại từ DB (tốc độ cao, không gọi mạng)
    try:
        foreign_metrics = get_exact_foreign_metrics(symbol)
        result['foreign_buy_streak'] = foreign_metrics.get('foreign_streak', 0)
        result['latest_net_val'] = foreign_metrics.get('latest_net_val', 0.0)
        result['foreign_absorption_ratio'] = foreign_metrics.get('foreign_absorption_ratio', 0.0)
        result['latest_net_val_2'] = foreign_metrics.get('latest_net_val_2', 0.0)
        result['foreign_buy_val'] = foreign_metrics.get('foreign_buy_val', 0.0)
        result['foreign_sell_val'] = foreign_metrics.get('foreign_sell_val', 0.0)
        result['foreign_trading_share'] = foreign_metrics.get('foreign_trading_share', 0.0)
        result['foreign_accumulated_trend'] = foreign_metrics.get('foreign_accumulated_trend', 'NEUTRAL')
        result['foreign_accumulated_slope'] = foreign_metrics.get('foreign_accumulated_slope', 0.0)
    except Exception:
        pass

    # 4. Luôn tính toán Relative Strength (RS so với VNINDEX) - Chỉ báo kỹ thuật cần tính trong mọi chế độ
    try:
        result['industry_performance'] = get_industry_performance(symbol, df=df, vnindex_df=vnindex_df)
        result['is_industry_leader'] = result['industry_performance'] >= 0
    except Exception:
        pass

    # 5. Tính toán F-Score & Profit growth nếu chưa có
    if not fast_mode:
        if result['profit_growth'] is None:
            growth_info = calculate_profit_growth(symbol)
            result['profit_growth'] = growth_info.get('profit_growth')
            result['profit_growth_note'] = growth_info.get('profit_growth_note', 'N/A')
            result['is_new_listing'] = growth_info.get('is_new_listing', False)

        if result['f_score'] == 0:
            result['f_score'] = calculate_f_score(symbol, result)
            result['f_score_grade'] = get_f_score_grade(result['f_score'])

    return result

def get_industry_pe_average(symbol: str) -> Optional[float]:
    """
    Lấy P/E trung bình ngành của mã cổ phiếu
    
    Priority:
    1. Từ bảng IndustryValuation (đã được lọc P/E > 0)
    2. Fallback: P/E thị trường VNINDEX
    """
    try:
        # Lấy thông tin ngành của mã từ StockData
        from .models import StockData
        try:
            stock = StockData.objects.get(symbol=symbol.upper())
            industry = stock.industry
        except:
            industry = None
        
        # Normalize industry name
        if industry:
            industry_key = next((k for k in INDUSTRY_CONFIG if k.lower() in industry.lower()), None)
            
            if industry_key:
                # Lấy từ IndustryValuation (đã filtered P/E > 0)
                try:
                    iv = IndustryValuation.objects.filter(name=industry_key, is_active=True).first()
                    if iv and iv.median_pe > 0:
                        return round(iv.median_pe, 2)
                except:
                    pass
        
        # Fallback P/E thị trường: dùng cấu hình mặc định ngành, không gọi vnstock
        
        # Final fallback: sử dụng INDUSTRY_CONFIG
        if industry:
            industry_key = next((k for k in INDUSTRY_CONFIG if k.lower() in industry.lower()), 'Default')
            return INDUSTRY_CONFIG.get(industry_key, INDUSTRY_CONFIG['Default']).get('target')
        
        return INDUSTRY_CONFIG['Default']['target']
        
    except Exception:
        return None


def calculate_optimal_position(
    account_balance: float,
    risk_tolerance: float,
    entry_price: float,
    support_price: float
) -> float:
    """
    Tính số tiền giải ngân tối ưu dựa trên công thức:
    Vốn giải ngân = (Số dư × % Rủi ro) / (Entry - SMA50)
    
    Args:
        account_balance: Số dư tài khoản (VND)
        risk_tolerance: % rủi ro chấp nhận (ví dụ: 2.0 = 2%)
        entry_price: Giá mua (VND)
        support_price: Giá hỗ trợ cứng SMA50 (VND)
    
    Returns:
        Số tiền nên giải ngân (VND)
    """
    try:
        if entry_price <= 0 or support_price <= 0 or entry_price <= support_price:
            return 0
        
        # Risk amount = Số dư × % rủi ro
        risk_amount = account_balance * (risk_tolerance / 100)
        
        # Khoảng cách từ Entry đến Support (Hard Risk)
        hard_risk_per_share = entry_price - support_price
        
        # Số cổ phiếu tối đa = Risk Amount / Hard Risk per share
        shares = risk_amount / hard_risk_per_share
        
        # Vốn giải ngân = Số cổ phiếu × Giá mua
        position_value = shares * entry_price
        
        return round(position_value, -3)  # Làm tròn đến 1000 VND gần nhất
    except Exception as e:
        return 0


def build_veto_response(
    symbol: str,
    tech: Dict[str, Any],
    fund_data: Dict[str, Any],
    veto_reason: str,
    entry: float,
    support_price: float,
    avg_volume_value: float = 0.0,
    industry: str = "",
    market_rsi: float = 50.0
) -> Dict[str, Any]:
    """
    Tạo response chuẩn hóa khi cổ phiếu bị VETO.

    Layer 1 (Gatekeepers) của pipeline. Trả về dict đầy đủ các field
    mà compute_core_logic() thường trả về, nhưng với signal="WAIT" và
    master_score=10.

    Args:
        symbol: Mã cổ phiếu
        tech: Dict chỉ số kỹ thuật
        fund_data: Dict dữ liệu cơ bản
        veto_reason: Lý do veto
        entry: Giá vào (entry price)
        support_price: Giá hỗ trợ
        avg_volume_value: Giá trị volume TB20 (tỷ đồng)
        industry: Tên ngành
        market_rsi: RSI thị trường

    Returns:
        Dict với tất cả các field của compute_core_logic() nhưng bị veto
    """
    price_val = tech.get("price", 0)
    vwap_val = tech.get("vwap", price_val)
    sma20_val = tech.get("sma_20", price_val)
    fv_daily = round((vwap_val * 0.4) + (sma20_val * 0.6), 2)
    atr_val = tech.get("atr", price_val * 0.02)
    rr_ratio = 0.0
    stop_loss = round(support_price * 0.985, 2) if support_price > 0 else round(entry * 0.96, 2)
    take_profit = round(entry + 2 * atr_val, 2)

    return {
        # Basic info
        "symbol": symbol,
        "price": price_val,
        "change_percent": tech.get("change_percent", 0),
        "volume": tech.get("volume", 0),
        # Technical
        "rsi": tech.get("rsi", 50),
        "mfi": tech.get("mfi", 50),
        "adx": tech.get("adx", 25),
        "plus_di": tech.get("plus_di", 0),
        "minus_di": tech.get("minus_di", 0),
        "cmf": tech.get("cmf", 0),
        "atr": tech.get("atr", 0),
        "sma_10": tech.get("sma_10", 0),
        "sma_20": tech.get("sma_20", 0),
        "sma_50": tech.get("sma_50", 0),
        "bb_upper": tech.get("bb_upper", 0),
        "bb_middle": tech.get("bb_middle", 0),
        "bb_lower": tech.get("bb_lower", 0),
        "bb_percent": tech.get("bb_percent", 50),
        "macd": tech.get("macd", 0),
        "macd_signal": tech.get("macd_signal", 0),
        "volume_ratio": tech.get("volume_ratio", 1.0),
        # Advanced TA
        "vwap": tech.get("vwap", price_val),
        "vwap_status": tech.get("vwap_status", "neutral"),
        "ichimoku_tenkan": tech.get("ichimoku_tenkan", 0),
        "ichimoku_kijun": tech.get("ichimoku_kijun", 0),
        "ichimoku_status": tech.get("ichimoku_status", "neutral"),
        "supertrend": tech.get("supertrend", 0),
        "supertrend_signal": tech.get("supertrend_signal", "neutral"),
        # Avg volume value
        "avg_volume_value": avg_volume_value,
        # Trading levels
        "entry_price": entry,
        "stop_loss": stop_loss,
        "trailing_sl": stop_loss,
        "take_profit": take_profit,
        "risk_reward_ratio": rr_ratio,
        "rr_quality": "Poor",
        "rr_quality_detail": "R:R thấp - VETO",
        "rr_warning": "VETO - không khuyến nghị giao dịch",
        # Fair Value
        "fv_daily": fv_daily,
        "valuation_status": "RISK",
        "intrinsic_value": round(price_val, 2),
        "sector_median_pe": None,
        "valuation_source": "veto",
        "valuation_cap_applied": False,
        "industry_config": {},
        # Target Yield & Est. Days
        "target_yield_pct": 0.0,
        "trend_factor": 0.6,
        "estimated_days_to_target": 0.0,
        "timeframe_label": "VETO",
        "timeframe_color": "red",
        "expected_profit_per_day": 0.0,
        "upside_per_day": 0.0,
        # Scores
        "master_score": 10,
        "base_master_score": 10,
        "market_weight": 0,
        "technical_score": 10,
        "fundamental_score": 10,
        # Safe Entry & Resistance
        "is_safe_entry": False,
        "has_high_resistance": False,
        # Signal & Status
        "signal": "WAIT",
        "is_vetoed": True,
        "veto_reason": veto_reason,
        "is_fast_pick": False,
        "is_short_term_qualified": False,
        "is_slow_mode": False,
        "is_high_risk": True,
        "is_market_high_risk": market_rsi > 80,
        "stock_risk_level": "High",
        "stock_risk_reason": f"VETO: {veto_reason}",
        "has_inverted_sl": stop_loss >= entry,
        "is_inverted_risk": True,
        # Criteria
        "criteria_met": 0,
        "criteria_list": [],
        "criteria_names": [],
        # Recommendation Label
        "recommendation_label": "WAIT (VETO)",
        # Trend
        "trend": "SIDEWAYS",
        "breakout_status": "VETO",
        # Market
        "market_rsi": market_rsi,
        # Fundamental
        "roe": fund_data.get('roe'),
        "pe": fund_data.get('pe'),
        "pb": fund_data.get('pb'),
        "f_score": fund_data.get('f_score', 0),
        "f_score_grade": get_f_score_grade(fund_data.get('f_score', 0)),
        "profit_growth": fund_data.get('profit_growth'),
        # Earning Guidance
        "annual_profit_plan": fund_data.get('annual_profit_plan'),
        "current_ytd_profit": fund_data.get('current_ytd_profit'),
        "profit_plan_completion": None,
        "profit_plan_status": "N/A",
        "plan_penalty_applied": 0,
        "profit_growth_note": fund_data.get('profit_growth_note', 'N/A'),
        "is_new_listing": fund_data.get('is_new_listing', False),
        # Smart Money & Industry
        "foreign_buy_streak": 0,
        "foreign_bonus": 0,
        "latest_net_val": 0.0,
        "foreign_absorption_ratio": 0.0,
        "latest_net_val_2": 0.0,
        "industry_performance": fund_data.get('industry_performance', 0),
        "is_industry_leader": False,
        # Real R:R
        "hard_risk_pct": 0.0,
        "support_price": round(support_price, 2),
        "risk_percent": 0.0,
        # P/E Industry
        "pe_industry_avg": fund_data.get('pe_industry_avg') or 0,
        # Early Exit
        "early_exit_trigger_pct": 2.0,
        "early_exit_drop_pct": 0.7,
        "optimal_position_size": 0,
        "account_balance": 100_000_000,
        "risk_tolerance_pct": 2.0,
        # Industry
        "industry": industry,
        # Relative Strength (RS)
        "rs_bonus": 0,
        "rs_label": "NEUTRAL",
        "rs_industry_performance": fund_data.get('industry_performance', 0),
        # Entry quality (new fields)
        "entry_quality": "BAD",
        "entry_quality_reason": f"VETO: {veto_reason}",
    }


def get_exact_foreign_metrics(symbol: str) -> dict:
    """
    Lấy chỉ số khối ngoại ưu tiên từ DB StockAnalysis để tránh rate-limit vnstock.
    Trả về:
        foreign_streak: Số phiên liên tiếp mua ròng
        latest_net_val: Giá trị mua ròng phiên gần nhất (VND)
        foreign_absorption_ratio: % khối ngoại mua ròng / tổng thanh khoản phiên
        latest_net_val_2: Giá trị mua ròng phiên trước
        foreign_buy_val: Giá trị mua phiên gần nhất (VND)
        foreign_sell_val: Giá trị bán phiên gần nhất (VND)
        foreign_trading_share: % giá trị giao dịch khối ngoại / tổng thanh khoản phiên
        foreign_accumulated_trend: 'ACCUMULATING'/'DISTRIBUTING'/'NEUTRAL'
        foreign_accumulated_slope: độ dốc của đường lũy kế net_val
    """
    default = {
        "foreign_streak": 0,
        "latest_net_val": 0.0,
        "foreign_absorption_ratio": 0.0,
        "latest_net_val_2": 0.0,
        "foreign_buy_val": 0.0,
        "foreign_sell_val": 0.0,
        "foreign_trading_share": 0.0,
        "foreign_accumulated_trend": "NEUTRAL",
        "foreign_accumulated_slope": 0.0,
        "foreign_sell_streak": 0,
        "streak_start_date": None,
        "net_val_latest": 0.0,
        "ranking_date": None,
    }
    try:
        from .models import StockAnalysis
        existing = StockAnalysis.objects.filter(symbol__symbol=symbol).first()
        if existing:
            default["foreign_streak"] = getattr(existing, 'foreign_buy_streak', 0) or 0
            default["latest_net_val"] = getattr(existing, 'latest_net_val', 0.0) or 0.0
            default["foreign_absorption_ratio"] = getattr(existing, 'foreign_absorption_ratio', 0.0) or 0.0
            default["latest_net_val_2"] = getattr(existing, 'latest_net_val_2', 0.0) or 0.0
            default["foreign_buy_val"] = getattr(existing, 'foreign_buy_val', 0.0) or 0.0
            default["foreign_sell_val"] = getattr(existing, 'foreign_sell_val', 0.0) or 0.0
            default["foreign_trading_share"] = getattr(existing, 'foreign_trading_share', 0.0) or 0.0
            default["foreign_accumulated_trend"] = getattr(existing, 'foreign_accumulated_trend', "NEUTRAL") or "NEUTRAL"
            default["foreign_accumulated_slope"] = getattr(existing, 'foreign_accumulated_slope', 0.0) or 0.0
            default["foreign_sell_streak"] = getattr(existing, 'foreign_sell_streak', 0) or 0
            default["streak_start_date"] = getattr(existing, 'streak_start_date', None)
            default["net_val_latest"] = getattr(existing, 'latest_net_val', 0.0) or 0.0
            default["ranking_date"] = getattr(existing, 'ranking_date', None)
            return default
    except Exception:
        pass

    return default


def sync_foreign_flow_from_vci(symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Đồng bộ dữ liệu giao dịch khối ngoại từ bảng giá VCI (hoàn toàn miễn phí, không tốn hạn ngạch vnstock).
    Cập nhật trực tiếp vào StockAnalysis:
    - latest_net_val
    - foreign_buy_val
    - foreign_sell_val
    - foreign_absorption_ratio
    - foreign_trading_share
    - foreign_accumulated_trend
    - foreign_buy_streak / foreign_sell_streak
    """
    from .models import StockData, StockAnalysis
    
    if not symbols:
        symbols = list(StockData.objects.values_list('symbol', flat=True))
    if not symbols:
        return {}
        
    results = {}
    chunk_size = 40
    
    try:
        from vnstock.explorer.vci.trading import Trading
        t = Trading(show_log=False)
    except Exception as e:
        print(f"[Foreign Flow] Không thể khởi tạo VCI Trading: {e}")
        return {}

    for i in range(0, len(symbols), chunk_size):
        chunk = [str(s).strip().upper() for s in symbols[i:i+chunk_size] if s]
        if not chunk:
            continue
        try:
            df = t.price_board(chunk)
            if df is None or df.empty:
                continue
                
            for _, r in df.iterrows():
                try:
                    sym = str(r[('listing', 'symbol')]).strip().upper()
                    buy_val = float(r[('match', 'foreign_buy_value')] or 0.0)
                    sell_val = float(r[('match', 'foreign_sell_value')] or 0.0)
                    net_val = buy_val - sell_val
                    tot_val = float(r[('match', 'accumulated_value')] or 0.0) * 1e6
                    abs_pct = round(abs(net_val) / tot_val * 100, 2) if tot_val > 0 else 0.0
                    share_pct = round((buy_val + sell_val) / tot_val * 100, 2) if tot_val > 0 else 0.0
                    
                    stock = StockData.objects.filter(symbol=sym).first()
                    if not stock:
                        continue
                    
                    analysis, _ = StockAnalysis.objects.get_or_create(symbol=stock)
                    prev_net = analysis.latest_net_val or 0.0
                    prev_buy_streak = analysis.foreign_buy_streak or 0
                    prev_sell_streak = analysis.foreign_sell_streak or 0
                    
                    # Cập nhật chuỗi mua / bán
                    if net_val > 0:
                        new_buy_streak = (prev_buy_streak + 1) if prev_net > 0 else 1
                        new_sell_streak = 0
                        trend = "ACCUMULATING"
                    elif net_val < 0:
                        new_sell_streak = (prev_sell_streak + 1) if prev_net < 0 else 1
                        new_buy_streak = 0
                        trend = "DISTRIBUTING"
                    else:
                        new_buy_streak = 0
                        new_sell_streak = 0
                        trend = "NEUTRAL"
                    
                    analysis.latest_net_val_2 = prev_net
                    analysis.latest_net_val = net_val
                    analysis.foreign_buy_val = buy_val
                    analysis.foreign_sell_val = sell_val
                    analysis.foreign_absorption_ratio = abs_pct
                    analysis.foreign_trading_share = share_pct
                    analysis.foreign_accumulated_trend = trend
                    analysis.foreign_buy_streak = new_buy_streak
                    analysis.foreign_sell_streak = new_sell_streak
                    analysis.save()
                    
                    results[sym] = {
                        "net_val": net_val,
                        "buy_val": buy_val,
                        "sell_val": sell_val,
                        "absorption": abs_pct,
                        "trend": trend,
                        "streak": new_buy_streak,
                    }
                except Exception:
                    continue
        except Exception as chunk_err:
            print(f"[Foreign Flow] Lỗi chunk {chunk[:3]}: {chunk_err}")
            
    return results


def get_industry_performance(symbol: str, df: pd.DataFrame = None, lookback: int = 5, vnindex_df=None) -> float:
    """
    Lấy RS (Relative Strength) của mã so với VNIndex.
    Hoàn toàn sử dụng dữ liệu nến OHLCV từ TradingView hoặc DataFrame đã truyền vào,
    không gọi bất kỳ API vnstock nào để tránh rate-limit.
    """
    try:
        lookback = min(lookback, 20)

        # 1. Lấy dữ liệu VNINDEX
        vn_df = vnindex_df
        if vn_df is None or len(vn_df) < lookback:
            from django.core.cache import cache
            vn_df = cache.get('vnindex_history')
        if vn_df is None or len(vn_df) < lookback:
            from dashboard.tv_client import get_ohlcv
            vn_df = get_ohlcv('VNINDEX', count=max(lookback + 10, 60))
            if vn_df is not None and len(vn_df) >= lookback:
                try:
                    from django.core.cache import cache
                    cache.set('vnindex_history', vn_df, 300)
                except Exception:
                    pass

        # 2. Lấy dữ liệu mã cổ phiếu
        stock_df = df
        if stock_df is None or len(stock_df) < lookback:
            from dashboard.tv_client import get_ohlcv
            stock_df = get_ohlcv(symbol, count=max(lookback + 10, 60))

        # 3. Tính toán Relative Strength
        if (stock_df is not None and vn_df is not None and
            len(stock_df) >= lookback and len(vn_df) >= lookback and
            'close' in stock_df.columns and 'close' in vn_df.columns):

            s_close = stock_df['close'].dropna()
            v_close = vn_df['close'].dropna()

            if len(s_close) >= lookback and len(v_close) >= lookback:
                s_base = float(s_close.iloc[-lookback])
                s_last = float(s_close.iloc[-1])
                v_base = float(v_close.iloc[-lookback])
                v_last = float(v_close.iloc[-1])

                if s_base > 0 and v_base > 0:
                    stock_return = ((s_last - s_base) / s_base) * 100
                    vn_return = ((v_last - v_base) / v_base) * 100
                    rs = round(stock_return - vn_return, 2)
                    return rs

        # Fallback từ DB nếu có
        try:
            from dashboard.models import StockData
            stk = StockData.objects.filter(symbol=symbol).first()
            if stk and stk.rs_rating:
                return round(float(stk.rs_rating), 2)
        except Exception:
            pass

        return 0.0
    except Exception as e:
        print(f"[RS][{symbol}] error={e}")
        return 0.0

def calculate_profit_growth(symbol: str) -> dict:
    """
    Calculate profit growth với ưu tiên: DB > TTM > YoY > QoQ
    Priority:
    1. TTM (Trailing Twelve Months) - ổn định nhất
    2. YoY (Year-over-Year) - chính xác nhất
    3. QoQ (Quarter-over-Quarter) với hệ số 0.8 - dự phòng
    4. NEW_LISTING - cổ phiếu mới (< 2 quý dữ liệu)
    """
    result = {
        'profit_growth': None,
        'profit_growth_note': 'N/A',
        'is_new_listing': False
    }
    try:
        from dashboard.models import StockData
        stk = StockData.objects.filter(symbol=symbol.upper()).first()
        if stk and stk.profit_growth is not None:
            return {
                'profit_growth': stk.profit_growth,
                'profit_growth_note': stk.profit_growth_note or 'DB',
                'is_new_listing': stk.is_new_listing
            }
    except Exception:
        pass
    
    # Không gọi mạng vnstock_data - chỉ dùng dữ liệu từ DB
    return result


def calculate_f_score(symbol: str, fund_data: dict = None) -> int:
    """
    Calculate Piotroski F-Score (0-9)
    Ưu tiên: fund_data -> DB (QuarterlyFinancial/StockData) -> vnstock_data (fallback).
    """
    # 1. Từ fund_data nếu có
    if fund_data and isinstance(fund_data, dict):
        f = fund_data.get('f_score')
        if f is not None and isinstance(f, (int, float)) and f > 0:
            return int(f)

    # 2. Từ DB QuarterlyFinancial
    try:
        from dashboard.models import QuarterlyFinancial
        qf = QuarterlyFinancial.objects.filter(symbol=symbol).order_by('-year', '-quarter').first()
        if qf and qf.f_score is not None and qf.f_score > 0:
            return int(qf.f_score)
    except Exception:
        pass

    # 3. Từ DB StockData
    try:
        from dashboard.models import StockData
        stk = StockData.objects.filter(symbol=symbol).first()
        if stk and stk.f_score is not None and stk.f_score > 0:
            return int(stk.f_score)
    except Exception:
        pass

    # Không gọi mạng vnstock_data - chỉ dùng dữ liệu từ DB
    return 0


def get_f_score_grade(score: int) -> str:
    """Convert F-Score to grade"""
    if score >= 8:
        return "A"
    elif score >= 6:
        return "B"
    elif score >= 4:
        return "C"
    elif score >= 2:
        return "D"
    else:
        return "F"


# ============== SECTOR-SPECIFIC SCORING FUNCTIONS (V3) ==============

def get_sector_category(industry: str, icb_code: str = "") -> str:
    """
    Classify industry into sector category for scoring purposes.
    Returns: 'banking', 'real_estate', 'manufacturing', 'retail', 'general'
    
    FIX v3: Extended keywords for SAB, beverages, consumer goods.
    Also supports ICB code for accurate classification.
    
    ICB Industry Codes Reference:
    - 1000/1500/2500/2700/2790/3500/3770: Food, beverage, consumer
    - 3500: Thực phẩm và đồ uống
    - 3530: Bia và đồ uống
    - 3533: Sản xuất bia
    - 3537: Đồ uống & giải khát
    - 5000: Consumer staples
    - 5500: Personal care, pharma
    - 8000: Ngân hàng
    - 8500: Bất động sản
    - 9000: Technology
    """
    # ICB Code-based classification (highest priority)
    if icb_code:
        icb_prefix = str(icb_code)[:2] if len(str(icb_code)) >= 2 else str(icb_code)
        if icb_code in ['3530', '3533', '3537'] or icb_prefix in ['35', '37', '50', '55']:
            return 'manufacturing'
        if icb_prefix == '80':  # Banks
            return 'banking'
        if icb_prefix == '85':  # Real Estate
            return 'real_estate'
        if icb_prefix == '40' or icb_prefix == '90':  # Retail / Technology
            return 'retail'
    
    if not industry:
        return 'general'
    
    industry_lower = industry.lower()
    
    # Securities: separate from Banking because business model and key metrics differ
    if 'chứng khoán' in industry_lower:
        return 'general'
    
    # Banking & Financial
    if any(k in industry_lower for k in ['bank', 'ngân hàng', 'bảo hiểm', 'tín dụng', 'tài chính']):
        return 'banking'
    
    # Real Estate
    if any(k in industry_lower for k in ['bất động sản', 'real estate', 'xây dựng', 'construction']):
        return 'real_estate'
    
    # Manufacturing (Capital Intensive) - Extended keywords for SAB, beverages
    manufacturing_keywords = [
        'thép', 'steel', 'điện', 'power', 'năng lượng', 'dầu', 'oil', 'gas',
        'hóa', 'chem', 'xi măng', 'cement', 'phân bón', 'fertilizer',
        'bia', 'rượu', 'bia/nước', 'đồ uống', 'beverage', 'giải khát',
        'thực phẩm', 'food', 'chế biến', 'processing', 'sản xuất', 'manufacturing',
        'rubber', 'tire', 'khoáng sản', 'mining', 'cao su'
    ]
    if any(k in industry_lower for k in manufacturing_keywords):
        return 'manufacturing'
    
    # Retail & Consumer - Extended keywords
    retail_keywords = [
        'bán lẻ', 'retail', 'fmcg', 'tiêu dùng', 'consumer',
        'dược', 'pharma', 'mỹ phẩm', 'cosmetic', 'bán buôn', 'wholesale',
        'thương mại', 'trading', 'phân phối', 'distribution',
        'công nghệ', 'technology', 'phần mềm', 'software'
    ]
    if any(k in industry_lower for k in retail_keywords):
        return 'retail'
    
    # FIX: Map SAB's specific industry names if they exist
    sab_keywords = ['sabmiller', 'sabre', 'brewery', 'harworth']
    if any(k in industry_lower for k in sab_keywords):
        return 'manufacturing'
    
    return 'general'


def score_banking_sector(raw_data: Dict[str, Any], symbol: str = "") -> Dict[str, Any]:
    """
    Score banking sector stocks using P/B, NIM, NPL, CASA metrics.
    Banking uses P/B instead of P/E for valuation.
    
    ROBUST FALLBACK: If essential banking metrics (NIM/NPL) are missing,
    automatically falls back to general scoring to avoid 0-score errors.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # ROBUST FALLBACK: Check for essential banking data
    has_nim = raw_data.get('nim') or raw_data.get('net_interest_margin')
    has_npl = raw_data.get('npl') or raw_data.get('npl_ratio')
    
    if not (has_nim or has_npl):
        logger.warning(f"[Data Warning] Missing sector metrics for {symbol or 'Unknown'}, falling back to General Score")
        result = score_general_sector(raw_data)
        result['fallback'] = True
        result['fallback_reason'] = 'Missing banking metrics (NIM/NPL)'
        return result
    
    result = {
        'fund_score': 0,
        'primary_metric': 'P/B',
        'primary_value': raw_data.get('pb'),
        'sector_metrics': {}
    }
    
    pb = raw_data.get('pb')
    roe = raw_data.get('roe')
    pe = raw_data.get('pe')
    
    # P/B scoring (Primary for banks)
    # Good P/B for banks: < 1.5, Great: < 1.0
    if pb:
        if pb < 0.8:
            result['fund_score'] += 25
        elif pb < 1.0:
            result['fund_score'] += 22
        elif pb < 1.5:
            result['fund_score'] += 18
        elif pb < 2.0:
            result['fund_score'] += 12
        else:
            result['fund_score'] += 5
    
    # ROE scoring (banks typically have 15-25% ROE)
    if roe:
        if roe >= 20:
            result['fund_score'] += 25
        elif roe >= 15:
            result['fund_score'] += 20
        elif roe >= 10:
            result['fund_score'] += 12
        elif roe >= 5:
            result['fund_score'] += 6
        else:
            result['fund_score'] += 0
    
    # NIM (Net Interest Margin) - if available
    nim = raw_data.get('nim') or raw_data.get('net_interest_margin')
    if nim:
        result['sector_metrics']['nim'] = nim
        if nim >= 4:
            result['fund_score'] += 15
        elif nim >= 3:
            result['fund_score'] += 10
        elif nim >= 2:
            result['fund_score'] += 5
    
    # NPL (Non-Performing Loans) - if available
    npl = raw_data.get('npl') or raw_data.get('npl_ratio')
    if npl:
        result['sector_metrics']['npl'] = npl
        if npl <= 2:
            result['fund_score'] += 20
        elif npl <= 3:
            result['fund_score'] += 12
        elif npl <= 5:
            result['fund_score'] += 5
        else:
            result['fund_score'] -= 10  # Penalty
    
    # CASA ratio - if available
    casa = raw_data.get('casa') or raw_data.get('casa_ratio')
    if casa:
        result['sector_metrics']['casa'] = casa
        if casa >= 30:
            result['fund_score'] += 10
        elif casa >= 20:
            result['fund_score'] += 5
    
    # Capital adequacy (CAR) - if available
    car = raw_data.get('car') or raw_data.get('capital_adequacy_ratio')
    if car:
        result['sector_metrics']['car'] = car
        if car >= 13:
            result['fund_score'] += 5
    
    # Cap at 100
    result['fund_score'] = min(result['fund_score'], 100)
    
    return result


def score_real_estate_sector(raw_data: Dict[str, Any], symbol: str = "") -> Dict[str, Any]:
    """
    Score real estate sector stocks using D/E, Inventory status, and land bank.
    
    ROBUST FALLBACK: If essential RE data (D/E) is missing,
    automatically falls back to general scoring.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # ROBUST FALLBACK: Check for essential RE data
    has_de = raw_data.get('debt_equity') or raw_data.get('de')
    
    if not has_de:
        logger.warning(f"[Data Warning] Missing RE metrics for {symbol or 'Unknown'}, falling back to General Score")
        result = score_general_sector(raw_data)
        result['fallback'] = True
        result['fallback_reason'] = 'Missing RE metrics (D/E)'
        return result
    
    result = {
        'fund_score': 0,
        'primary_metric': 'D/E',
        'primary_value': has_de,
        'sector_metrics': {}
    }
    
    de = has_de
    roe = raw_data.get('roe')
    pb = raw_data.get('pb')
    
    # D/E scoring (Critical for RE)
    # Good D/E for RE: < 1.0, Caution: 1.0-1.5, High: > 1.5
    if de:
        if de < 0.5:
            result['fund_score'] += 25
        elif de < 1.0:
            result['fund_score'] += 20
        elif de < 1.5:
            result['fund_score'] += 12
        elif de < 2.0:
            result['fund_score'] += 6
        else:
            result['fund_score'] += 0
    
    # ROE scoring
    if roe:
        if roe >= 15:
            result['fund_score'] += 25
        elif roe >= 10:
            result['fund_score'] += 18
        elif roe >= 5:
            result['fund_score'] += 10
        elif roe >= 0:
            result['fund_score'] += 5
    
    # P/B scoring (RE often trades below book value)
    if pb:
        if pb < 0.7:
            result['fund_score'] += 15
        elif pb < 1.0:
            result['fund_score'] += 10
        elif pb < 1.5:
            result['fund_score'] += 5
    
    # Inventory status - if available
    inventory_days = raw_data.get('inventory_days') or raw_data.get('inventory_turnover_days')
    if inventory_days:
        result['sector_metrics']['inventory_days'] = inventory_days
        if inventory_days < 365:
            result['fund_score'] += 15
        elif inventory_days < 730:
            result['fund_score'] += 8
        elif inventory_days < 1095:
            result['fund_score'] += 3
    
    # Land bank (pre-sales potential) - if available
    land_bank = raw_data.get('land_bank') or raw_data.get('unsold_inventory')
    if land_bank:
        result['sector_metrics']['land_bank'] = land_bank
        result['fund_score'] += 5  # Having land bank is positive
    
    # Cap at 100
    result['fund_score'] = min(result['fund_score'], 100)
    
    return result


def score_manufacturing_sector(raw_data: Dict[str, Any], symbol: str = "") -> Dict[str, Any]:
    """
    Score manufacturing sector stocks using Gross Margin, Inventory Turnover.
    Lower ROE threshold (10%) for capital-intensive sectors.
    
    ROBUST FALLBACK: If essential manufacturing data (Gross Margin) is missing,
    automatically falls back to general scoring.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # ROBUST FALLBACK: Check for essential manufacturing data
    has_gm = raw_data.get('gross_margin')
    
    if not has_gm:
        logger.warning(f"[Data Warning] Missing manufacturing metrics for {symbol or 'Unknown'}, falling back to General Score")
        result = score_general_sector(raw_data)
        result['fallback'] = True
        result['fallback_reason'] = 'Missing manufacturing metrics (Gross Margin)'
        return result
    
    result = {
        'fund_score': 0,
        'primary_metric': 'Gross Margin',
        'primary_value': raw_data.get('gross_margin'),
        'sector_metrics': {}
    }
    
    roe = raw_data.get('roe')
    gross_margin = raw_data.get('gross_margin')
    inventory_turnover = raw_data.get('inventory_turnover')
    pb = raw_data.get('pb')
    
    # Gross Margin scoring
    if gross_margin:
        result['sector_metrics']['gross_margin'] = gross_margin
        if gross_margin >= 30:
            result['fund_score'] += 25
        elif gross_margin >= 20:
            result['fund_score'] += 18
        elif gross_margin >= 10:
            result['fund_score'] += 10
        else:
            result['fund_score'] += 3
    
    # ROE scoring (lower threshold for capital-intensive)
    if roe:
        if roe >= 15:
            result['fund_score'] += 25
        elif roe >= 10:  # Lowered from 15%
            result['fund_score'] += 18
        elif roe >= 5:
            result['fund_score'] += 10
        elif roe >= 0:
            result['fund_score'] += 3
    
    # Inventory Turnover
    if inventory_turnover:
        result['sector_metrics']['inventory_turnover'] = inventory_turnover
        if inventory_turnover >= 6:
            result['fund_score'] += 20
        elif inventory_turnover >= 4:
            result['fund_score'] += 14
        elif inventory_turnover >= 2:
            result['fund_score'] += 8
        else:
            result['fund_score'] += 3
    
    # P/B scoring
    if pb:
        if pb < 1.0:
            result['fund_score'] += 15
        elif pb < 1.5:
            result['fund_score'] += 10
        elif pb < 2.0:
            result['fund_score'] += 5
    
    # Cap at 100
    result['fund_score'] = min(result['fund_score'], 100)
    
    return result


def score_retail_sector(raw_data: Dict[str, Any], symbol: str = "") -> Dict[str, Any]:
    """
    Score retail/consumer sector stocks.
    Focus on P/E, Revenue Growth, ROE.
    
    ROBUST FALLBACK: If essential retail data (P/E) is missing,
    automatically falls back to general scoring.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # ROBUST FALLBACK: Check for essential retail data
    has_pe = raw_data.get('pe')
    
    if not has_pe:
        logger.warning(f"[Data Warning] Missing retail metrics for {symbol or 'Unknown'}, falling back to General Score")
        result = score_general_sector(raw_data)
        result['fallback'] = True
        result['fallback_reason'] = 'Missing retail metrics (P/E)'
        return result
    
    result = {
        'fund_score': 0,
        'primary_metric': 'P/E',
        'primary_value': raw_data.get('pe'),
        'sector_metrics': {}
    }
    
    pe = raw_data.get('pe')
    roe = raw_data.get('roe')
    profit_growth = raw_data.get('profit_growth')
    
    # P/E scoring (important for growth sectors)
    if pe:
        if 5 <= pe <= 15:
            result['fund_score'] += 28
        elif 15 < pe <= 20:
            result['fund_score'] += 20
        elif 20 < pe <= 25:
            result['fund_score'] += 12
        elif pe < 5:
            result['fund_score'] += 18  # May indicate problems
        else:
            result['fund_score'] += 5
    
    # ROE scoring (standard threshold for consumer)
    if roe:
        if roe >= 20:
            result['fund_score'] += 25
        elif roe >= 15:
            result['fund_score'] += 20
        elif roe >= 10:
            result['fund_score'] += 12
        else:
            result['fund_score'] += 5
    
    # Profit Growth
    if profit_growth:
        result['sector_metrics']['profit_growth'] = profit_growth
        if profit_growth >= 20:
            result['fund_score'] += 22
        elif profit_growth >= 10:
            result['fund_score'] += 16
        elif profit_growth >= 0:
            result['fund_score'] += 8
    
    # P/B scoring
    pb = raw_data.get('pb')
    if pb:
        if pb < 3:
            result['fund_score'] += 15
        elif pb < 5:
            result['fund_score'] += 10
        else:
            result['fund_score'] += 3
    
    # Cap at 100
    result['fund_score'] = min(result['fund_score'], 100)
    
    return result


def score_general_sector(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Default scoring for sectors without specific rules.
    Uses P/E, P/B, ROE framework.
    """
    result = {
        'fund_score': 0,
        'primary_metric': 'P/E',
        'primary_value': raw_data.get('pe'),
        'sector_metrics': {}
    }
    
    pe = raw_data.get('pe')
    pb = raw_data.get('pb')
    roe = raw_data.get('roe')
    
    # P/E scoring
    if pe:
        if 5 <= pe <= 20:
            result['fund_score'] += 30
        elif 20 < pe <= 30:
            result['fund_score'] += 20
        elif pe < 5:
            result['fund_score'] += 15
        else:
            result['fund_score'] += 5
    
    # P/B scoring
    if pb:
        if pb < 1.5:
            result['fund_score'] += 25
        elif pb < 2.5:
            result['fund_score'] += 18
        elif pb < 4:
            result['fund_score'] += 10
        else:
            result['fund_score'] += 3
    
    # ROE scoring
    if roe:
        if roe >= 20:
            result['fund_score'] += 30
        elif roe >= 15:
            result['fund_score'] += 22
        elif roe >= 10:
            result['fund_score'] += 14
        elif roe >= 5:
            result['fund_score'] += 7
    
    # Cap at 100
    result['fund_score'] = min(result['fund_score'], 100)
    
    return result


# ============== INDUSTRY MEDIAN FALLBACK ==============

# Static median values for common sectors (Vietnam market)
SECTOR_MEDIAN_DEFAULTS = {
    'banking': {
        'nim': 3.5,        # Net Interest Margin %
        'npl': 2.0,        # Non-Performing Loans %
        'casa': 20.0,      # CASA ratio %
        'car': 12.0,       # Capital Adequacy Ratio %
        'roe': 18.0,       # Return on Equity %
        'pb': 1.5,         # Price/Book
    },
    'real_estate': {
        'debt_equity': 1.0,  # D/E ratio
        'roe': 12.0,
        'pb': 1.0,
        'inventory_days': 730,
    },
    'manufacturing': {
        'gross_margin': 20.0,   # Gross margin %
        'inventory_turnover': 5.0,
        'roe': 15.0,
        'pb': 1.5,
        'pe': 12.0,
    },
    'retail': {
        'profit_growth': 10.0,  # Profit growth %
        'roe': 18.0,
        'pb': 2.5,
        'pe': 15.0,
    },
    'general': {
        'roe': 15.0,
        'pb': 2.0,
        'pe': 12.0,
    }
}


def get_industry_median_values(sector: str) -> Dict[str, float]:
    """
    Lấy median values cho sector cụ thể từ database hoặc fallback to static values.
    
    Returns:
        Dict với các default values cho sector
    """
    # Ưu tiên 1: Try lấy từ database IndustryValuation
    try:
        from dashboard.models import IndustryValuation
        iv = IndustryValuation.objects.filter(
            name__icontains=sector,
            is_active=True
        ).first()
        
        if iv:
            db_values = {}
            if iv.median_pe and iv.median_pe > 0:
                db_values['pe'] = iv.median_pe
            if iv.median_pb and iv.median_pb > 0:
                db_values['pb'] = iv.median_pb
            if hasattr(iv, 'median_de') and iv.median_de and iv.median_de > 0:
                db_values['debt_equity'] = iv.median_de
            if db_values:
                # Merge with static defaults (DB values take priority)
                return {**SECTOR_MEDIAN_DEFAULTS.get(sector, SECTOR_MEDIAN_DEFAULTS['general']), **db_values}
    except Exception:
        pass
    
    # Ưu tiên 2: Return static defaults
    return SECTOR_MEDIAN_DEFAULTS.get(sector, SECTOR_MEDIAN_DEFAULTS['general'])


def apply_median_fallback(raw_data: Dict[str, Any], sector: str, symbol: str = "") -> Dict[str, Any]:
    """
    Áp dụng median fallback cho các trường thiếu dữ liệu.
    
    Thay vì chấm điểm 0 hoặc fallback sang general sector,
    ta lấy giá trị median ngành làm substitute.
    
    Args:
        raw_data: Dict financial metrics (sẽ được clone và modified)
        sector: Sector category
        symbol: Stock symbol for logging
    
    Returns:
        Modified raw_data với fallback values applied
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Clone để không modify original
    data = dict(raw_data)
    medians = get_industry_median_values(sector)
    fallback_applied = []
    
    # Banking specific fallbacks
    if sector == 'banking':
        if not data.get('nim') and not data.get('net_interest_margin'):
            data['nim'] = medians.get('nim')
            fallback_applied.append('nim')
        if not data.get('npl') and not data.get('npl_ratio'):
            data['npl'] = medians.get('npl')
            fallback_applied.append('npl')
        if not data.get('casa') and not data.get('casa_ratio'):
            data['casa'] = medians.get('casa')
            fallback_applied.append('casa')
        if not data.get('car') and not data.get('capital_adequacy_ratio'):
            data['car'] = medians.get('car')
            fallback_applied.append('car')
    
    # Real Estate specific fallbacks
    elif sector == 'real_estate':
        if not data.get('debt_equity') and not data.get('de'):
            data['debt_equity'] = medians.get('debt_equity')
            fallback_applied.append('debt_equity')
    
    # Manufacturing specific fallbacks
    elif sector == 'manufacturing':
        if not data.get('gross_margin'):
            data['gross_margin'] = medians.get('gross_margin')
            fallback_applied.append('gross_margin')
    
    # Log warning if fallbacks applied
    if fallback_applied and symbol:
        logger.warning(f"[Data Fallback] {symbol} ({sector}): Applied median for {fallback_applied}")
    
    # Attach fallback info
    data['_fallback_applied'] = fallback_applied
    
    return data


def score_by_sector(raw_data: Dict[str, Any], industry: str = "", symbol: str = "") -> Dict[str, Any]:
    """
    Main entry point for sector-specific scoring.
    Routes to appropriate scoring function based on industry.
    
    MEDIAN FALLBACK v2: Nếu dữ liệu ngành thiếu, áp dụng median fallback
    thay vì fallback sang general sector scoring.
    
    Args:
        raw_data: Dict containing financial metrics
        industry: Industry name for sector classification
        symbol: Stock symbol for logging purposes
    """
    sector = get_sector_category(industry)
    
    # FIX v2: Apply median fallback BEFORE scoring
    # Đảm bảo các chỉ số ngành có giá trị (median) thay vì None/0
    enriched_data = apply_median_fallback(raw_data, sector, symbol)
    
    if sector == 'banking':
        return score_banking_sector(enriched_data, symbol)
    elif sector == 'real_estate':
        return score_real_estate_sector(enriched_data, symbol)
    elif sector == 'manufacturing':
        return score_manufacturing_sector(enriched_data, symbol)
    elif sector == 'retail':
        return score_retail_sector(enriched_data, symbol)
    else:
        return score_general_sector(enriched_data)


def get_sector_median_de(industry: str = "") -> float:
    """
    Get sector median Debt/Equity ratio from IndustryValuation model.
    Used for RELATIVE VETO logic for Real Estate.
    
    Returns:
        float: Sector median D/E ratio (default 1.0 if not found)
    """
    try:
        from dashboard.models import IndustryValuation
        # Try to find Real Estate industry valuation
        industry_key = "Real Estate"
        iv = IndustryValuation.objects.filter(
            name__icontains=industry_key,
            is_active=True
        ).first()
        
        if iv and hasattr(iv, 'median_de') and iv.median_de and iv.median_de > 0:
            return float(iv.median_de)
    except Exception:
        pass
    
    # Fallback: Return typical RE median DE for Vietnam market
    return 1.0  # Vietnam RE typically has DE around 1.0-1.5


# ============== HEALTH VETO CHECK (13 RULES) ==============
def check_health_veto(
    tech: Dict[str, Any],
    fund_data: Dict[str, Any],
    market_rsi: float = 50.0,
    df: pd.DataFrame = None,
    avg_volume_value: float = 0.0,
    industry: str = "",
    scan_mode: str = "EARLY_TREND"
) -> Dict[str, Any]:
    """Kiểm tra VETO dựa trên bộ lọc 4 nhóm (KHÔNG bao gồm R:R hay Định giá)

    BỘ LỌC "SĂN ĐÁY & CHÂN SÓNG":
    - Nhóm 1: Dòng tiền & chặn đỉnh ngắn hạn
    - Nhóm 2: Neo dài hạn + lọc volume dưới SMA50
    - Nhóm 3: Sức khỏe tài chính
    - Nhóm 4: Thị trường

    Args:
        tech: Dict chỉ số kỹ thuật (price, cmf, rsi, adx, sma_50, sma_200, bb_percent, volume_ratio, v.v.)
        fund_data: Dict dữ liệu cơ bản (roe, pe, pb, f_score, profit_growth, v.v.)
        market_rsi: RSI thị trường chung
        df: DataFrame giá để tính volume TB 20 phiên
        avg_volume_value: Giá trị volume TB quy đổi sang tỷ đồng
        industry: Ngành của cổ phiếu (để xác định sector-adaptive rules)

    Returns:
        Dict: is_vetoed (bool), veto_reason (str), veto_reasons (list)
    """
    veto_reasons = []
    sector = get_sector_category(industry)

    # Determine capital-intensive flag for ROE threshold
    is_capital_intensive = sector in ['manufacturing', 'real_estate']
    roe_threshold = 10 if is_capital_intensive else 15

    price_val = tech.get('price', 0)
    sma_50_val = tech.get('sma_50', 0)
    sma_200_val = tech.get('sma_200', 0)
    rsi_val = tech.get('rsi', 50)
    bb_percent_val = tech.get('bb_percent', 50)
    volume_ratio_val = tech.get('volume_ratio', 1.0)

    # ===== NHÓM 1: DÒNG TIỀN & PHỦ QUYẾT ĐỈNH NGẮN HẠN =====
    # VETO_1: CMF < 0
    if tech.get('cmf', 0) < 0:
        veto_reasons.append(f"VETO_1: CMF < 0 ({tech.get('cmf', 0):.2f})")
    # VETO_2: Volume TB 20 phiên < 15 tỷ
    if avg_volume_value > 0 and avg_volume_value < 15:
        veto_reasons.append(f"VETO_2: VolTB20 < 15B ({avg_volume_value:.1f}B)")
    elif avg_volume_value == 0:
        # Nếu thiếu df, ước tính từ volume trong tech
        actual_price = price_val * 1000 if (0 < price_val < 1000) else price_val
        tech_vol = tech.get('volume', 0)
        if tech_vol > 0 and actual_price > 0:
            est_val = (actual_price * tech_vol) / 1e9
            if est_val < 15:
                veto_reasons.append(f"VETO_2: VolTB20 < 15B (~{est_val:.1f}B)")
    # VETO_3: Volume_Ratio < 0.5 - chỉ áp dụng cho EARLY_TREND; BOTTOM_FISHING cho phép volume cạn kiệt
    if scan_mode != "BOTTOM_FISHING" and volume_ratio_val < 0.5:
        veto_reasons.append(f"VETO_3: VolRatio < 0.5 ({volume_ratio_val:.2f})")
    # VETO_4: Anti-FOMO - RSI quá cao (chỉ BOTTOM_FISHING)
    # EARLY_TREND: breakout hợp lệ sẽ tự nhiên có RSI cao -> không VETO cứng ở Layer 1
    if scan_mode == "BOTTOM_FISHING" and rsi_val > 70:
        veto_reasons.append(f"VETO_4: Anti-FOMO RSI > 70 ({rsi_val:.1f})")
    # VETO_5: Anti-FOMO - BB% quá cao (chỉ BOTTOM_FISHING)
    if scan_mode == "BOTTOM_FISHING" and bb_percent_val > 95:
        veto_reasons.append(f"VETO_5: Anti-FOMO BB% > 95 ({bb_percent_val:.1f})")

    # ===== NHÓM 2: NEO DÀI HẠN & LỌC VOLUME DƯỚI SMA50 =====
    # VETO_6: Giá dưới SMA200 -> xu hướng dài hạn gãy
    if price_val > 0 and sma_200_val > 0 and price_val < sma_200_val:
        veto_reasons.append("VETO_6: Giá < SMA200 (Xu hướng dài hạn gãy)")

    # VETO_7: Dưới SMA50 nhưng volume còn lớn -> rơi tự do chưa kết thúc
    if price_val > 0 and sma_50_val > 0 and price_val < sma_50_val:
        if volume_ratio_val > 1.2:
            veto_reasons.append(f"VETO_7: Giá < SMA50 + VolRatio {volume_ratio_val:.2f} (Rơi tự do)")
        # Nếu volume_ratio < 0.8: xác nhận cạn cung -> cho phép tiếp
        # Còn lại 0.8-1.2: trung tính -> không VETO

    # VETO_8: ADX quá thấp
    if tech.get('adx', 25) < 20:
        veto_reasons.append(f"VETO_8: ADX < 20 ({tech.get('adx', 0):.1f})")

    # VETO_9: Foreign Distribution Trap (EARLY_TREND only)
    # Breakout kèm khối ngoại bán ròng khốc liệt -> Bulltrap của đội lái trong nước
    if scan_mode == "EARLY_TREND":
        latest_net_val = fund_data.get('latest_net_val', 0.0)
        absorption = fund_data.get('foreign_absorption_ratio', 0.0)
        breakout_signal = (
            tech.get('price', 0) > tech.get('sma_10', 0) and
            tech.get('price', 0) > tech.get('sma_20', 0) and
            tech.get('volume_ratio', 1.0) > 1.5
        )
        if breakout_signal and latest_net_val < 0 and absorption > 25:
            veto_reasons.append(
                f"VETO_9: Foreign Dist. Trap (net={latest_net_val/1e9:.2f}B, abs={absorption:.1f}%)"
            )

    # ===== NHÓM 3: SỨC KHỎE TÀI CHÍNH (ĐÃ SỬA THÀNH CÁC LỆNH IF ĐỘC LẬP) =====
    # Luật 1: Kiểm tra tỷ lệ nợ theo đặc thù ngành
    if sector == 'real_estate':
        de = fund_data.get('debt_equity') or fund_data.get('de') or 0
        if de > 0:
            sector_median_de = get_sector_median_de(industry)
            relative_threshold = sector_median_de * 1.2
            if de > relative_threshold:
                veto_reasons.append(f"VETO_14: RE D/E > {relative_threshold:.2f} (sector median: {sector_median_de:.2f})")
    elif sector != 'banking':
        de = fund_data.get('debt_equity') or fund_data.get('de') or 0
        if de > 1.5:
            veto_reasons.append(f"VETO_15: D/E > 1.5 ({de:.2f})")
    elif sector == 'banking':
        npl = fund_data.get('npl') or fund_data.get('npl_ratio') or 0
        if npl > 3:
            veto_reasons.append(f"VETO_15: NPL > 3% ({npl:.2f}%)")

    # Luật 2: Ép kiểm tra ROE độc lập cho TẤT CẢ các ngành
    if fund_data.get('roe') is not None:
        roe_val = fund_data['roe']
        if roe_val < roe_threshold:
            threshold_note = "10%" if is_capital_intensive else "15%"
            veto_reasons.append(f"VETO_9: ROE < {threshold_note} ({roe_val:.1f}%)")

    # Luật 3: Ép kiểm tra F-Score độc lập cho TẤT CẢ các ngành
    # Chỉ VETO khi F-Score đã được tính toán thực tế (> 0) và < 5
    # Nếu f_score == 0 do thiếu BCTC lịch sử, KHÔNG kích hoạt VETO_10 cứng
    f_score_val = fund_data.get('f_score')
    if f_score_val is not None and 0 < f_score_val < 5:
        veto_reasons.append(f"VETO_10: F-Score < 5 ({f_score_val}/9)")

    # Luật 4: Ép kiểm tra Tăng trưởng lợi nhuận độc lập
    if not fund_data.get('is_new_listing', False):
        pg = fund_data.get('profit_growth')
        if pg is not None and pg < 0:
            veto_reasons.append(f"VETO_11: ProfitGrowth < 0 ({pg:.1f}%)")

    # VETO_12: Thiếu dữ liệu tài chính (chỉ veto khi hoàn toàn không có dữ liệu tài chính nào)
    has_pe = fund_data.get('pe') is not None
    has_pb = fund_data.get('pb') is not None
    has_roe = fund_data.get('roe') is not None
    if not (has_pe or has_pb or has_roe):
        veto_reasons.append("VETO_12: Thiếu dữ liệu tài chính")

    # ===== NHÓM 4: THỊ TRƯỜNG =====
    # VETO_13: VNIndex RSI > 80
    if market_rsi > 80:
        veto_reasons.append(f"VETO_13: Market RSI > 80 ({market_rsi:.1f})")

    # ===== KẾT QUẢ =====
    is_vetoed = len(veto_reasons) > 0
    veto_reason = "; ".join(veto_reasons) if veto_reasons else ""

    return {
        "is_vetoed": is_vetoed,
        "veto_reason": veto_reason,
        "veto_reasons": veto_reasons,
        "sector": sector,
        "roe_threshold_used": roe_threshold
    }


# ============== CORE LOGIC ENGINE (SHARED) ==============
# Hàm thuần túy - KHÔNG gọi API, chỉ tính toán từ dữ liệu đầu vào
# Dùng chung cho cả Live scan và Backtest

def compute_core_logic(
    symbol: str,
    tech: Dict[str, Any],
    fund_data: Dict[str, Any],
    market_rsi: float = 50.0,
    market_group: str = "UNKNOWN",
    df: pd.DataFrame = None,
    quarterly_data: Optional[Dict[str, Dict[str, Any]]] = None,
    date_str: Optional[str] = None,
    account_balance: float = 100_000_000,
    risk_tolerance_pct: float = 2.0,
    scan_mode: str = "EARLY_TREND",
) -> Dict[str, Any]:
    """
    PURE FUNCTION - Engine tính toán trung tâm
    Nhận dữ liệu thô và trả về kết quả phân tích đầy đủ

    ARCHITECTURE: 4-Layer Pipeline
        Layer 1 - Gatekeepers (VETO): Early exit if stock violates hard rules
        Layer 2 - Accelerators (Technical Score): Momentum-based scoring
        Layer 3 - Timers (Entry Quality): RSI/BB-based entry classification
        Layer 4 - Anchors (Fair Value & Risk Management): FV/SL/TP/Signal/Position sizing

    Args:
        symbol: Mã cổ phiếu
        tech: Dict chứa indicators (price, rsi, cmf, adx, sma_50, sma_200, v.v.)
        fund_data: Dict chứa dữ liệu tài chính (roe, pe, pb, f_score, v.v.)
        market_rsi: RSI của VNIndex tại thời điểm tính
        market_group: Nhóm thị trường (VN30, MIDCAP, SMALL)
        df: DataFrame OHLCV (tùy chọn, để tính avg_volume_value)
        quarterly_data: Dict quarter -> {roe, f_score} cho backtest
        date_str: Ngày tính (format YYYY-MM-DD) để lookup quarterly data
        account_balance: Số dư tài khoản (VND) để tính position sizing
        risk_tolerance_pct: % rủi ro chấp nhận cho mỗi lệnh
        scan_mode: Chế độ quét ("BOTTOM_FISHING" | "EARLY_TREND")
    """
    # ========== GET QUARTERLY DATA IF AVAILABLE (FOR BACKTEST) ==========
    roe_val = fund_data.get('roe')
    f_score_val = fund_data.get('f_score', 0)

    if quarterly_data and date_str:
        # Parse quarter from date
        try:
            from datetime import datetime as dt
            dt_obj = dt.strptime(date_str, '%Y-%m-%d')
            quarter = f"{dt_obj.year}-Q{(dt_obj.month - 1) // 3 + 1}"
            if quarter in quarterly_data:
                qd = quarterly_data[quarter]
                roe_val = qd.get('roe') or roe_val
                f_score_val = qd.get('f_score') or f_score_val
        except:
            pass

    # ========== COMMON INPUTS (used across all layers) ==========
    price_val = tech.get("price", 0)
    rsi_val = tech.get("rsi", 50)
    cmf_val = tech.get("cmf", 0)
    volume_ratio_val = tech.get("volume_ratio", 1.0)
    adx_val = tech.get("adx", 25)
    vwap_val = tech.get('vwap', price_val)
    vwap_status_val = tech.get("vwap_status", "neutral")
    sma_10_val = tech.get("sma_10", 0)
    sma_20_val = tech.get("sma_20", 0)
    sma_50_val = tech.get("sma_50", 0)
    sma_200_val = tech.get("sma_200", 0)
    sma20_val_t = tech.get("sma_20", price_val)
    macd_val = tech.get("macd", 0)
    macd_signal_val = tech.get("macd_signal", 0)
    ichimoku_status_val = tech.get("ichimoku_status", "neutral")
    supertrend_signal_val = tech.get("supertrend_signal", "neutral")
    bb_percent_val = tech.get("bb_percent", 50)
    bb_upper_val = tech.get("bb_upper", 0)
    bb_middle_val = tech.get("bb_middle", 0)
    bb_lower_val = tech.get("bb_lower", 0)
    entry = tech.get("price", 0)
    target_yield_pct = 0.0
    scan_mode = (scan_mode or "EARLY_TREND").upper()

    # Industry config
    industry = fund_data.get('industry', 'Default')
    industry_key = next((k for k in INDUSTRY_CONFIG if k.lower() in industry.lower()), 'Default')
    sector = get_sector_category(industry)
    sector_group = get_sector_group(industry, sector)

    # Avg volume value (used by VETO) - Giá trị giao dịch trung bình 20 phiên (tỷ đồng)
    avg_volume_value = 0.0
    actual_price = price_val * 1000 if (0 < price_val < 1000) else price_val
    if df is not None and 'volume' in df.columns and len(df) > 0 and actual_price > 0:
        mean_vol20 = float(df['volume'].tail(20).mean())
        avg_volume_value = round((actual_price * mean_vol20) / 1e9, 2)
    elif actual_price > 0 and tech.get('volume', 0) > 0:
        avg_volume_value = round((actual_price * tech.get('volume', 0)) / 1e9, 2)

    # ============================================================
    # LAYER 1: THE GATEKEEPERS (VETO)
    # Move ALL veto logic to the VERY TOP. Simplified veto rules:
    #   - VolTB20 < 15B
    #   - Price < SMA50
    #   - Ichimoku Bearish
    #   - Banking: NPL > 3%
    #   - Non-banking: D/E > 1.5
    # If vetoed: immediately return a standardized veto response.
    # ============================================================
    health_result = check_health_veto(
        tech=tech,
        fund_data=fund_data,
        market_rsi=market_rsi,
        df=df,
        avg_volume_value=avg_volume_value,
        industry=industry,
        scan_mode=scan_mode
    )

    is_vetoed = bool(health_result.get("is_vetoed", False))
    veto_reason = health_result.get("veto_reason", "")
    if is_vetoed:
        support_price = sma_50_val if sma_50_val > 0 else entry * 0.97

    # ============================================================
    # LAYER 2: THE ACCELERATORS (TECHNICAL SCORE)
    # Spec: điểm nền 0, trần 100, tổng 5 mục = 30 + 30 + 20 + 20.
    # ============================================================
    tech_score = 0

    # --- 1. Xu hướng & Động lực (tối đa 30) ---
    if adx_val > 25:
        tech_score += 15
    elif 20 <= adx_val <= 25:
        tech_score += 8

    if sma_10_val > 0 and sma_20_val > 0 and price_val > sma_10_val > sma_20_val:
        tech_score += 15

    if scan_mode == "EARLY_TREND" and adx_val < 20:
        tech_score -= 10
    elif scan_mode == "BOTTOM_FISHING" and adx_val < 20 and volume_ratio_val < 0.7 and cmf_val > 0:
        tech_score += 10

    # --- 2. Xung lực dòng tiền nội tại (tối đa 30) ---
    if cmf_val > 0.1:
        tech_score += 15
    elif 0 <= cmf_val <= 0.1:
        tech_score += 8

    mfi_val = tech.get("mfi", 50) or 50
    if mfi_val > 50:
        tech_score += 15

    if cmf_val < 0:
        tech_score -= 15

    # Fast pick flag (giữ logic cũ cho UI)
    is_fast_pick = adx_val > 18 and volume_ratio_val > 0.8

    # --- 3. Tín hiệu kích hoạt xu hướng (tối đa 20) ---
    if macd_val > macd_signal_val:
        tech_score += 10
    if ichimoku_status_val == "bullish" or supertrend_signal_val == "bullish":
        tech_score += 10
    if macd_val < macd_signal_val:
        tech_score -= 10

    # --- 4. Thanh khoản đột biến (tối đa 20) ---
    if volume_ratio_val > 1.5:
        tech_score += 20
    elif 1.0 <= volume_ratio_val <= 1.5:
        tech_score += 10
    if scan_mode == "EARLY_TREND" and volume_ratio_val < 0.5:
        tech_score -= 10

    # --- 5. Bộ phanh hạ nhiệt kỹ thuật (trừ trực tiếp) ---
    if rsi_val > 80:
        tech_score -= 15
    if bb_percent_val > 100:
        tech_score -= 10

    tech_score = max(0, min(100, tech_score))

    # ============================================================
    # SCAN MODE SCORING (Layer 2/3 extension)
    # ============================================================
    price_to_vwap_pct = ((price_val - vwap_val) / vwap_val * 100) if vwap_val > 0 else 0
    price_to_sma20_pct = ((price_val - sma20_val_t) / sma20_val_t * 100) if sma20_val_t > 0 else 0
    breakout_signal = price_val > sma_10_val and price_val > sma_20_val and volume_ratio_val > 1.5
    is_bottom_setup = 35 <= rsi_val <= 45 and volume_ratio_val < 0.8 and abs(price_to_vwap_pct) <= 1.5

    # ============================================================
    # SECTOR-AWARE TECH SCORING (Layer 2 extension)
    # Spec không yêu cầu cộng/trừ thêm theo sector trong tech_score
    # (sector được xử lý qua Relative Strength ở Layer Master).
    # ============================================================

    # ============================================================
    # LAYER 3: THE TIMERS (ENTRY QUALITY)
    # entry_quality: "GOOD" / "BAD" / "ACCUMULATE"
    # is_safe_entry: distance to SMA20 <= 2%
    # ============================================================
    if scan_mode == "BOTTOM_FISHING":
        # EXCELLENT: Khối ngoại gom âm thầm >= 3 phiên liên tiếp (vùng đáy Shark accumulation)
        foreign_streak = fund_data.get('foreign_buy_streak', 0)
        if foreign_streak >= 3 and volume_ratio_val < 0.7:
            entry_quality = "EXCELLENT"
            entry_quality_reason = f"VÙNG GOM SHARK: Foreign streak {foreign_streak} phiên + volume cạn"
        elif is_bottom_setup or (35 <= rsi_val <= 45 and volume_ratio_val < 1.0):
            entry_quality = "ACCUMULATE"
            entry_quality_reason = "ZONE ĐÁY: Volume cạn + thắt nút cổ chai"
        elif rsi_val > 70 or bb_percent_val > 95:
            entry_quality = "BAD"
            entry_quality_reason = "Anti-FOMO: RSI/BB% quá cao"
        else:
            entry_quality = "GOOD"
            entry_quality_reason = "Vùng giá tích lũy có xác nhận"
    elif scan_mode == "EARLY_TREND":
        # Ưu tiên breakout trước RSI>70 (breakout hợp lệ không bị chặn bởi RSI cao)
        if breakout_signal:
            entry_quality = "GOOD"
            entry_quality_reason = "Chân sóng: Breakout SMA10/20 + volume xác nhận"
        elif rsi_val < 35 or bb_percent_val < -5:
            entry_quality = "ACCUMULATE"
            entry_quality_reason = "Giá quá bán - chờ xác nhận hồi phục"
        elif rsi_val > 70 or bb_percent_val > 95:
            entry_quality = "BAD"
            entry_quality_reason = "Anti-FOMO: RSI/BB% quá cao"
        else:
            entry_quality = "GOOD"
            entry_quality_reason = "Vùng giá hợp lý"
    else:
        if rsi_val > 75 or bb_percent_val > 105:
            entry_quality = "BAD"
            entry_quality_reason = "FOMO zone (RSI > 75 hoặc BB% > 105)"
        elif rsi_val < 35 or bb_percent_val < -5:
            entry_quality = "ACCUMULATE"
            entry_quality_reason = "Panic selling (RSI < 35 hoặc BB% < -5)"
        else:
            entry_quality = "GOOD"
            entry_quality_reason = "Vùng giá hợp lý"

    # is_safe_entry: distance to SMA20 <= 2%
    safe_entry_distance = 0
    if sma_20_val > 0 and price_val > 0:
        safe_entry_distance = ((price_val - sma_20_val) / sma_20_val) * 100
    is_safe_entry = abs(safe_entry_distance) <= 2

    # ============================================================
    # LAYER 4: THE ANCHORS (FAIR VALUE & RISK MANAGEMENT)
    # ============================================================

    # ---- 4a. Fair Value (FV) calculations FIRST ----
    sma20_val_t = tech.get('sma_20', price_val)

    # FV Daily: (VWAP * 0.4) + (SMA20 * 0.6)
    fv_daily = round((vwap_val * 0.4) + (sma20_val_t * 0.6), 2)

    # Get dynamic sector valuation (Median-based với Wealth Guard Cap)
    actual_pe = fund_data.get('pe') or 0
    val_config = get_target_valuation(industry_key)
    target_pe = val_config['target']
    pe_valuation = price_val * (target_pe / actual_pe) if actual_pe > 0 else price_val
    valuation_source = val_config['source']
    valuation_cap_applied = val_config['cap_applied']
    sector_median_pe = val_config['dynamic']

    # Valuation source info
    valuation_source = val_config['source']
    valuation_cap_applied = val_config['cap_applied']
    sector_median_pe = val_config['dynamic']

    # ---- 4b. Trading levels: SL/TP/Support ----
    # Support = min(SMA50, 20-day low)
    sma_50_support = tech.get("sma_50", 0)
    low_20_val = 0
    if df is not None and 'low' in df.columns and len(df) >= 20:
        low_20_val = df['low'].tail(20).min()

    if sma_50_support > 0 and low_20_val > 0:
        support_price = min(sma_50_support, low_20_val)
    elif low_20_val > 0:
        support_price = low_20_val
    elif sma_50_support > 0:
        support_price = sma_50_support
    else:
        support_price = entry * 0.97

    hard_risk = entry - support_price
    hard_risk_pct = (hard_risk / entry) * 100 if entry > 0 else 3

    # ATR baseline (used for new SL formula)
    atr_value = tech.get("atr", 0) if tech.get("atr", 0) > 0 else entry * 0.02

    # Scan-mode-aware Stop Loss (Layer 4 refined)
    low_10_val = 0
    breakout_candle_low = support_price
    has_volume_breakout = False

    if df is not None and 'low' in df.columns and len(df) >= 20:
        low_10_val = df['low'].tail(10).min()

        # Breakout detector: price above SMA10 + SMA20 with volume spike
        sma_10_series = df['close'].rolling(10).mean()
        sma_20_series = df['close'].rolling(20).mean()
        avg_vol_20 = df['volume'].rolling(20).mean()

        price_above_sma10 = float(sma_10_series.iloc[-1] or 0) > 0 and price_val > sma_10_series.iloc[-1]
        price_above_sma20 = float(sma_20_series.iloc[-1] or 0) > 0 and price_val > sma_20_series.iloc[-1]
        latest_vol = float(df['volume'].iloc[-1] or 0)
        avg_vol = float(avg_vol_20.iloc[-1] or 0)
        vol_breakout = avg_vol > 0 and latest_vol > avg_vol * 1.5

        if price_above_sma10 and price_above_sma20 and vol_breakout:
            has_volume_breakout = True

            breakout_start = max(0, len(df) - 10)
            breakout_idx = None
            for i in range(breakout_start, len(df)):
                close_i = float(df['close'].iloc[i])
                sma10_i = float(sma_10_series.iloc[i] or 0)
                vol_i = float(df['volume'].iloc[i] or 0)
                avg_i = float(avg_vol_20.iloc[i] or 0)
                if close_i > sma10_i and avg_i > 0 and vol_i > avg_i * 1.5:
                    breakout_idx = i

            if breakout_idx is not None:
                breakout_candle_low = float(df['low'].iloc[breakout_idx])

    if scan_mode == "BOTTOM_FISHING" or not has_volume_breakout:
        accumulation_sl = round((low_10_val - 1.5 * atr_value), 2) if low_10_val > 0 else round(entry * 0.97, 2)
        stop_loss = accumulation_sl
    else:
        breakout_sl = round(max(breakout_candle_low, price_val * 0.95), 2)
        stop_loss = breakout_sl

    # ===== MINIMUM RISK BUFFER (3%) =====
    risk_percent = (entry - stop_loss) / entry if entry > 0 else 0
    if risk_percent < 0.03:
        stop_loss = round(entry * 0.96, 2)  # 4% risk

    # Inverted SL check
    has_inverted_sl = stop_loss >= entry

    # Take profit = Entry + 2*ATR (short-term momentum-based, no fundamental bias)
    take_profit = round(entry + 2 * atr_value, 2)

    # Trailing SL = 5% below current price
    trailing_sl = round(price_val * 0.95, 2)

    # ============================================================
    # SECTOR-AWARE EXIT RULES (Layer 4 extension)
    # ============================================================
    early_exit_trigger_pct = 2.0
    early_exit_drop_pct = 0.7

    if sector_group == 'cyclical':
        # Tài sản/Chu kỳ: bán sớm khi BB breakout quá mức hoặc RSI xâm nhập 80
        if bb_percent_val > 105 or rsi_val >= 80:
            early_exit_trigger_pct = 1.5
            early_exit_drop_pct = 0.5
        else:
            early_exit_trigger_pct = 2.0
            early_exit_drop_pct = 0.7
    elif sector_group == 'banking':
        # Banking: xuất hiện khi MACD Histogram đảo chiều hoặc giá cắt dưới SMA5 ở vùng cao
        if (macd_val < macd_signal_val and price_val > sma_20_val) or (sma_10_val > 0 and price_val < sma_10_val and rsi_val > 65):
            early_exit_trigger_pct = 1.8
            early_exit_drop_pct = 0.6
        else:
            early_exit_trigger_pct = 2.0
            early_exit_drop_pct = 0.8
    elif sector_group == 'growth_defensive':
        # Growth/Defensive: trailing theo xu hướng ngắn hạn, bắt đầu khi Price < SMA10
        if sma_10_val > 0 and price_val < sma_10_val:
            early_exit_trigger_pct = 1.5
            early_exit_drop_pct = 0.7
        else:
            early_exit_trigger_pct = 2.0
            early_exit_drop_pct = 0.7
    else:
        early_exit_trigger_pct = 2.0
        early_exit_drop_pct = 0.7

    # ===== LAYER 4 EXIT SENSOR: FOREIGN DISTRIBUTION WARNING =====
    # Nếu giá tiến sát fv_daily mà khối ngoại quay xe bán ròng liên tiếp 2 phiên
    # -> Siết early_exit_drop_pct để bám đuổi sát đỉnh
    if fv_daily > 0 and entry > 0:
        price_to_fv_pct = ((fv_daily - entry) / entry) * 100

        latest_net = fund_data.get('latest_net_val', 0.0)
        prev_net = fund_data.get('latest_net_val_2', 0.0)

        # Foreign selling 2 phiên liên tiếp + giá đang tiến về fv_daily target
        if latest_net < 0 and prev_net < 0 and price_to_fv_pct >= 70:
            early_exit_trigger_pct = 1.5
            early_exit_drop_pct = 0.3  # Siết từ 0.7 -> 0.3


    # Recalculate R:R with final stop loss
    risk = entry - stop_loss
    is_inverted_risk = False
    if risk > 0:
        rr_ratio = round((take_profit - entry) / risk, 2)
    else:
        rr_ratio = 0
        is_inverted_risk = True

    # ---- 4c. Target Yield & Est. Days (recalculated with final TP) ----
    target_yield_pct = round((take_profit - entry) / entry * 100, 2) if entry > 0 else 0

    # ============================================================
    # SCAN MODE SCORING (Layer 2/3 extension)
    # Moved here so yield-based rules use the real target_yield_pct.
    # ============================================================
    if scan_mode == "BOTTOM_FISHING":
        if volume_ratio_val < 0.7:
            tech_score += 12
        if 35 <= rsi_val <= 45:
            tech_score += 10
        if abs(price_to_vwap_pct) <= 1.5 or abs(price_to_sma20_pct) <= 1.5:
            tech_score += 10
        if rsi_val > tech.get("rsi_previous", rsi_val):
            tech_score += 8
        if is_bottom_setup:
            tech_score += 5
    elif scan_mode == "EARLY_TREND":
        if breakout_signal:
            tech_score += 18
        if target_yield_pct < 10:
            tech_score -= 25
        # NOTE: Theo spec mới, các bonus liên quan foreign flow (absorption,
        # trading_share, sponsor, distributing, streak) KHÔNG được cộng vào
        # tech_score. Tác động khối ngoại được áp dụng thống nhất tại
        # Master Score (Foreign Flow Modifier -25..+30).

    # Clamp tech_score theo trần 0..100 sau mọi điều chỉnh scan_mode
    tech_score = max(0, min(100, tech_score))

    # Trend Factor dựa trên ADX
    if adx_val > 25:
        trend_factor = 0.8
    elif adx_val < 20:
        trend_factor = 0.4
    else:
        trend_factor = 0.6

    # Est. Days dựa trên upside thực tế, không triệt tiêu ATR nữa.
    upside_pct = ((take_profit - entry) / entry) if entry > 0 else 0
    if upside_pct > 0:
        est_days = upside_pct / (abs(trend_factor - 1.0) + 0.01)
    else:
        est_days = 30 if atr_value > 0 else 10
    est_days = min(max(est_days, 1), 30)
    est_days_rounded = round(est_days)

    # Timeframe Label
    if est_days <= 3:
        timeframe_label = f"Fast T+ ({est_days_rounded}d)"
        timeframe_color = "emerald"
    elif est_days <= 7:
        timeframe_label = f"Swing ({est_days_rounded}d)"
        timeframe_color = "emerald"
    elif est_days <= 15:
        timeframe_label = f"Swing ({est_days_rounded}d)"
        timeframe_color = "sky"
    else:
        timeframe_label = f"Position ({est_days_rounded}d+)"
        timeframe_color = "amber"

    profit_per_day = round(target_yield_pct / est_days, 2) if est_days > 0 else 0

    # ============================================================
    # MARKET REGIME FILTER
    # Moved to BEFORE position sizing so market_position_scale applies correctly.
    # ============================================================
    if market_rsi > 80:
        market_regime = "FREEZE"
        market_regime_label = "Đóng băng"
        market_regime_icon = "❄️"
        market_regime_color = "red"
        market_veto_boost = True
        market_position_scale = 0.0
        market_tp_scale = 0.85
    elif market_rsi > 70:
        market_regime = "DEFENSE"
        market_regime_label = "Phòng thủ"
        market_regime_icon = "🛡️"
        market_regime_color = "amber"
        market_veto_boost = True
        market_position_scale = 0.5
        market_tp_scale = 0.9
    elif 40 <= market_rsi <= 65:
        market_regime = "NORMAL"
        market_regime_label = "Thuận lợi"
        market_regime_icon = "🌤️"
        market_regime_color = "emerald"
        market_veto_boost = False
        market_position_scale = 1.0
        market_tp_scale = 1.0
    elif market_rsi < 40:
        market_regime = "NORMAL"
        market_regime_label = "Thuận lợi"
        market_regime_icon = "🌤️"
        market_regime_color = "emerald"
        market_veto_boost = False
        market_position_scale = 1.0
        market_tp_scale = 1.0
    else:
        market_regime = "NORMAL"
        market_regime_label = "Trung tính"
        market_regime_icon = "☁️"
        market_regime_color = "sky"
        market_veto_boost = False
        market_position_scale = 1.0
        market_tp_scale = 1.0

    # ---- 4d. Position sizing ----
    atr_risk = max(atr_value * 2, entry * 0.01)
    regime_position_scale = market_position_scale if 'market_position_scale' in dir() else 1.0
    if regime_position_scale is None:
        regime_position_scale = 1.0
    if sector_group == 'cyclical':
        sector_position_scale = 0.9
    elif sector_group == 'banking':
        sector_position_scale = 0.85
    elif sector_group == 'growth_defensive':
        sector_position_scale = 1.0
    else:
        sector_position_scale = 1.0
    position_scale = regime_position_scale * sector_position_scale
    if entry > 0 and atr_risk > 0:
        optimal_position_size = (account_balance * (risk_tolerance_pct / 100)) / atr_risk
        optimal_position_size = optimal_position_size * entry * position_scale
    else:
        optimal_position_size = 0
    optimal_position_size = max(0, round(optimal_position_size, -3))

    # ============================================================
    # POST-LAYER-4 PROCESSING (preserve all original behavior)
    # ============================================================

    # ========== HIGH RESISTANCE (legacy from tech_score) ==========
    has_high_resistance = False
    if bb_upper_val > 0 and take_profit > bb_upper_val:
        has_high_resistance = True

    # ========== CRITERIA ==========
    criteria = []
    criteria_names = []

    # RSI Sweet Spot
    if 50 <= rsi_val <= 65:
        criteria.append("RSI Sweet Spot")
        criteria_names.append("RSI")
    # ADX Strong
    if adx_val > 20:
        criteria.append("ADX Strong")
        criteria_names.append("ADX")
    # DI Bullish
    if tech.get("plus_di", 0) > tech.get("minus_di", 0):
        criteria.append("DI Bullish")
        criteria_names.append("DI+")
    # CMF Positive
    if cmf_val > 0:
        criteria.append("CMF Positive")
        criteria_names.append("CMF")
    # Volume Active
    if volume_ratio_val > 1.0:
        criteria.append("Volume Active")
        criteria_names.append("Vol")
    # Above SMA20
    if sma_20_val > 0 and price_val > sma_20_val:
        criteria.append("Above SMA20")
        criteria_names.append("SMA20")
    # MACD Bullish
    if macd_val > macd_signal_val:
        criteria.append("MACD Bullish")
        criteria_names.append("MACD")
    # R:R Good
    if rr_ratio >= 2.0:
        criteria.append("R:R >= 2.0")
        criteria_names.append("R:R>=2")
    elif rr_ratio >= 1.5:
        criteria.append("R:R >= 1.5")
        criteria_names.append("R:R>=1.5")
    # Fast Holding
    if est_days <= 10:
        criteria.append("Fast Holding")
        criteria_names.append("Fast")
    # VWAP
    if vwap_status_val == "above":
        criteria.append("Above VWAP")
        criteria_names.append("VWAP")
    # Ichimoku Bullish
    if ichimoku_status_val == "bullish":
        criteria.append("Ichimoku Bullish")
        criteria_names.append("Cloud")
    # SuperTrend Bullish
    if supertrend_signal_val == "bullish":
        criteria.append("SuperTrend Bull")
        criteria_names.append("ST")

    criteria_met = len(criteria)

    # ========== FUND SCORE (Spec mới: trần 100, 3 mục = 40 + 30 + 30) ==========
    fund_score = 0

    # 1. Piotroski F-Score (tối đa 40)
    if f_score_val >= 8:
        fund_score += 40
    elif f_score_val >= 6:
        fund_score += 30
    elif f_score_val == 5:
        fund_score += 20
    # F < 5: +0 và VETO layer 1 đã chặn (VETO_10) — không tính thêm

    # 2. ROE (tối đa 30)
    if roe_val is not None:
        if roe_val > 25:
            fund_score += 30
        elif 15 <= roe_val <= 25:
            fund_score += 20
        elif 10 <= roe_val < 15:
            fund_score += 10
        # Án phạt ROE yếu kém so với ngưỡng ngành
        is_capital_intensive = sector_group in ('cyclical',)
        roe_floor = 10 if is_capital_intensive else 15
        if roe_val < roe_floor:
            fund_score -= 15

    # 3. Profit Growth (tối đa 30)
    profit_growth = fund_data.get('profit_growth')
    if profit_growth is not None:
        if profit_growth > 25:
            fund_score += 30
        elif 15 <= profit_growth <= 25:
            fund_score += 20
        elif 5 <= profit_growth < 15:
            fund_score += 10

    fund_score = max(0, min(100, fund_score))

    # ========== EARNING GUIDANCE (profit_plan_completion) ==========
    # Theo spec: chỉ dùng làm Plan Penalty cho Master Score (KHÔNG cộng vào fund_score)
    plan_penalty = 0
    plan_completion_pct = None
    plan_status = "N/A"
    annual_plan = fund_data.get('annual_profit_plan')
    current_ytd = fund_data.get('current_ytd_profit')

    if annual_plan and current_ytd and annual_plan > 0:
        plan_completion_pct = (current_ytd / annual_plan) * 100

        now = datetime.now()
        current_month = now.month
        current_quarter = (current_month - 1) // 3 + 1
        expected_progress_pct = current_quarter * 25  # 25%, 50%, 75%, 100%

        min_required_pct = expected_progress_pct * 0.8

        if plan_completion_pct < min_required_pct:
            plan_penalty = -20
            plan_status = "BEHIND"
        elif plan_completion_pct >= expected_progress_pct:
            plan_status = "ON_TRACK"
        else:
            plan_status = "SLIGHTLY_BEHIND"

    # NOTE: Theo spec mới, foreign_streak/foreign_bonus và industry_perf
    # KHÔNG còn được cộng trực tiếp vào fund_score. Tác động khối ngoại
    # được áp dụng tại Master Score (Foreign Flow Modifier), còn industry
    # dùng cho Relative Strength Bonus.

    industry_perf = fund_data.get('industry_performance', 0)

    # ========== RISK ASSESSMENT ==========
    is_market_high_risk = market_rsi > 80
    sl_distance_pct = ((entry - stop_loss) / entry) * 100 if entry > 0 else 0

    if sl_distance_pct > 7:
        stock_risk_level = "High"
        stock_risk_reason = f"SL cách xa {sl_distance_pct:.1f}%"
    elif sl_distance_pct > 5:
        stock_risk_level = "Medium"
        stock_risk_reason = f"SL cách xa {sl_distance_pct:.1f}%"
    elif sl_distance_pct > 3:
        stock_risk_level = "Low"
        stock_risk_reason = f"SL cách xa {sl_distance_pct:.1f}%"
    else:
        stock_risk_level = "Very Low"
        stock_risk_reason = f"SL gần {sl_distance_pct:.1f}%"

    if sma_50_val > 0 and price_val < sma_50_val:
        stock_risk_level = "High"
        stock_risk_reason = "Giá dưới SMA50 (xu hướng dài hạn giảm)"

    is_high_risk = stock_risk_level == "High"

    # ========== SIGNAL ==========
    is_sell_zone = market_rsi > 70

    # Determine signal based on tech_score + entry_quality + rr_ratio
    if rr_ratio < 1.0 or target_yield_pct < 3:
        signal = "WAIT"
    elif tech_score >= 75 and entry_quality == "GOOD":
        signal = "STRONG_BUY"
    elif tech_score >= 65 and entry_quality != "BAD":
        signal = "BUY"
    elif entry_quality == "ACCUMULATE":
        signal = "ACCUMULATE"
    else:
        signal = "WAIT"

    # Bộ phanh rủi ro đơn lẻ: Nếu cổ phiếu quá đắt hoặc RSI cá nhân quá nóng, cấm mua mạnh
    if price_val > (fv_daily * 1.15) or rsi_val > 80:
        if signal in ["STRONG_BUY", "BUY"]:
            signal = "WAIT"

    # ============================================================
    # MARKET REGIME ADJUSTMENTS
    # Apply TP scale and FREEZE override AFTER signal is determined.
    # ============================================================
    if market_regime == "DEFENSE":
        take_profit = round(take_profit * market_tp_scale, 2)
    elif market_regime == "FREEZE":
        signal = "WAIT"
        take_profit = round(take_profit * market_tp_scale, 2)

    # Recalculate target yield after market-adjusted TP
    target_yield_pct = round((take_profit - entry) / entry * 100, 2) if entry > 0 else 0

    # ========== RELATIVE STRENGTH (RS) BONUS/PENALTY (spec: -10..+15) ==========
    rs_bonus = 0
    rs_label = "NEUTRAL"

    if industry_perf > 5:
        rs_bonus = 15
        rs_label = "LEADER"
    elif industry_perf > 0:
        rs_bonus = 8
        rs_label = "OUTPERFORM"
    elif industry_perf < 0:
        rs_bonus = -10
        rs_label = "LAGGARD"

    rs_info = {
        'bonus': rs_bonus,
        'label': rs_label,
        'industry_performance': industry_perf
    }

    # ========== MARKET WEIGHT (spec: -25..+20) ==========
    market_weight = 0
    if market_rsi < 25:
        market_weight = 20
    elif market_rsi > 80:
        market_weight = -20
    elif market_rsi > 70:
        market_weight = -10

    # ========== FOREIGN FLOW MODIFIER (spec: -25..+30) ==========
    fmm_latest_net = fund_data.get('latest_net_val', 0.0)
    fmm_streak = fund_data.get('foreign_buy_streak', 0)
    absorption = fund_data.get('foreign_absorption_ratio', 0.0)
    foreign_accumulated_trend = fund_data.get('foreign_accumulated_trend', 'NEUTRAL')

    foreign_master_modifier = 0

    if foreign_accumulated_trend == 'ACCUMULATING':
        if fmm_latest_net > 0:
            if absorption > 20:
                foreign_master_modifier = 25
            elif 10 <= absorption <= 20:
                foreign_master_modifier = 15
    elif foreign_accumulated_trend == 'DISTRIBUTING':
        if fmm_latest_net < 0 and absorption > 20:
            foreign_master_modifier = -25

    if fmm_streak >= 5:
        foreign_master_modifier += 5

    if foreign_accumulated_trend == 'NEUTRAL':
        if fmm_streak >= 5:
            foreign_master_modifier = 8
        elif fmm_streak >= 3:
            foreign_master_modifier = 4
        elif fmm_streak == 0 and fmm_latest_net < 0:
            foreign_master_modifier = -8

    foreign_master_modifier = max(-25, min(30, foreign_master_modifier))

    # Clamp scores
    tech_score = max(0, min(100, tech_score))
    fund_score = max(0, min(100, fund_score))

    # ========== MASTER SCORE ==========
    base_master_score = int(round(tech_score * 0.7 + fund_score * 0.3))
    final_master_score = (
        base_master_score
        + market_weight
        + rs_bonus
        + plan_penalty
        + foreign_master_modifier
    )
    master_score = max(0, min(100, final_master_score))

    # ========== FREEZE OVERRIDE (uses master_score) ==========
    if market_regime == "FREEZE":
        master_score = min(master_score, 45)

    # ========== TREND ==========
    if sma_20_val > 0 and sma_50_val > 0:
        if price_val > sma_20_val > sma_50_val:
            trend = "UPTREND"
        elif price_val < sma_20_val < sma_50_val:
            trend = "DOWNTREND"
        else:
            trend = "SIDEWAYS"
    else:
        trend = "SIDEWAYS"

    # ========== RECOMMENDATION LABEL ==========
    if master_score >= 70:
        strategy_group = "GOLD"
    elif master_score >= 55:
        strategy_group = "GUERRILLA"
    else:
        strategy_group = "RISK"

    if plan_status == "BEHIND" and strategy_group == "GOLD":
        strategy_group = "WATCH"

    recommendation_label = f"{signal} ({strategy_group})"

    if is_vetoed:
        recommendation_label = "WAIT (VETO)"
        signal = "WAIT"
        breakout_status = "VETO"

    # ========== VALUATION STATUS (based on fv_daily) ==========
    safe_threshold = fv_daily * 0.9
    valuation_status = "Rẻ" if price_val < safe_threshold else "Đắt"

    if is_vetoed:
        valuation_status = "RISK"

    # ===== R:R QUALITY GRADING =====
    rr_quality = ""
    rr_quality_detail = ""
    rr_warning = ""

    if rr_ratio >= 10:
        rr_quality = "⚠️ Warning"
        rr_quality_detail = "Cắt lỗ quá sát, rủi ro nhiễu cao"
        rr_warning = f"⚠️ Cắt lỗ quá sát, rủi ro nhiễu cao"
    elif 5.0 <= rr_ratio < 10:
        rr_quality = "💎 Diamond"
        rr_quality_detail = "Kèo cực phẩm - R:R vượt ngưỡng"
    elif 2.5 <= rr_ratio < 5.0:
        rr_quality = "⭐ Golden"
        rr_quality_detail = "Vùng R:R lý tưởng"
    elif 1.5 <= rr_ratio < 2.5:
        rr_quality = "Good"
        rr_quality_detail = "R:R khả thi"
    else:
        rr_quality = "Poor"
        rr_quality_detail = "R:R thấp"

    # ============================================================
    # SIGNAL OVERRIDE BRAKE - chặn mua đuổi khi quá đắt hoặc RSI quá nóng
    # Đặt cuối hàm, trên return để đảm bảo chặn mọi tín hiệu BUY/STRONG_BUY.
    # ============================================================
    if (fv_daily > 0 and price_val > fv_daily * 1.15) or rsi_val > 80:
        signal = "WAIT"
        recommendation_label = "WAIT (OVERVALUED)"

    # ========== RETURN ==========
    return {
        # Basic info
        "symbol": symbol,
        "price": price_val,
        "change_percent": tech.get("change_percent", 0),
        "volume": tech.get("volume", 0),
        # Technical
        "rsi": rsi_val,
        "mfi": tech.get("mfi", 50),
        "adx": adx_val,
        "plus_di": tech.get("plus_di", 0),
        "minus_di": tech.get("minus_di", 0),
        "cmf": cmf_val,
        "atr": atr_value,
        "sma_10": sma_10_val,
        "sma_20": sma20_val_t,
        "sma_50": sma_50_val,
        "bb_upper": bb_upper_val,
        "bb_middle": bb_middle_val,
        "bb_lower": bb_lower_val,
        "bb_percent": bb_percent_val,
        "macd": macd_val,
        "macd_signal": macd_signal_val,
        "volume_ratio": volume_ratio_val,
        # Advanced TA
        "vwap": vwap_val,
        "vwap_status": vwap_status_val,
        "ichimoku_tenkan": tech.get("ichimoku_tenkan", 0),
        "ichimoku_kijun": tech.get("ichimoku_kijun", 0),
        "ichimoku_status": ichimoku_status_val,
        "supertrend": tech.get("supertrend", 0),
        "supertrend_signal": supertrend_signal_val,
        # Avg volume value
        "avg_volume_value": avg_volume_value,
        # Trading levels
        "entry_price": entry,
        "stop_loss": stop_loss,
        "trailing_sl": trailing_sl,
        "take_profit": take_profit,
        "risk_reward_ratio": rr_ratio,
        "rr_quality": rr_quality,
        "rr_quality_detail": rr_quality_detail,
        "rr_warning": rr_warning,
        # Foreign Master Modifier (X2)
        "foreign_master_modifier": foreign_master_modifier,
        # Fair Value
        "fv_daily": fv_daily,
        "valuation_status": valuation_status,
        "intrinsic_value": round(pe_valuation, 2),
        "sector_median_pe": sector_median_pe,
        "valuation_source": valuation_source,
        "valuation_cap_applied": valuation_cap_applied,
        "industry_config": val_config,
        # Target Yield & Est. Days
        "target_yield_pct": target_yield_pct,
        "trend_factor": trend_factor,
        "estimated_days_to_target": round(est_days, 1),
        "timeframe_label": timeframe_label,
        "timeframe_color": timeframe_color,
        "expected_profit_per_day": profit_per_day,
        "upside_per_day": profit_per_day,
        # Scores
        "master_score": master_score,
        "base_master_score": base_master_score,
        "market_weight": market_weight,
        "technical_score": tech_score,
        "fundamental_score": fund_score,
        # Safe Entry & Resistance
        "is_safe_entry": is_safe_entry,
        "has_high_resistance": has_high_resistance,
        # Signal & Status
        "signal": signal,
        "is_vetoed": is_vetoed,
        "veto_reason": veto_reason,
        "is_fast_pick": is_fast_pick,
        "is_short_term_qualified": not is_vetoed and criteria_met >= 9,
        "is_slow_mode": est_days > 10,
        "is_high_risk": is_high_risk,
        "is_market_high_risk": is_market_high_risk,
        "stock_risk_level": stock_risk_level,
        "stock_risk_reason": stock_risk_reason,
        "has_inverted_sl": has_inverted_sl,
        "is_inverted_risk": is_inverted_risk,
        # Criteria
        "criteria_met": criteria_met,
        "criteria_list": criteria,
        "criteria_names": criteria_names,
        # Recommendation Label
        "recommendation_label": recommendation_label,
        # Trend
        "trend": trend,
        "breakout_status": "BREAKOUT" if is_fast_pick and not is_vetoed else ("VETO" if is_vetoed else "WAIT"),
        # Market
        "market_rsi": market_rsi,
        "market_regime": market_regime,
        "market_regime_label": market_regime_label,
        "market_regime_icon": market_regime_icon,
        "market_regime_color": market_regime_color,
        "market_veto_boost": market_veto_boost,
        "market_position_scale": market_position_scale,
        "market_tp_scale": market_tp_scale,
        # Fundamental
        "roe": roe_val,
        "pe": fund_data.get('pe'),
        "pb": fund_data.get('pb'),
        "f_score": f_score_val,
        "f_score_grade": get_f_score_grade(f_score_val),
        "profit_growth": profit_growth,
        # Earning Guidance
        "annual_profit_plan": annual_plan,
        "current_ytd_profit": current_ytd,
        "profit_plan_completion": plan_completion_pct,
        "profit_plan_status": plan_status,
        "plan_penalty_applied": plan_penalty,
        "profit_growth_note": fund_data.get('profit_growth_note', 'N/A'),
        "is_new_listing": fund_data.get('is_new_listing', False),
        # Smart Money & Industry
        "foreign_buy_streak": fund_data.get('foreign_buy_streak', 0),
        "foreign_bonus": 0,  # giữ field cho UI; tác động khối ngoại đã gộp vào foreign_master_modifier
        "latest_net_val": fund_data.get('latest_net_val', 0.0),
        "foreign_absorption_ratio": fund_data.get('foreign_absorption_ratio', 0.0),
        "latest_net_val_2": fund_data.get('latest_net_val_2', 0.0),
        "foreign_buy_val": fund_data.get('foreign_buy_val', 0.0),
        "foreign_sell_val": fund_data.get('foreign_sell_val', 0.0),
        "foreign_trading_share": fund_data.get('foreign_trading_share', 0.0),
        "foreign_accumulated_trend": fund_data.get('foreign_accumulated_trend', 'NEUTRAL'),
        "foreign_accumulated_slope": fund_data.get('foreign_accumulated_slope', 0.0),
        "industry_performance": industry_perf,
        "is_industry_leader": industry_perf >= 0,
        # Real R:R
        "hard_risk_pct": round(hard_risk_pct, 2),
        "support_price": round(support_price, 2),
        "risk_percent": round(risk_percent * 100, 2),
        # P/E Industry
        "pe_industry_avg": fund_data.get('pe_industry_avg') or 0,
        # Early Exit
        "early_exit_trigger_pct": early_exit_trigger_pct,
        "early_exit_drop_pct": early_exit_drop_pct,
        "optimal_position_size": optimal_position_size,
        "account_balance": 100_000_000,
        "risk_tolerance_pct": 2.0,
        # Industry
        "industry": industry,
        "sector": sector,
        "sector_group": sector_group,
        # Relative Strength (RS)
        "rs_bonus": rs_info['bonus'],
        "rs_label": rs_info['label'],
        "rs_industry_performance": rs_info['industry_performance'],
    # Entry quality (new fields per refactor)
    "entry_quality": entry_quality,
    "entry_quality_reason": entry_quality_reason,
}


def calculate_technical_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate technical indicators using manual Pandas and TradingView API
    Includes: RSI, MACD, ADX, CMF, Bollinger, SMA, VWAP, Ichimoku, SuperTrend, MFI
    """
    result = {
        "price": 0.0,
        "change_percent": 0.0,
        "volume": 0,
        "rsi": 50.0,
        "mfi": 50.0,
        "adx": 25.0,
        "plus_di": 0.0,
        "minus_di": 0.0,
        "cmf": 0.0,
        "sma_10": 0.0,
        "sma_20": 0.0,
        "sma_50": 0.0,
        "sma_200": 0.0,
        "bb_upper": 0.0,
        "bb_middle": 0.0,
        "bb_lower": 0.0,
        "bb_percent": 50.0,
        "macd": 0.0,
        "macd_signal": 0.0,
        "atr": 0.0,
        "vwap": 0.0,
        "vwap_status": "neutral",
        "ichimoku_tenkan": 0.0,
        "ichimoku_kijun": 0.0,
        "ichimoku_status": "neutral",
        "supertrend": 0.0,
        "supertrend_signal": "neutral",
        "volume_ratio": 1.0,
    }

    if df is None or len(df) < 20:
        return result

    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    try:
        # Current values
        result["price"] = float(close.iloc[-1])
        result["volume"] = int(volume.iloc[-1]) if 'volume' in df.columns else 0

        # Change Percent
        if len(close) > 1:
            prev_close = float(close.iloc[-2])
            if prev_close > 0:
                result["change_percent"] = round((result["price"] - prev_close) / prev_close * 100, 2)

        # Volume Ratio
        avg_vol = volume.tail(20).mean()
        if avg_vol > 0:
            result["volume_ratio"] = round(float(volume.iloc[-1]) / avg_vol, 2)

        # Dùng TradingView API cho các chỉ báo cơ bản
        symbol_name = df.attrs.get("symbol")
        if symbol_name:
            try:
                from dashboard.tv_client import get_multiple_indicators
                tv_inds = get_multiple_indicators(
                    symbol=symbol_name,
                    indicators=["STD;RSI", "STD;MACD", "STD;Bollinger_Bands", "STD;DMI", "STD;Supertrend"]
                )
                if tv_inds:
                    for item in tv_inds:
                        ind_name = item.get("indicator")
                        data = item.get("data")
                        if not data or len(data) == 0:
                            continue
                        last_val = data[-1]
                        
                        if ind_name == "STD;RSI" and "RSI" in last_val:
                            result["rsi"] = round(float(last_val["RSI"]), 1)
                        
                        elif ind_name == "STD;MACD" and "MACD" in last_val and "Signal_line" in last_val:
                            result["macd"] = round(float(last_val["MACD"]), 2)
                            result["macd_signal"] = round(float(last_val["Signal_line"]), 2)
                            
                        elif ind_name == "STD;Bollinger_Bands" and "Upper" in last_val and "Lower" in last_val and "Basis" in last_val:
                            result["bb_upper"] = round(float(last_val["Upper"]), 2)
                            result["bb_middle"] = round(float(last_val["Basis"]), 2)
                            result["bb_lower"] = round(float(last_val["Lower"]), 2)
                            if result["bb_upper"] > result["bb_lower"]:
                                result["bb_percent"] = round((result["price"] - result["bb_lower"]) / (result["bb_upper"] - result["bb_lower"]) * 100, 1)
                                
                        elif ind_name == "STD;DMI" and "ADX" in last_val and "DI" in last_val and "DI_2" in last_val:
                            result["adx"] = round(float(last_val["ADX"]), 1)
                            # Note: TradingView DI / DI_2 maps to +DI / -DI depending on formula.
                            # Normally DI is +DI, DI_2 is -DI.
                            result["plus_di"] = round(float(last_val["DI"]), 1)
                            result["minus_di"] = round(float(last_val["DI_2"]), 1)
                            
                        elif ind_name == "STD;Supertrend" and "Trend_Change" in last_val:
                            # Down_Trend contains value when bearish, Up_Trend when bullish.
                            if last_val.get("Up_Trend") and last_val["Up_Trend"] < 1e50:
                                result["supertrend"] = round(float(last_val["Up_Trend"]), 2)
                                result["supertrend_signal"] = "bullish"
                            elif last_val.get("Down_Trend") and last_val["Down_Trend"] < 1e50:
                                result["supertrend"] = round(float(last_val["Down_Trend"]), 2)
                                result["supertrend_signal"] = "bearish"
            except Exception as e:
                print(f"[Sync] TV API Fallback error: {e}")

        # Tự tính SMA bằng pandas (Chính xác 100% và cực nhanh)
        if len(close) >= 200:
            result["sma_200"] = round(float(close.rolling(200).mean().iloc[-1]), 2)
        if len(close) >= 50:
            result["sma_50"] = round(float(close.rolling(50).mean().iloc[-1]), 2)
        if len(close) >= 20:
            result["sma_20"] = round(float(close.rolling(20).mean().iloc[-1]), 2)
        if len(close) >= 10:
            result["sma_10"] = round(float(close.rolling(10).mean().iloc[-1]), 2)

        # Manual ATR fallback
        if result["atr"] <= 0 and len(df) >= 15:
            try:
                tr1 = high - low
                tr2 = abs(high - close.shift(1))
                tr3 = abs(low - close.shift(1))
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr_series = tr.rolling(14).mean()
                result["atr"] = round(float(atr_series.iloc[-1]), 2) if not pd.isna(atr_series.iloc[-1]) else 0
            except Exception:
                pass

        # ATR fallback to percentage
        if result["atr"] <= 0 or result["atr"] is None:
            result["atr"] = round(result["price"] * 0.02, 2) if result["price"] > 0 else 1000

        # Manual RSI fallback
        if result["rsi"] == 50.0:
            try:
                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                result["rsi"] = round(float(rsi.iloc[-1]), 1) if not pd.isna(rsi.iloc[-1]) else 50
            except Exception:
                pass

        # Manual Bollinger Bands fallback (SMA 20, 2 STD)
        if (result["bb_middle"] <= 0 or result["bb_upper"] <= 0) and len(close) >= 20:
            try:
                sma_20 = close.rolling(20).mean()
                std_20 = close.rolling(20).std()
                bb_upper = sma_20 + (2.0 * std_20)
                bb_lower = sma_20 - (2.0 * std_20)
                last_price = float(close.iloc[-1])
                last_mid = float(sma_20.iloc[-1])
                last_up = float(bb_upper.iloc[-1])
                last_low = float(bb_lower.iloc[-1])
                result["bb_middle"] = round(last_mid, 2)
                result["bb_upper"] = round(last_up, 2)
                result["bb_lower"] = round(last_low, 2)
                if last_up > last_low:
                    result["bb_percent"] = round((last_price - last_low) / (last_up - last_low) * 100, 1)
                else:
                    result["bb_percent"] = 50.0
            except Exception:
                pass

        # Manual MACD fallback (12, 26, 9 EMA)
        if result["macd"] == 0.0 and result["macd_signal"] == 0.0 and len(close) >= 26:
            try:
                exp1 = close.ewm(span=12, adjust=False).mean()
                exp2 = close.ewm(span=26, adjust=False).mean()
                macd_line = exp1 - exp2
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                histogram = macd_line - signal_line
                result["macd"] = round(float(macd_line.iloc[-1]), 2)
                result["macd_signal"] = round(float(signal_line.iloc[-1]), 2)
                result["macd_histogram"] = round(float(histogram.iloc[-1]), 2)
            except Exception:
                pass

        # Manual CMF
        if result["cmf"] == 0.0:
            try:
                mfm = ((close - low) - (high - close)) / (high - low)
                mfm = mfm.fillna(0)
                mfv = mfm * volume
                cmf = mfv.rolling(20).sum() / volume.rolling(20).sum()
                result["cmf"] = round(float(cmf.iloc[-1]), 4) if not pd.isna(cmf.iloc[-1]) else 0
            except Exception:
                pass

        # Manual MFI
        if result["mfi"] == 50.0:
            try:
                typical_price = (high + low + close) / 3
                money_flow = typical_price * volume
                positive_flow = money_flow.where(typical_price > typical_price.shift(), 0).rolling(14).sum()
                negative_flow = money_flow.where(typical_price < typical_price.shift(), 0).rolling(14).sum()
                money_ratio = positive_flow / negative_flow.replace(0, 1)
                mfi = 100 - (100 / (1 + money_ratio))
                result["mfi"] = round(float(mfi.iloc[-1]), 1) if not pd.isna(mfi.iloc[-1]) else 50
            except Exception:
                pass

        # VWAP
        try:
            typical_price = (high + low + close) / 3
            cum_vol = volume.cumsum()
            vwap_series = (typical_price * volume).cumsum() / cum_vol
            last_vwap = vwap_series.iloc[-1]
            if pd.isna(last_vwap) or math.isnan(float(last_vwap)) or math.isinf(float(last_vwap)):
                result["vwap"] = float(result["price"])
            else:
                result["vwap"] = round(float(last_vwap), 2)
            result["vwap_status"] = "above" if result["price"] > result["vwap"] else "below"
        except Exception:
            result["vwap"] = float(result.get("price", 0.0))
            result["vwap_status"] = "neutral"

        # Ichimoku
        if len(df) >= 52:
            try:
                high_9 = high.rolling(9).max()
                low_9 = low.rolling(9).min()
                result["ichimoku_tenkan"] = round((high_9 + low_9).iloc[-1] / 2, 2)

                high_26 = high.rolling(26).max()
                low_26 = low.rolling(26).min()
                result["ichimoku_kijun"] = round((high_26 + low_26).iloc[-1] / 2, 2)

                tenkan = result["ichimoku_tenkan"]
                kijun = result["ichimoku_kijun"]
                price = result["price"]

                if price > tenkan > kijun:
                    result["ichimoku_status"] = "bullish"
                elif price < tenkan < kijun:
                    result["ichimoku_status"] = "bearish"
                else:
                    result["ichimoku_status"] = "neutral"
            except Exception:
                pass

        # SuperTrend
        try:
            if result["atr"] > 0:
                hl2 = (high + low) / 2
                lower_band = hl2 - (result["atr"] * 2)
                result["supertrend"] = round(float(lower_band.iloc[-1]), 2)
                result["supertrend_signal"] = "bullish" if result["price"] > result["supertrend"] else "bearish"
        except Exception:
            pass

    except Exception as e:
        print(f"[Sync] Error calculating indicators: {e}")

    return result


def analyze_stock(symbol: str, market_rsi: float = 50.0, fast_mode: bool = False, vnindex_df=None) -> Optional[Dict[str, Any]]:
    """Phân tích một mã cổ phiếu - trả về dict kết quả
    fast_mode: True = bỏ qua các API calls tốn thời gian (profit_growth, industry, foreign)
    vnindex_df: DataFrame VNINDEX đã prefetch sẵn (tránh cache congestion giữa 8 threads)

    REFACTORED: Sử dụng compute_core_logic() để đảm bảo đồng bộ với Backtest
    """
    try:
        import warnings as w
        w.filterwarnings('ignore')

        # Get Company Name (skip in fast mode)
        company_name = get_company_name(symbol) if not fast_mode else symbol

        # Get Price Data - try TradingView API first (via microservice)
        from dashboard.tv_client import get_ohlcv_with_fallback
        df = get_ohlcv_with_fallback(symbol, exchange='HOSE', count=250)
        
        if df is None or len(df) < 50:
            print(f"[Sync] Insufficient price data for {symbol}")
            return None

        # Get Fundamental Data (ROE, P/E, P/B, F-Score, Foreign, RS)
        fund_data = get_fundamental_data(symbol, fast_mode=fast_mode, vnindex_df=vnindex_df, df=df)
            
        # Lưu symbol vào df attrs để calculate_technical_indicators có thể gọi TV API
        df.attrs["symbol"] = symbol
            
        # TradingView trả giá trị thật (VD: 20150.0), không cần nhân 1000 như vnstock
        price_multiplier = 1

        # Get Market Group for Veto check
        market_group = "UNKNOWN"
        try:
            stock = StockData.objects.get(symbol=symbol.upper())
            market_group = stock.market_group or "UNKNOWN"
        except:
            pass

        # Calculate indicators
        tech = calculate_technical_indicators(df)
        
        # Add industry to fund_data - prioritize API, fallback to DB
        fund_data_with_industry = dict(fund_data)
        
        # Try vnstock_data API first
        industry_from_api = get_industry(symbol)
        if industry_from_api and industry_from_api != "Default":
            fund_data_with_industry['industry'] = industry_from_api
        else:
            # Fallback to DB
            try:
                stock = StockData.objects.get(symbol=symbol.upper())
                fund_data_with_industry['industry'] = stock.industry or 'Default'
            except:
                fund_data_with_industry['industry'] = 'Default'

        # ========== CALL CORE LOGIC ENGINE ==========
        result = compute_core_logic(
            symbol=symbol,
            tech=tech,
            fund_data=fund_data_with_industry,
            market_rsi=market_rsi,
            market_group=market_group,
            df=df
        )
        
        # Add company_name (only for live analysis)
        result['company_name'] = company_name

        return result

    except Exception as e:
        print(f"[Sync] Error analyzing {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None


def sync_stock_batch(symbols: List[str], market_rsi: float = 50.0, fast_mode: bool = False, retry_failed: int = 2, vnindex_df=None) -> Dict[str, Any]:
    """Đồng bộ một batch mã cổ phiếu với timeout per-symbol, retry logic và fast_mode"""
    SYMBOL_TIMEOUT = 35 if fast_mode else 60  # Fast mode = 35s, Full mode = 60s
    MAX_RETRIES = retry_failed  # Số lần retry cho failed symbols
    
    results = []
    failed_symbols = list(symbols)  # Bắt đầu với tất cả symbols
    
    for attempt in range(MAX_RETRIES + 1):
        if not failed_symbols:
            break
            
        if attempt > 0:
            print(f"[Sync] 🔄 Thử lại lần {attempt}/{MAX_RETRIES} cho {len(failed_symbols)} mã lỗi...", flush=True)
            sleep(2)  # Chờ 2s trước khi retry
        
        batch_results = []
        still_failed = []
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(analyze_stock, symbol, market_rsi, fast_mode, vnindex_df): symbol for symbol in failed_symbols}
            
            # Tính timeout tổng = timeout per symbol + buffer
            total_timeout = (SYMBOL_TIMEOUT + 10) * (MAX_RETRIES - attempt + 1)  # Tăng timeout cho retry
            
            try:
                for future in as_completed(futures, timeout=total_timeout):
                    symbol = futures[future]
                    try:
                        result = future.result(timeout=SYMBOL_TIMEOUT)
                        if result:
                            batch_results.append(result)
                            score = result.get('master_score', 0)
                            f_score = result.get('f_score', 0)
                            is_veto = result.get('is_vetoed', False)
                            veto_reason = result.get('veto_reason', '')
                            tag = f"VETO ({veto_reason})" if is_veto else f"PASS (Score: {score})"
                            print(f"[Sync]   -> {symbol:4s} | F: {f_score} | {tag}", flush=True)
                        else:
                            still_failed.append(symbol)
                            print(f"[Sync]   -> {symbol:4s} | ⚠️ Không có dữ liệu", flush=True)
                    except TimeoutError:
                        print(f"[Sync]   -> {symbol:4s} | ⏱️ Hết thời gian chờ (Timeout)", flush=True)
                        still_failed.append(symbol)
                    except Exception as e:
                        print(f"[Sync]   -> {symbol:4s} | ❌ Lỗi: {e}", flush=True)
                        still_failed.append(symbol)
            except TimeoutError:
                # Timeout toàn bộ batch
                print(f"[Sync] ⚠️ Batch timeout sau {total_timeout}s", flush=True)
                still_failed = list(futures.values())
        
        results.extend(batch_results)
        failed_symbols = still_failed
    
    if failed_symbols:
        print(f"[Sync] ⚠️ {len(failed_symbols)} mã không phân tích được sau {MAX_RETRIES} lần thử: {failed_symbols}", flush=True)
    
    return {"results": results, "count": len(results), "failed": failed_symbols}


def sync_market_data(mode: str = "full", fast_mode: bool = False) -> Dict[str, Any]:
    """Đồng bộ toàn bộ dữ liệu thị trường
    fast_mode: True = bỏ qua các API calls tốn thời gian (profit_growth, industry, foreign)
    """
    start_time = datetime.now()

    # Lấy danh sách symbols TRƯỚC để biết total_symbols chính xác
    if mode == "analyze":
        symbols = list(StockData.objects.values_list('symbol', flat=True))
        print(f"[Sync] Chế độ Phân tích lại (Analyze mode): {len(symbols)} mã có sẵn trong DB", flush=True)
    else:
        symbols = _get_top_100_by_liquidity()  # Sử dụng danh sách tuyển chọn chuẩn
        print(f"[Sync] Đã sẵn sàng danh sách {len(symbols)} mã cần đồng bộ", flush=True)

    # Tạo SyncStatus với đúng số lượng symbols
    sync_record, created = SyncStatus.objects.get_or_create(
        id=1,
        defaults={
            "status": "running",
            "total_symbols": len(symbols),
            "processed_symbols": 0,
            "started_at": timezone.now()
        }
    )
    sync_record.status = "running"
    sync_record.total_symbols = len(symbols)  # Cập nhật đúng số lượng thực tế
    sync_record.started_at = timezone.now()
    sync_record.processed_symbols = 0
    sync_record.save()

    mode_desc = "ĐẦY ĐỦ (FULL)" if not fast_mode else "NHANH (FAST)"
    print(f"\n[Sync] ==================================================", flush=True)
    print(f"[Sync] BẮT ĐẦU ĐỒNG BỘ: mode='{mode}' ({mode_desc}) | {len(symbols)} mã", flush=True)
    print(f"[Sync] ==================================================", flush=True)

    # Lấy Market RSI
    market_rsi = get_market_rsi()
    print(f"[Sync] Market RSI VNINDEX: {market_rsi:.2f}", flush=True)

    # Prefetch VNINDEX history TRƯỚC khi chia thread từ TradingView
    vnindex_df = None
    try:
        from dashboard.tv_client import get_ohlcv, ensure_tv_service
        ensure_tv_service()
        vnindex_df = get_ohlcv('VNINDEX', count=250)
        if vnindex_df is not None and len(vnindex_df) > 0:
            print(f"[Sync] VNINDEX prefetch hoàn tất: {len(vnindex_df)} phiên nến từ TradingView", flush=True)
        else:
            vnindex_df = None
    except Exception as e:
        print(f"[Sync] VNINDEX prefetch cảnh báo: {e}", flush=True)

    # 🌐 Đồng bộ nhanh dòng tiền khối ngoại cho toàn bộ Universe từ VCI price_board (0.5 - 1s)
    try:
        print("[Sync] 🌐 Bắt đầu đồng bộ dòng tiền khối ngoại từ VCI price_board...", flush=True)
        sync_foreign_flow_from_vci(symbols)
        print("[Sync] ✅ Đã cập nhật dòng tiền khối ngoại thành công!", flush=True)
    except Exception as fe:
        print(f"[Sync] Cảnh báo lỗi đồng bộ khối ngoại: {fe}", flush=True)

    # Process in batches
    batch_size = 20
    all_results = []
    total_failed = 0
    failed_symbols_list = []
    saved_count = 0

    try:
        total_batches = (len(symbols) + batch_size - 1) // batch_size
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            batch_num = i // batch_size + 1
            print(f"\n[Sync] >>> Batch {batch_num}/{total_batches} ({len(batch)} mã): {', '.join(batch[:4])}...", flush=True)
            print(f"[Sync] Tiến độ hiện tại: {i}/{len(symbols)} mã ({(i / len(symbols) * 100):.0f}%)", flush=True)

            try:
                batch_result = sync_stock_batch(batch, market_rsi, fast_mode=fast_mode, vnindex_df=vnindex_df)
                if batch_result and "results" in batch_result:
                    all_results.extend(batch_result["results"])
                
                if batch_result and batch_result.get("failed"):
                    total_failed += len(batch_result["failed"])
                    failed_symbols_list.extend(batch_result["failed"])
            except Exception as batch_err:
                print(f"[Sync] ❌ Lỗi khi xử lý batch {batch_num}: {batch_err}", flush=True)
                total_failed += len(batch)
                failed_symbols_list.extend(batch)

            # Update progress percentage
            sync_record.processed_symbols = min(i + batch_size, len(symbols))
            sync_record.save()
            print(f"[Sync] Đã xong Batch {batch_num}/{total_batches}. Tổng đã quét thành công: {len(all_results)} mã.", flush=True)

        # Save to Database
        failed_msg = f" ({total_failed} mã lỗi)" if total_failed > 0 else ""
        print(f"\n[Sync] Đã phân tích xong {len(all_results)}/{len(symbols)} mã thành công{failed_msg}", flush=True)
        if all_results:
            print(f"[Sync] Đang lưu {len(all_results)} mã vào cơ sở dữ liệu...", flush=True)
            saved_count = save_results_to_db(all_results)
            print(f"[Sync] ✅ Đã lưu thành công {saved_count} bản ghi vào Database!", flush=True)

        # Validation: Top 5 by F-Score
        if all_results:
            valid_fscore = [r for r in all_results if r.get('f_score', 0) > 0]
            if valid_fscore:
                top_fscore = sorted(valid_fscore, key=lambda x: x.get('f_score') or 0, reverse=True)[:5]
                print(f"[Sync] Top 5 theo F-Score cao nhất:", flush=True)
                for r in top_fscore:
                    print(f"  {r['symbol']}: F={r.get('f_score')}, ROE={r.get('roe')}, PE={r.get('pe')}, PB={r.get('pb')}", flush=True)

            # Top 5 by Volume Ratio (for FAST picks)
            non_vetoed = [r for r in all_results if not r.get('is_vetoed')]
            if non_vetoed:
                top_vol = sorted(non_vetoed, key=lambda x: x.get('volume_ratio') or 0, reverse=True)[:5]
                print(f"[Sync] Top 5 theo Volume Ratio (Ứng viên FAST):", flush=True)
                for r in top_vol:
                    print(f"  {r['symbol']}: VolRatio={r.get('volume_ratio')}, Score={r.get('master_score')}", flush=True)

    except Exception as e:
        print(f"[Sync] ❌ Lỗi không mong muốn trong pipeline: {e}", flush=True)
        if all_results and saved_count == 0:
            try:
                saved_count = save_results_to_db(all_results)
            except Exception as save_err:
                print(f"[Sync] Lưu dự phòng thất bại: {save_err}", flush=True)
    finally:
        # LUÔN LUÔN ghi nhận hoàn thành để UI không bị kẹt ở trạng thái 'running'
        sync_record.processed_symbols = len(symbols)
        sync_record.status = "completed"
        sync_record.completed_at = timezone.now()
        sync_record.save()
        print(f"[Sync] 🎉 ĐỒNG BỘ HOÀN TẤT 100%! Trạng thái: completed.\n", flush=True)

    elapsed = (datetime.now() - start_time).total_seconds()

    result = {
        "status": "success",
        "mode": mode,
        "total": len(all_results),
        "saved": saved_count,
        "market_rsi": market_rsi,
        "elapsed_seconds": elapsed,
    }

    print(f"[Sync] Completed in {elapsed:.1f}s. Saved {saved_count}/{len(all_results)} results")
    return result


def _clean_float(val, default: float = 0.0) -> float:
    if val is None or pd.isna(val):
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return default


def _clean_int(val, default: int = 0) -> int:
    if val is None or pd.isna(val):
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else int(f)
    except (ValueError, TypeError):
        return default


def _clean_opt_float(val) -> Optional[float]:
    if val is None or pd.isna(val):
        return None
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return None


def save_results_to_db(results: List[Dict[str, Any]]) -> int:
    """Lưu kết quả vào Database với kiểm tra chuẩn hóa kiểu dữ liệu"""
    saved = 0

    # Get VN30 list
    vn30_list = list(VN30_SYMBOLS)

    for data in results:
        try:
            symbol = data["symbol"]
            industry = data.get("industry", "Other")
            if not industry or industry == "Default":
                industry = "Other"
            avg_vol_val = _clean_float(data.get("avg_volume_value", 0))
            market_group = "VN30" if symbol in vn30_list else ("MIDCAP" if avg_vol_val >= 5 else "SMALL")

            # Save StockData
            stock, _ = StockData.objects.update_or_create(
                symbol=symbol,
                defaults={
                    "company_name": data.get("company_name", symbol) or symbol,
                    "industry": industry,
                    "market_group": market_group,
                    "price": _clean_float(data.get("price")),
                    "change_percent": _clean_float(data.get("change_percent")),
                    "volume": _clean_int(data.get("volume")),
                    "avg_volume_value": avg_vol_val,
                    "rsi": _clean_float(data.get("rsi"), 50.0),
                    "adx": _clean_float(data.get("adx"), 25.0),
                    "plus_di": _clean_float(data.get("plus_di")),
                    "minus_di": _clean_float(data.get("minus_di")),
                    "cmf": _clean_float(data.get("cmf")),
                    "atr": _clean_float(data.get("atr")),
                    "sma_10": _clean_float(data.get("sma_10")),
                    "sma_20": _clean_float(data.get("sma_20")),
                    "sma_50": _clean_float(data.get("sma_50")),
                    "bb_upper": _clean_float(data.get("bb_upper")),
                    "bb_middle": _clean_float(data.get("bb_middle")),
                    "bb_lower": _clean_float(data.get("bb_lower")),
                    "bb_percent": _clean_float(data.get("bb_percent"), 50.0),
                    "macd": _clean_float(data.get("macd")),
                    "macd_signal": _clean_float(data.get("macd_signal")),
                    "volume_ratio": _clean_float(data.get("volume_ratio"), 1.0),
                    # Advanced TA
                    "mfi": _clean_float(data.get("mfi"), 50.0),
                    "vwap": _clean_float(data.get("vwap"), _clean_float(data.get("price"))),
                    "vwap_status": data.get("vwap_status", "neutral") or "neutral",
                    "ichimoku_tenkan": _clean_float(data.get("ichimoku_tenkan")),
                    "ichimoku_kijun": _clean_float(data.get("ichimoku_kijun")),
                    "ichimoku_status": data.get("ichimoku_status", "neutral") or "neutral",
                    "supertrend": _clean_float(data.get("supertrend")),
                    "supertrend_signal": data.get("supertrend_signal", "neutral") or "neutral",
                    # Fundamental
                    "pe": _clean_opt_float(data.get("pe")),
                    "pb": _clean_opt_float(data.get("pb")),
                    "roe": _clean_opt_float(data.get("roe")),
                    "f_score": _clean_int(data.get("f_score")),
                    "profit_growth": _clean_opt_float(data.get("profit_growth")),
                }
            )

            # Save StockAnalysis with foreign metrics preservation
            existing_sa = StockAnalysis.objects.filter(symbol=stock).first()

            f_buy_streak = _clean_int(data.get("foreign_buy_streak"))
            if f_buy_streak == 0 and existing_sa and existing_sa.foreign_buy_streak:
                f_buy_streak = existing_sa.foreign_buy_streak

            f_net_val = _clean_float(data.get("latest_net_val"))
            if f_net_val == 0.0 and existing_sa and existing_sa.latest_net_val:
                f_net_val = existing_sa.latest_net_val

            f_net_val_2 = _clean_float(data.get("latest_net_val_2"))
            if f_net_val_2 == 0.0 and existing_sa and existing_sa.latest_net_val_2:
                f_net_val_2 = existing_sa.latest_net_val_2

            f_buy_val = _clean_float(data.get("foreign_buy_val"))
            if f_buy_val == 0.0 and existing_sa and existing_sa.foreign_buy_val:
                f_buy_val = existing_sa.foreign_buy_val

            f_sell_val = _clean_float(data.get("foreign_sell_val"))
            if f_sell_val == 0.0 and existing_sa and existing_sa.foreign_sell_val:
                f_sell_val = existing_sa.foreign_sell_val

            f_absorption = _clean_float(data.get("foreign_absorption_ratio"))
            if f_absorption == 0.0 and existing_sa and existing_sa.foreign_absorption_ratio:
                f_absorption = existing_sa.foreign_absorption_ratio

            f_share = _clean_float(data.get("foreign_trading_share"))
            if f_share == 0.0 and existing_sa and existing_sa.foreign_trading_share:
                f_share = existing_sa.foreign_trading_share

            f_trend = data.get("foreign_accumulated_trend") or (existing_sa.foreign_accumulated_trend if existing_sa else "NEUTRAL") or "NEUTRAL"
            if f_trend == "NEUTRAL" and existing_sa and existing_sa.foreign_accumulated_trend and existing_sa.foreign_accumulated_trend != "NEUTRAL":
                f_trend = existing_sa.foreign_accumulated_trend

            f_slope = _clean_float(data.get("foreign_accumulated_slope"))
            if f_slope == 0.0 and existing_sa and existing_sa.foreign_accumulated_slope:
                f_slope = existing_sa.foreign_accumulated_slope

            StockAnalysis.objects.update_or_create(
                symbol=stock,
                defaults={
                    "master_score": _clean_int(data.get("master_score"), 50),
                    "base_master_score": _clean_int(data.get("base_master_score", data.get("master_score")), 50),
                    "market_weight": _clean_int(data.get("market_weight")),
                    "technical_score": _clean_int(data.get("technical_score"), 50),
                    "fundamental_score": _clean_int(data.get("fundamental_score"), 50),
                    "signal": data.get("signal", "WAIT") or "WAIT",
                    "entry_price": _clean_float(data.get("entry_price")),
                    "stop_loss": _clean_float(data.get("stop_loss")),
                    "trailing_sl": _clean_float(data.get("trailing_sl")),
                    "take_profit": _clean_float(data.get("take_profit")),
                    "risk_reward_ratio": _clean_float(data.get("risk_reward_ratio")),
                    "rr_quality": data.get("rr_quality", "") or "",
                    "rr_quality_detail": data.get("rr_quality_detail", "") or "",
                    "rr_warning": data.get("rr_warning", "") or "",
                    "is_vetoed": bool(data.get("is_vetoed", False)),
                    "veto_reason": data.get("veto_reason", "") or "",
                    "is_fast_pick": bool(data.get("is_fast_pick", False)),
                    "is_short_term_qualified": bool(data.get("is_short_term_qualified", False)),
                    "is_slow_mode": bool(data.get("is_slow_mode", False)),
                    "is_high_risk": bool(data.get("is_high_risk", False)),
                    "is_market_high_risk": bool(data.get("is_market_high_risk", False)),
                    "stock_risk_level": data.get("stock_risk_level", "Medium") or "Medium",
                    "stock_risk_reason": data.get("stock_risk_reason", "") or "",
                    "has_inverted_sl": bool(data.get("has_inverted_sl", False)),
                    "is_safe_entry": bool(data.get("is_safe_entry", False)),
                    "has_high_resistance": bool(data.get("has_high_resistance", False)),
                    "avg_volume_value": avg_vol_val,
                    "trend_factor": _clean_float(data.get("trend_factor"), 0.6),
                    # Smart Money & Industry
                    "foreign_buy_streak": f_buy_streak,
                    "foreign_bonus": _clean_int(data.get("foreign_bonus")),
                    "foreign_master_modifier": _clean_int(data.get("foreign_master_modifier")),
                    "latest_net_val": f_net_val,
                    "foreign_absorption_ratio": f_absorption,
                    "latest_net_val_2": f_net_val_2,
                    "foreign_buy_val": f_buy_val,
                    "foreign_sell_val": f_sell_val,
                    "foreign_trading_share": f_share,
                    "foreign_accumulated_trend": f_trend,
                    "foreign_accumulated_slope": f_slope,
                    "industry_performance": _clean_float(data.get("industry_performance")),
                    "is_industry_leader": bool(data.get("is_industry_leader", True)),
                    # Real R:R
                    "hard_risk_pct": _clean_float(data.get("hard_risk_pct")),
                    "support_price": _clean_float(data.get("support_price")),
                    # P/E Industry & Early Exit
                    "pe_industry_avg": _clean_float(data.get("pe_industry_avg")),
                    "early_exit_trigger_pct": _clean_float(data.get("early_exit_trigger_pct"), 2.0),
                    "early_exit_drop_pct": _clean_float(data.get("early_exit_drop_pct"), 0.7),
                    "optimal_position_size": _clean_float(data.get("optimal_position_size")),
                    "account_balance": _clean_float(data.get("account_balance"), 100_000_000),
                    "risk_tolerance_pct": _clean_float(data.get("risk_tolerance_pct"), 2.0),
                    "estimated_days_to_target": _clean_float(data.get("estimated_days_to_target")),
                    "timeframe_label": data.get("timeframe_label", "") or "",
                    "timeframe_color": data.get("timeframe_color", "") or "",
                    "expected_profit_per_day": _clean_float(data.get("expected_profit_per_day")),
                    "upside_per_day": _clean_float(data.get("upside_per_day")),
                    "target_yield_pct": _clean_float(data.get("target_yield_pct")),
                    "criteria_met": _clean_int(data.get("criteria_met")),
                    "criteria_list": data.get("criteria_list") if isinstance(data.get("criteria_list"), list) else [],
                    "recommendation_label": data.get("recommendation_label", "") or "",
                    # Fair Value
                    "fv_daily": _clean_float(data.get("fv_daily")),
                    "valuation_status": data.get("valuation_status", "N/A") or "N/A",
                    "intrinsic_value": _clean_float(data.get("intrinsic_value")),
                    "sector_median_pe": _clean_float(data.get("sector_median_pe")),
                    "valuation_source": data.get("valuation_source", "static") or "static",
                    "valuation_cap_applied": bool(data.get("valuation_cap_applied", False)),
                    # Relative Strength (RS) - FIX v2
                    "rs_label": data.get("rs_label", "NEUTRAL") or "NEUTRAL",
                    "rs_bonus": _clean_int(data.get("rs_bonus")),
                    "trend": data.get("trend", "SIDEWAYS") or "SIDEWAYS",
                    "breakout_status": data.get("breakout_status", "") or "",
                    "market_rsi": _clean_float(data.get("market_rsi"), 50.0),
                    # Entry Quality & Scan Mode
                    "scan_mode": data.get("scan_mode", "EARLY_TREND") or "EARLY_TREND",
                    "entry_quality": data.get("entry_quality", "GOOD") or "GOOD",
                    "entry_quality_reason": data.get("entry_quality_reason", "") or "",
                }
            )
            saved += 1

        except Exception as e:
            print(f"[Sync] Error saving {data.get('symbol')}: {e}")

    return saved


def get_top_picks_from_db(limit: int = 5, include_vetoed: bool = False):
    """Lấy top picks từ Database - SECTOR DIVERSIFIED for Portfolio Shield
    
    Logic:
    1. Fetch a larger pool of stocks (non-vetoed for top picks, all for leaderboard)
    2. Apply sector cap: max 3 stocks per industry (for diversified picks)
    3. Calculate portfolio_health for concentration warning
    4. Return both picks and portfolio metadata
    """
    from django.db.models import F, ExpressionWrapper, FloatField  # pyright: ignore[reportMissingImports]
    
    # Portfolio Shield: Max stocks per sector
    MAX_STOCKS_PER_SECTOR = 3 if not include_vetoed else 100
    
    # Step A: Fetch pool
    if include_vetoed:
        base_qs = StockAnalysis.objects.select_related("symbol").all()
    else:
        base_qs = StockAnalysis.objects.select_related("symbol").filter(is_vetoed=False)
        if not base_qs.exists():
            # Fallback khi chưa có mã nào vượt qua VETO hoàn toàn
            base_qs = StockAnalysis.objects.select_related("symbol").all()

    if base_qs.filter(estimated_days_to_target__gt=0).exists() and not include_vetoed:
        analyses = base_qs.filter(
            estimated_days_to_target__gt=0
        ).annotate(
            profit_per_day_calc=ExpressionWrapper(
                F('take_profit') - F('entry_price'),
                output_field=FloatField()
            )
        ).order_by(
            '-profit_per_day_calc',
            '-master_score'
        )[:limit * 3]
    else:
        analyses = base_qs.order_by('-master_score')[:limit * 3]
    
    # Step B: Build diversified picks with sector cap
    diversified_picks = []
    sector_counts = {}  # {industry: count}
    
    for a in analyses:
        # Get industry - use get_industry() method for actual industry name
        s = a.symbol
        industry = s.get_industry() if hasattr(s, 'get_industry') else (getattr(s, 'industry', 'Unknown') or 'Unknown')
        
        # Check sector cap
        current_count = sector_counts.get(industry, 0)
        if current_count < MAX_STOCKS_PER_SECTOR:
            # Add to diversified picks
            diversified_picks.append(a)
            sector_counts[industry] = current_count + 1
        
        # Stop when we have enough
        if len(diversified_picks) >= limit:
            break
    
    # Step C: Build output list
    picks = []
    for a in diversified_picks:
        s = a.symbol
        # Use target_yield_pct from DB if available, otherwise calculate
        target_yield_pct = a.target_yield_pct if a.target_yield_pct else round((a.take_profit - (a.entry_price or s.price)) / (a.entry_price or s.price) * 100, 2) if a.take_profit and (a.entry_price or s.price) > 0 else 0
        days = a.estimated_days_to_target or 1
        profit_per_day = round(target_yield_pct / days, 2) if days > 0 else 0
        
        # Get industry using get_industry() method
        industry = s.get_industry() if hasattr(s, 'get_industry') else (getattr(s, 'industry', 'Unknown') or 'Unknown')
        
        picks.append({
            "symbol": s.symbol,
            "company_name": s.company_name,
            "industry": industry,
            "sector_group": getattr(s, 'sector_group', '') or '',
            "market_group": getattr(s, 'market_group', '') or '',
            "price": s.price,
            "change_percent": s.change_percent,
            # Target Yield
            "target_yield_pct": target_yield_pct,
            "profit_per_day": profit_per_day,
            # Technical
            "rsi": s.rsi,
            "adx": s.adx,
            "volume_ratio": s.volume_ratio,
            "cmf": s.cmf,
            "atr": s.atr,
            # Scores
            "master_score": a.master_score,
            "technical_score": a.technical_score,
            "fundamental_score": a.fundamental_score,
            "signal": a.signal,
            "risk_reward_ratio": a.risk_reward_ratio,
            "is_fast_pick": a.is_fast_pick,
            "criteria_met": a.criteria_met,
            "criteria_list": a.criteria_list,
            "trend": a.trend,
            "breakout_status": a.breakout_status,
            # Trading Levels
            "entry_price": a.entry_price,
            "stop_loss": a.stop_loss,
            "take_profit": a.take_profit,
            "estimated_days_to_target": a.estimated_days_to_target,
            "timeframe_label": a.timeframe_label,
            "timeframe_color": a.timeframe_color,
            # Risk
            "is_high_risk": a.is_high_risk,
            "is_market_high_risk": getattr(a, 'is_market_high_risk', False),
            "stock_risk_level": getattr(a, 'stock_risk_level', 'Medium'),
            # Meta
            "market_rsi": a.market_rsi,
            "market_regime": getattr(a, 'market_regime', 'NORMAL'),
            "market_regime_label": getattr(a, 'market_regime_label', 'Trung tính'),
            "market_regime_icon": getattr(a, 'market_regime_icon', '☁️'),
            "market_regime_color": getattr(a, 'market_regime_color', 'sky'),
            "market_position_scale": getattr(a, 'market_position_scale', 1.0),
            "market_tp_scale": getattr(a, 'market_tp_scale', 1.0),
            "market_veto_boost": getattr(a, 'market_veto_boost', False),
            "profit_growth": getattr(s, 'profit_growth', None),
            # Earning Guidance
            "annual_profit_plan": getattr(s, 'annual_profit_plan', None),
            "current_ytd_profit": getattr(s, 'current_ytd_profit', None),
            "profit_plan_completion": getattr(s, 'profit_plan_completion', None),
            "profit_plan_status": getattr(s, 'profit_plan_status', None),
            # Extra for criteria check
            "plus_di": s.plus_di,
            "minus_di": s.minus_di,
            "macd": s.macd,
            "macd_signal": s.macd_signal,
            "sma_20": s.sma_20,
            # Money Management / Early Exit
            "early_exit_trigger_pct": getattr(a, 'early_exit_trigger_pct', 2.0),
            "early_exit_drop_pct": getattr(a, 'early_exit_drop_pct', 0.7),
            "optimal_position_size": getattr(a, 'optimal_position_size', 0),
            "account_balance": getattr(a, 'account_balance', 100_000_000),
            "risk_tolerance_pct": getattr(a, 'risk_tolerance_pct', 2.0),
        })

    # Step D: Calculate Portfolio Health (Sector Concentration)
    portfolio_health = calculate_portfolio_health(sector_counts, len(picks))
    
    return picks, portfolio_health


def calculate_portfolio_health(sector_counts: Dict[str, int], total_picks: int) -> Dict[str, Any]:
    """
    Calculate portfolio health based on sector concentration.
    
    Args:
        sector_counts: Dict of {industry: count}
        total_picks: Total number of picks
        
    Returns:
        Dict with risk_level, risk_message, and suggested_sectors
    """
    # Low correlation mapping (Vietnam market)
    LOW_CORRELATION_MAP = {
        "Banking": ["Retail", "Technology", "Utilities", "FMCG"],
        "Real Estate": ["Technology", "Utilities", "Fishery", "Textile"],
        "Securities": ["Healthcare", "Agriculture", "Technology"],
        "Steel": ["Consumer Services", "Healthcare", "FMCG"],
        "Manufacturing": ["Retail", "Technology", "Utilities"],
        "Oil & Gas": ["Utilities", "Technology", "Healthcare"],
        "Retail": ["Banking", "Technology", "Healthcare"],
        "Technology": ["Banking", "Real Estate", "Utilities"],
        "Utilities": ["Technology", "Retail", "Banking"],
        "FMCG": ["Banking", "Technology", "Healthcare"],
        "Conglomerate": ["Technology", "Healthcare", "Utilities"],
        "Other": ["Technology", "Healthcare", "Retail"],
    }
    
    # Concentration threshold (40%)
    CONCENTRATION_THRESHOLD = 0.40
    
    if total_picks == 0:
        return {
            "risk_level": "LOW",
            "risk_message": "",
            "concentrated_sector": None,
            "concentration_pct": 0,
            "sector_distribution": {},
            "suggested_sectors": []
        }
    
    # Find max concentration
    max_sector = max(sector_counts.items(), key=lambda x: x[1])
    concentrated_sector = max_sector[0]
    max_count = max_sector[1]
    concentration_pct = max_count / total_picks
    
    # Check if concentration exceeds threshold
    is_high_concentration = concentration_pct > CONCENTRATION_THRESHOLD
    
    # Get low-correlation suggestions
    suggestions = LOW_CORRELATION_MAP.get(concentrated_sector, [])
    
    # Get sectors not currently in picks
    current_sectors = set(sector_counts.keys())
    suggested_sectors = [s for s in suggestions if s not in current_sectors][:3]
    
    # Determine risk level
    if concentration_pct > 0.6:  # >60% concentration
        risk_level = "HIGH"
    elif concentration_pct > CONCENTRATION_THRESHOLD:  # >40%
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    # Generate message
    if is_high_concentration:
        risk_message = f"Cảnh báo: Danh mục tập trung {int(concentration_pct * 100)}% vào nhóm {concentrated_sector}. Rủi ro hệ thống tăng cao."
    else:
        risk_message = ""
    
    return {
        "risk_level": risk_level,
        "risk_message": risk_message,
        "concentrated_sector": concentrated_sector if is_high_concentration else None,
        "concentration_pct": round(concentration_pct * 100, 1),
        "sector_distribution": sector_counts,
        "suggested_sectors": suggested_sectors,
        "total_picks": total_picks,
        "max_per_sector": max_count
    }


def get_sync_status() -> Optional[Dict[str, Any]]:
    """Lấy trạng thái sync cuối cùng"""
    try:
        sync = SyncStatus.objects.get(id=1)
        return {
            "status": sync.status,
            "is_running": sync.is_running,
            "progress_percent": sync.progress_percent,
            "total_symbols": sync.total_symbols,
            "processed_symbols": sync.processed_symbols,
            "started_at": str(sync.started_at) if sync.started_at else None,
            "completed_at": str(sync.completed_at) if sync.completed_at else None,
            "error_message": sync.error_message,
        }
    except:
        return None


def diagnose_stock(symbol: str) -> Dict[str, Any]:
    """
    Diagnostic tool cho một mã cổ phiếu - Single Stock Test Mode
    
    Chạy full sync pipeline cho một mã và trả về chi tiết tất cả các bước:
    - Raw data từ API
    - Valuation info (từ DB hay Config)
    - Computed FV Daily/Weekly
    - Criteria passed/failed
    - VETO reasons (if any)
    
    Args:
        symbol: Mã cổ phiếu cần diagnose
        
    Returns:
        Dict chứa chi tiết đầy đủ của quá trình tính toán
    """
    print(f"\n{'='*80}")
    print(f"🔍 DIAGNOSTIC REPORT: {symbol}")
    print(f"{'='*80}\n")
    
    result = {
        "symbol": symbol.upper(),
        "timestamp": datetime.now().isoformat(),
        "steps": {},
        "summary": {}
    }
    
    try:
        # ========== STEP 1: Get Raw Technical Data ==========
        print("[1/5] Fetching technical data...")
        result["steps"]["technical"] = {}
        
        try:
            from vnstock import Quote
            q = Quote(symbol=symbol, source="vci")
            df = q.history(
                start=(datetime.now() - pd.Timedelta(days=90)).strftime("%Y-%m-%d"),
                end=datetime.now().strftime("%Y-%m-%d"),
                interval="1D"
            )
            
            if df is not None and len(df) > 0:
                tech = calculate_technical_indicators(df)
                result["steps"]["technical"]["status"] = "success"
                result["steps"]["technical"]["raw_data"] = {
                    "price": float(df['close'].iloc[-1]),
                    "volume": int(df['volume'].iloc[-1]),
                    "rows": len(df)
                }
                result["steps"]["technical"]["indicators"] = tech
                print(f"  ✅ Price: {tech.get('price')}, RSI: {tech.get('rsi')}, CMF: {tech.get('cmf')}")
            else:
                result["steps"]["technical"]["status"] = "error"
                result["steps"]["technical"]["error"] = "No data returned"
                print(f"  ❌ No data returned")
                return result
        except Exception as e:
            result["steps"]["technical"]["status"] = "error"
            result["steps"]["technical"]["error"] = str(e)
            print(f"  ❌ Error: {e}")
            return result
        
        # ========== STEP 2: Get Raw Fundamental Data ==========
        print("[2/5] Fetching fundamental data...")
        result["steps"]["fundamental"] = {}
        
        try:
            fund_data = get_fundamental_data(symbol, fast_mode=False)
            result["steps"]["fundamental"]["status"] = "success"
            result["steps"]["fundamental"]["raw_data"] = {
                "roe": fund_data.get("roe"),
                "pe": fund_data.get("pe"),
                "pb": fund_data.get("pb"),
                "f_score": fund_data.get("f_score"),
                "industry": fund_data.get("industry"),
                "profit_growth": fund_data.get("profit_growth")
            }
            print(f"  ✅ ROE: {fund_data.get('roe')}, PE: {fund_data.get('pe')}, PB: {fund_data.get('pb')}")
            print(f"  ✅ F-Score: {fund_data.get('f_score')}, Industry: {fund_data.get('industry')}")
        except Exception as e:
            result["steps"]["fundamental"]["status"] = "error"
            result["steps"]["fundamental"]["error"] = str(e)
            print(f"  ❌ Error: {e}")
            fund_data = {}
        
        # ========== STEP 3: Get Market RSI ==========
        print("[3/5] Fetching market RSI...")
        result["steps"]["market"] = {}
        
        market_rsi = get_market_rsi()
        result["steps"]["market"]["status"] = "success"
        result["steps"]["market"]["data"] = {"vnindex_rsi": market_rsi}
        print(f"  ✅ VNIndex RSI: {market_rsi}")
        
        # ========== STEP 4: Valuation Info ==========
        print("[4/5] Analyzing valuation...")
        result["steps"]["valuation"] = {}
        
        industry = fund_data.get('industry', 'Default')
        industry_key = next((k for k in INDUSTRY_CONFIG if k.lower() in industry.lower()), 'Default')
        
        # Get from IndustryValuation DB
        db_valuation = None
        try:
            iv = IndustryValuation.objects.filter(name=industry_key, is_active=True).first()
            if iv:
                db_valuation = {
                    "name": iv.name,
                    "median_pe": iv.median_pe,
                    "median_pb": iv.median_pb,
                    "stock_count": iv.stock_count,
                    "source": "database"
                }
        except:
            pass
        
        # Get from Config
        config_val = INDUSTRY_CONFIG.get(industry_key, INDUSTRY_CONFIG['Default'])
        
        # Get resolved valuation
        val_config = get_target_valuation(industry_key)
        
        result["steps"]["valuation"]["industry"] = industry_key
        result["steps"]["valuation"]["database_valuation"] = db_valuation
        result["steps"]["valuation"]["config_valuation"] = config_val
        result["steps"]["valuation"]["resolved"] = val_config
        
        print(f"  Industry: {industry_key}")
        print(f"  Database Median PE: {db_valuation.get('median_pe') if db_valuation else 'N/A'}")
        print(f"  Config Target: {config_val.get('target')}")
        print(f"  Resolved Target: {val_config.get('target')} (Source: {val_config.get('source')})")
        print(f"  Wealth Guard Cap Applied: {val_config.get('cap_applied')}")
        
        # ========== STEP 5: Compute Core Logic ==========
        print("[5/5] Running core computation...")
        result["steps"]["computation"] = {}
        
        try:
            # Get market group
            try:
                stock = StockData.objects.get(symbol=symbol.upper())
                market_group = stock.market_group or "UNKNOWN"
            except:
                market_group = "UNKNOWN"
            
            analysis = compute_core_logic(
                symbol=symbol,
                tech=tech,
                fund_data=fund_data,
                market_rsi=market_rsi,
                market_group=market_group,
                df=df if 'df' in dir() else None
            )
            
            result["steps"]["computation"]["status"] = "success"
            result["steps"]["computation"]["analysis"] = analysis
            
            print(f"\n  📊 COMPUTED VALUES:")
            print(f"  ├── FV Daily: {analysis.get('fv_daily')}")
            print(f"  ├── Intrinsic Value: {analysis.get('intrinsic_value')}")
            print(f"  ├── Take Profit: {analysis.get('take_profit')}")
            print(f"  ├── Stop Loss: {analysis.get('stop_loss')}")
            print(f"  └── R:R Ratio: {analysis.get('risk_reward_ratio')}")
            
        except Exception as e:
            result["steps"]["computation"]["status"] = "error"
            result["steps"]["computation"]["error"] = str(e)
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # ========== SUMMARY ==========
        print(f"\n{'='*80}")
        print("📋 SUMMARY")
        print(f"{'='*80}")
        
        if result["steps"].get("computation", {}).get("status") == "success":
            analysis = result["steps"]["computation"]["analysis"]
            
            print(f"\n  🎯 SIGNAL: {analysis.get('signal')}")
            print(f"  📈 MASTER SCORE: {analysis.get('master_score')}")
            print(f"  📉 TECH SCORE: {analysis.get('tech_score')}")
            print(f"  💰 FUND SCORE: {analysis.get('fund_score')}")
            
            # Criteria
            criteria_met = analysis.get('criteria_met', 0)
            criteria_list = analysis.get('criteria_list', [])
            print(f"\n  ✅ CRITERIA MET: {criteria_met}/12")
            if criteria_list:
                print(f"     {', '.join(criteria_list)}")
            
            # VETO
            is_vetoed = analysis.get('is_vetoed', False)
            veto_reason = analysis.get('veto_reason', '')
            print(f"\n  {'🚫 VETO' if is_vetoed else '✅ NO VETO'}")
            if is_vetoed:
                print(f"     Reason: {veto_reason}")
            
            # Fair Value Status
            print(f"\n  💵 VALUATION:")
            print(f"     Status: {analysis.get('valuation_status')}")
            print(f"     Source: {analysis.get('valuation_source')}")
            print(f"     Sector Median PE: {analysis.get('sector_median_pe')}")
            
            result["summary"] = {
                "signal": analysis.get('signal'),
                "master_score": analysis.get('master_score'),
                "is_vetoed": is_vetoed,
                "veto_reason": veto_reason,
                "valuation_status": analysis.get('valuation_status'),
                "valuation_source": analysis.get('valuation_source')
            }
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        result["error"] = str(e)
        import traceback
        traceback.print_exc()
    
    return result


# ============== DEEP FUNDAMENTAL SYNC (PHASE 2 - TOP 30) ==============

def update_deep_sync_progress(
    step: str,
    message: str,
    progress: int = -1,
    symbol: str = "",
    processed: int = 0,
    total: int = 0,
    status: str = "running",
    error: str = ""
) -> None:
    """Ghi nhận tiến độ đồng bộ chuyên sâu vào file sync_progress.json và SyncStatus DB."""
    import json
    from django.conf import settings
    files_to_update = [
        os.path.join(os.path.dirname(__file__), "sync_progress.json"),
        os.path.join(getattr(settings, "BASE_DIR", os.path.dirname(os.path.dirname(__file__))), "sync_progress.json"),
    ]
    data = {
        "status": status,
        "step": step,
        "message": message,
        "progress": progress,
        "symbol": symbol,
        "processed": processed,
        "total": total,
        "error": error,
        "timestamp": timezone.now().isoformat()
    }
    for pf in files_to_update:
        try:
            with open(pf, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
        except Exception as e:
            pass

    try:
        sync_obj, _ = SyncStatus.objects.get_or_create(id=1)
        sync_obj.status = status
        sync_obj.total_symbols = total if total > 0 else sync_obj.total_symbols
        sync_obj.processed_symbols = processed
        if status == "running" and not sync_obj.started_at:
            sync_obj.started_at = timezone.now()
        elif status == "completed":
            sync_obj.completed_at = timezone.now()
        if error:
            sync_obj.error_message = error
        sync_obj.save()
    except Exception as e:
        print(f"[Deep Sync] Không thể lưu SyncStatus DB: {e}", flush=True)


def calculate_piotroski_f_score_from_df(df_quarters: pd.DataFrame, is_bank: bool = False) -> tuple[int, dict]:
    """
    Tính điểm Piotroski F-Score (0-9) chuẩn mực từ DataFrame tỷ số tài chính 4 quý.
    
    9 Tiêu chí:
    1. ROA > 0 (Khả năng sinh lời)
    2. CFO / Dòng tiền thuần > 0
    3. Delta ROA > 0 (ROA cải thiện so với kỳ trước)
    4. Accrual: CFO > ROA (Chất lượng lợi nhuận)
    5. Delta Leverage <= 0 (Đòn bẩy nợ giảm hoặc duy trì ở mức an toàn)
    6. Delta Liquidity >= 0 (Khả năng thanh toán hiện thời cải thiện)
    7. Shares Dilution = 0 (Không phát hành pha loãng cổ phiếu)
    8. Delta Margin >= 0 (Biên lợi nhuận gộp/thuần tăng)
    9. Delta Turnover >= 0 (Vòng quay tài sản tăng)
    """
    if df_quarters is None or df_quarters.empty:
        return 0, {}

    try:
        # Sắp xếp các quý theo thứ tự tăng dần thời gian (cũ -> mới)
        df_sorted = df_quarters.sort_index(ascending=True)
        if len(df_sorted) < 1:
            return 0, {}

        q0 = df_sorted.iloc[-1]  # Quý gần nhất
        q1 = df_sorted.iloc[-2] if len(df_sorted) >= 2 else None  # Quý liền kề trước đó

        def _val(row, *col_names, default=0.0):
            if row is None:
                return default
            for name in col_names:
                if name in row and pd.notna(row[name]):
                    try:
                        return float(row[name])
                    except (ValueError, TypeError):
                        pass
            return default

        breakdown = {}

        # 1. ROA > 0
        roa_q0 = _val(q0, 'ROA (%)', 'ROA', 'roa', default=0.0)
        breakdown['f1_roa_positive'] = 1 if roa_q0 > 0 else 0

        # 2. Cash Flow / Margin > 0
        p_cf = _val(q0, 'Price/Cash Flow', 'P/Cashflow', default=0.0)
        net_margin_q0 = _val(q0, 'After-tax Profit Margin (%)', 'Biên lợi nhuận thuần (%)', default=0.0)
        breakdown['f2_cfo_positive'] = 1 if (p_cf > 0 or net_margin_q0 > 0) else 0

        # 3. Delta ROA > 0 (So với quý trước)
        if q1 is not None:
            roa_q1 = _val(q1, 'ROA (%)', 'ROA', 'roa', default=0.0)
            breakdown['f3_delta_roa'] = 1 if roa_q0 >= roa_q1 else 0
        else:
            breakdown['f3_delta_roa'] = 1 if roa_q0 > 1.5 else 0

        # 4. Accrual: Chất lượng lợi nhuận
        breakdown['f4_accrual'] = 1 if (net_margin_q0 >= roa_q0 or p_cf > 0) else 0

        # 5. Delta Leverage: Tỷ lệ nợ/VCSH không tăng đột biến
        de_q0 = _val(q0, 'Debt/Equity', 'Tỷ lệ nợ/Vốn CSH', default=0.0)
        if q1 is not None:
            de_q1 = _val(q1, 'Debt/Equity', 'Tỷ lệ nợ/Vốn CSH', default=0.0)
            breakdown['f5_delta_leverage'] = 1 if (de_q0 <= de_q1 or de_q0 < 1.2) else 0
        else:
            breakdown['f5_delta_leverage'] = 1 if de_q0 < 1.5 else 0

        # 6. Delta Liquidity: Tỷ lệ thanh toán hiện thời
        if is_bank:
            car = _val(q0, 'CAR', default=0.0)
            ldr = _val(q0, 'LDR (%)', default=80.0)
            breakdown['f6_liquidity'] = 1 if (car >= 8.0 or ldr <= 85.0) else 0
        else:
            cr_q0 = _val(q0, 'Current Ratio', 'Tỷ lệ thanh toán hiện thời', default=1.0)
            if q1 is not None:
                cr_q1 = _val(q1, 'Current Ratio', 'Tỷ lệ thanh toán hiện thời', default=1.0)
                breakdown['f6_liquidity'] = 1 if (cr_q0 >= cr_q1 or cr_q0 >= 1.2) else 0
            else:
                breakdown['f6_liquidity'] = 1 if cr_q0 >= 1.1 else 0

        # 7. Shares Dilution: Không bị pha loãng vốn
        sh_q0 = _val(q0, 'Outstanding Shares (mil)', default=0.0)
        if q1 is not None:
            sh_q1 = _val(q1, 'Outstanding Shares (mil)', default=0.0)
            breakdown['f7_no_dilution'] = 1 if (sh_q1 == 0 or sh_q0 <= sh_q1 * 1.02) else 0
        else:
            breakdown['f7_no_dilution'] = 1

        # 8. Delta Margin: Biên lợi nhuận cải thiện
        if is_bank:
            nim_q0 = _val(q0, 'Net Interest Margin', default=0.0)
            if q1 is not None:
                nim_q1 = _val(q1, 'Net Interest Margin', default=0.0)
                breakdown['f8_delta_margin'] = 1 if nim_q0 >= nim_q1 else 0
            else:
                breakdown['f8_delta_margin'] = 1 if nim_q0 >= 3.0 else 0
        else:
            gm_q0 = _val(q0, 'Gross Margin (%)', 'Biên lợi nhuận gộp (%)', default=0.0)
            if q1 is not None:
                gm_q1 = _val(q1, 'Gross Margin (%)', 'Biên lợi nhuận gộp (%)', default=0.0)
                breakdown['f8_delta_margin'] = 1 if (gm_q0 >= gm_q1 or gm_q0 >= 20.0) else 0
            else:
                breakdown['f8_delta_margin'] = 1 if gm_q0 >= 15.0 else 0

        # 9. Delta Turnover: Vòng quay tài sản cải thiện
        to_q0 = _val(q0, 'Asset Turnover', 'Vòng quay tài sản', default=0.0)
        if q1 is not None:
            to_q1 = _val(q1, 'Asset Turnover', 'Vòng quay tài sản', default=0.0)
            breakdown['f9_delta_turnover'] = 1 if to_q0 >= to_q1 else 0
        else:
            breakdown['f9_delta_turnover'] = 1 if to_q0 >= 0.4 else 0

        total_f_score = sum(breakdown.values())
        return total_f_score, breakdown

    except Exception as e:
        print(f"[calculate_piotroski_f_score_from_df] Lỗi tính F-Score: {e}", flush=True)
        return 0, {}


def _sanitize_for_json(obj: Any) -> Any:
    """Làm sạch các giá trị NaN/Inf, NumPy types thành chuẩn JSON hợp lệ cho SQLite JSONField."""
    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(x) for x in obj]
    elif obj is None or pd.isna(obj):
        return None
    elif isinstance(obj, (np.floating, float)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif hasattr(obj, 'isoformat') and callable(getattr(obj, 'isoformat', None)):
        return obj.isoformat()
    return obj

def sync_top30_deep_fundamentals(target_symbols: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Tiến trình đồng bộ chuyên sâu BCTC (Giai đoạn 2) chỉ dành cho Top 30 cổ phiếu được chọn lọc.
    
    Đặc điểm kỹ thuật:
    - Trích xuất 4 quý BCTC từ vnstock_data (VCI ratio) gồm 56 chỉ số tài chính.
    - Token Bucket & Anti-Ban Rate Limiter: Pacing sleep 2.5 - 3.8s ngẫu nhiên, Cooldown 5s mỗi batch 5 mã.
    - Exponential Backoff Retry (10s, 20s, 40s) khi gặp lỗi mạng/quá tải.
    - Tính toán Piotroski F-Score (0-9) chuẩn xác 9 tiêu chí.
    - Cập nhật tăng trưởng lợi nhuận QoQ/YoY.
    - Lưu trữ chuẩn hóa vào QuarterlyFinancial, StockData, StockAnalysis.
    - Đánh giá lại VETO Rule Nhóm 3 (Sức khỏe tài chính).
    - Cập nhật tiến độ realtime cho UI polling.
    """
    import random
    import time
    from django import db
    from dashboard.models import QuarterlyFinancial, StockData, StockAnalysis

    print(f"\n{'='*75}", flush=True)
    print(f"🚀 [DEEP FUNDAMENTAL SYNC] BẮT ĐẦU ĐỒNG BỘ CHUYÊN SÂU BCTC TOP 30 CỔ PHIẾU", flush=True)
    print(f"{'='*75}\n", flush=True)

    # 1. Xác định danh sách 30 mã mục tiêu
    if not target_symbols:
        # Ưu tiên lấy từ StockAnalysis các mã không bị VETO xếp theo master_score
        selected = list(
            StockAnalysis.objects.filter(is_vetoed=False)
            .order_by('-master_score')
            .values_list('symbol__symbol', flat=True)[:30]
        )
        if len(selected) < 30:
            # Bổ sung các mã còn lại xếp theo master_score
            more = list(
                StockAnalysis.objects.exclude(symbol__symbol__in=selected)
                .order_by('-master_score')
                .values_list('symbol__symbol', flat=True)[:(30 - len(selected))]
            )
            selected.extend(more)

        # Nếu DB trống, dùng danh sách 30 mã cốt lõi thị trường
        if len(selected) < 10:
            core_30 = [
                "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "HDB", "STB", "TPB",
                "FPT", "HPG", "VNM", "MSN", "MWG", "PNJ", "GAS", "PLX", "VHM", "VIC",
                "VRE", "SSI", "VCI", "VND", "DGC", "GEX", "REE", "KDH", "NLG", "PVD"
            ]
            selected = core_30
        target_symbols = selected[:30]

    total_symbols = len(target_symbols)
    update_deep_sync_progress(
        step="starting",
        message=f"Bắt đầu đồng bộ chuyên sâu BCTC 4 quý cho {total_symbols} mã hàng đầu...",
        progress=0,
        symbol="",
        processed=0,
        total=total_symbols,
        status="running"
    )

    success_count = 0
    failed_count = 0
    results_detail = []

    # Import thư viện vnstock_data
    try:
        from vnstock_data import Finance
    except ImportError as e:
        err_msg = f"Không tìm thấy thư viện vnstock_data: {e}"
        print(f"[Deep Sync] ❌ {err_msg}", flush=True)
        update_deep_sync_progress("error", err_msg, 0, status="failed", error=err_msg)
        return {"status": "error", "message": err_msg}

    # Đóng kết nối cũ để an toàn luồng
    db.close_old_connections()

    for idx, symbol in enumerate(target_symbols, 1):
        symbol = symbol.strip().upper()
        print(f"\n[Deep Sync {idx}/{total_symbols}] >>> Đang xử lý: {symbol}...", flush=True)

        update_deep_sync_progress(
            step="fetching",
            message=f"[{idx}/{total_symbols}] Đang tải BCTC 4 quý từ VCI cho {symbol}...",
            progress=int(((idx - 1) / total_symbols) * 100),
            symbol=symbol,
            processed=idx - 1,
            total=total_symbols,
            status="running"
        )

        # 2. Token Bucket Rate-Limiting & Jitter Sleep
        # Tránh gửi dồn dập, tuân thủ quota 60 req/phút của Community Tier
        jitter_sleep = random.uniform(2.5, 3.8)
        time.sleep(jitter_sleep)

        # Cooldown bổ sung mỗi 5 mã
        if idx > 1 and idx % 5 == 1:
            print(f"[Deep Sync] ⏱️ Cooldown 5s sau 5 request để giải phóng kết nối...", flush=True)
            time.sleep(5.0)

        # 3. Request với Exponential Backoff Retry (Max 3 lần)
        max_retries = 3
        df_ratio = None
        last_error = None

        for attempt in range(max_retries):
            try:
                f_client = Finance(source='VCI', symbol=symbol)
                # Lấy 8 quý để có đủ dữ liệu so sánh YoY và tính toán F-Score
                df_ratio = f_client.ratio(period='quarter', limit=8)
                if df_ratio is not None and not df_ratio.empty:
                    break
            except Exception as e:
                last_error = e
                wait_time = 10 * (2 ** attempt)
                print(f"[Deep Sync] ⚠️ {symbol} gặp lỗi ở lần thử {attempt + 1}: {e}. Chờ {wait_time}s retry...", flush=True)
                time.sleep(wait_time)

        if df_ratio is None or df_ratio.empty:
            failed_count += 1
            print(f"[Deep Sync] ❌ Thất bại khi lấy BCTC cho {symbol}: {last_error}", flush=True)
            results_detail.append({"symbol": symbol, "status": "failed", "error": str(last_error)})
            continue

        # 4. Trích xuất và chuẩn hóa dữ liệu 4 quý gần nhất
        try:
            # Lấy 4 quý mới nhất (tail(4))
            recent_quarters_df = df_ratio.tail(4)
            is_bank = (symbol in ['VCB', 'BID', 'CTG', 'TCB', 'MBB', 'ACB', 'VPB', 'HDB', 'STB', 'TPB', 'SHB', 'LPB', 'MSB', 'VIB', 'OCB'])

            # Tính Piotroski F-Score từ 4 quý
            f_score, f_score_breakdown = calculate_piotroski_f_score_from_df(recent_quarters_df, is_bank=is_bank)

            latest_quarter_key = recent_quarters_df.index[-1]
            latest_row = recent_quarters_df.iloc[-1]

            def _get_f(row, *col_names, default=None):
                for col in col_names:
                    if col in row and pd.notna(row[col]):
                        try:
                            return float(row[col])
                        except:
                            pass
                return default

            latest_roe = _get_f(latest_row, 'ROE (%)', 'ROE', 'roe')
            if latest_roe is not None and abs(latest_roe) < 1.0:
                latest_roe = latest_roe * 100.0

            latest_roa = _get_f(latest_row, 'ROA (%)', 'ROA', 'roa')
            if latest_roa is not None and abs(latest_roa) < 1.0:
                latest_roa = latest_roa * 100.0

            latest_pe = _get_f(latest_row, 'P/E', 'pe')
            latest_pb = _get_f(latest_row, 'P/B', 'pb')
            latest_de = _get_f(latest_row, 'Debt to Equity', 'Debt/Equity', 'Tỷ lệ nợ/Vốn CSH', default=0.0)

            # Tính tăng trưởng lợi nhuận QoQ
            profit_growth = None
            if len(recent_quarters_df) >= 2:
                prev_row = recent_quarters_df.iloc[-2]
                current_margin = _get_f(latest_row, 'After-tax Profit Margin (%)', 'Biên lợi nhuận thuần (%)', default=0.0)
                prev_margin = _get_f(prev_row, 'After-tax Profit Margin (%)', 'Biên lợi nhuận thuần (%)', default=0.0)
                if prev_margin != 0:
                    profit_growth = round(((current_margin - prev_margin) / abs(prev_margin)) * 100, 2)

            # Lưu từng quý vào bảng QuarterlyFinancial
            for period_str in recent_quarters_df.index:
                q_row = recent_quarters_df.loc[period_str]
                period_str_clean = str(period_str).strip()

                # Xác định ngày kết thúc quý
                q_date = None
                try:
                    year_part = period_str_clean[:4]
                    if 'Q1' in period_str_clean: q_date = f"{year_part}-03-31"
                    elif 'Q2' in period_str_clean: q_date = f"{year_part}-06-30"
                    elif 'Q3' in period_str_clean: q_date = f"{year_part}-09-30"
                    elif 'Q4' in period_str_clean: q_date = f"{year_part}-12-31"
                    else: q_date = f"{year_part}-12-31"
                except:
                    q_date = timezone.now().strftime("%Y-%m-%d")

                q_roe = _get_f(q_row, 'ROE (%)', 'ROE', 'roe')
                if q_roe is not None and abs(q_roe) < 1.0:
                    q_roe = q_roe * 100.0

                q_roa = _get_f(q_row, 'ROA (%)', 'ROA', 'roa')
                if q_roa is not None and abs(q_roa) < 1.0:
                    q_roa = q_roa * 100.0

                q_pe = _get_f(q_row, 'P/E', 'pe')
                q_pb = _get_f(q_row, 'P/B', 'pb')

                QuarterlyFinancial.objects.update_or_create(
                    symbol=symbol,
                    quarter=period_str_clean,
                    defaults={
                        'quarter_date': q_date,
                        'roe': q_roe,
                        'roa': q_roa,
                        'pe': q_pe,
                        'pb': q_pb,
                        'f_score': f_score,
                        'profit_growth': profit_growth,
                        'is_vetoed': (q_roe is not None and q_roe < 10),
                        'veto_reason': "ROE < 10%" if (q_roe is not None and q_roe < 10) else "",
                        'vci_data': _sanitize_for_json(q_row.to_dict()) if hasattr(q_row, 'to_dict') else {}
                    }
                )

            # 5. Cập nhật vào StockData
            stock_data_obj = StockData.objects.filter(symbol=symbol).first()
            if stock_data_obj:
                if latest_roe is not None:
                    stock_data_obj.roe = round(latest_roe, 2)
                if latest_pe is not None:
                    stock_data_obj.pe = round(latest_pe, 2)
                if latest_pb is not None:
                    stock_data_obj.pb = round(latest_pb, 2)
                stock_data_obj.f_score = f_score
                if profit_growth is not None:
                    stock_data_obj.profit_growth = profit_growth
                    stock_data_obj.profit_growth_note = "QoQ"
                stock_data_obj.save()

            # 6. Đánh giá lại VETO và cập nhật StockAnalysis
            analysis_obj = StockAnalysis.objects.filter(symbol__symbol=symbol).first()
            if analysis_obj and stock_data_obj:
                fund_dict = {
                    "roe": latest_roe,
                    "roa": latest_roa,
                    "pe": latest_pe,
                    "pb": latest_pb,
                    "f_score": f_score,
                    "profit_growth": profit_growth,
                    "debt_equity": latest_de,
                    "is_new_listing": stock_data_obj.is_new_listing
                }
                tech_dict = {
                    "price": stock_data_obj.price,
                    "cmf": stock_data_obj.cmf,
                    "rsi": stock_data_obj.rsi,
                    "adx": stock_data_obj.adx,
                    "sma_50": stock_data_obj.sma_50,
                    "sma_200": 0,
                    "bb_percent": stock_data_obj.bb_percent,
                    "volume_ratio": stock_data_obj.volume_ratio,
                    "volume": stock_data_obj.volume
                }
                veto_res = check_health_veto(
                    tech=tech_dict,
                    fund_data=fund_dict,
                    market_rsi=analysis_obj.market_rsi or 50.0,
                    avg_volume_value=stock_data_obj.avg_volume_value,
                    industry=stock_data_obj.industry or ""
                )

                analysis_obj.f_score = f_score
                analysis_obj.roe = latest_roe
                analysis_obj.profit_growth = profit_growth
                analysis_obj.is_vetoed = veto_res.get('is_vetoed', False)
                analysis_obj.veto_reason = veto_res.get('veto_reason', "")
                analysis_obj.veto_reasons = veto_res.get('veto_reasons', [])
                analysis_obj.save()

            success_count += 1
            print(f"[Deep Sync] ✅ Đã lưu BCTC cho {symbol}: ROE={latest_roe}%, F-Score={f_score}/9, P/E={latest_pe}, P/B={latest_pb}", flush=True)

            results_detail.append({
                "symbol": symbol,
                "status": "success",
                "roe": latest_roe,
                "f_score": f_score,
                "pe": latest_pe,
                "pb": latest_pb,
                "profit_growth": profit_growth
            })

            update_deep_sync_progress(
                step="progress",
                message=f"[{idx}/{total_symbols}] Đã đồng bộ BCTC cho {symbol} (ROE: {latest_roe or 0:.1f}%, F-Score: {f_score}/9)",
                progress=int((idx / total_symbols) * 100),
                symbol=symbol,
                processed=idx,
                total=total_symbols,
                status="running"
            )

        except Exception as e:
            failed_count += 1
            print(f"[Deep Sync] ❌ Lỗi xử lý dữ liệu cho {symbol}: {e}", flush=True)
            results_detail.append({"symbol": symbol, "status": "failed", "error": str(e)})

    # 7. Cập nhật lại sector median benchmarks sau khi có BCTC mới
    try:
        sync_sector_benchmarks()
    except Exception as e:
        print(f"[Deep Sync] Không thể sync sector benchmarks: {e}", flush=True)

    # 8. Hoàn tất toàn bộ tiến trình
    final_message = f"✅ Hoàn tất đồng bộ chuyên sâu BCTC Top 30: Thành công {success_count}/{total_symbols} mã!"
    print(f"\n{'='*75}", flush=True)
    print(f"[DEEP FUNDAMENTAL SYNC] {final_message}", flush=True)
    print(f"{'='*75}\n", flush=True)

    update_deep_sync_progress(
        step="done",
        message=final_message,
        progress=100,
        symbol="",
        processed=total_symbols,
        total=total_symbols,
        status="completed"
    )

    return {
        "status": "success",
        "processed_count": total_symbols,
        "success_count": success_count,
        "failed_count": failed_count,
        "details": results_detail
    }
