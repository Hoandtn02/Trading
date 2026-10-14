"""
Sync foreign ranking data - standalone script version
Chạy trực tiếp bằng: python sync_foreign_ranking.py
"""
import os
os.environ['PYTHONWARNINGS'] = 'ignore'

import warnings
warnings.filterwarnings('ignore')

import sys
import django

# Setup Django
PROJECT_ROOT = r"D:\OneDrive\Desktop\Trading-1"
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
django.setup()

import json
from datetime import datetime, timedelta
from dashboard.models import StockData, StockAnalysis

PROGRESS_FILE = os.path.join(PROJECT_ROOT, 'sync_progress.json')

print(f"Script started. Progress file: {PROGRESS_FILE}")

def update_progress(step, message, progress=-1):
    data = {'status': 'running', 'step': step, 'message': message}
    if progress >= 0:
        data['progress'] = progress
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(data, f)
            f.flush()
    except Exception as e:
        print(f"Progress update error: {e}", file=sys.stderr)

def update_symbol(symbol, action, net_val, date, ranking_date):
    try:
        stock_data = StockData.objects.filter(symbol=symbol).first()
        if not stock_data:
            return
        analysis, created = StockAnalysis.objects.get_or_create(symbol=stock_data)
        if action == 'buy':
            analysis.latest_net_val = abs(net_val)
            analysis.foreign_buy_val = abs(net_val)
        else:
            analysis.latest_net_val = -abs(net_val)
            analysis.foreign_sell_val = abs(net_val)
        # Lưu ngày dữ liệu ranking (ngày trading gần nhất từ Insights API)
        if ranking_date:
            analysis.foreign_ranking_date = ranking_date
        analysis.save()
    except Exception as e:
        print(f"Error updating {symbol}: {e}")

def calculate_streaks():
    from vnstock_data import Market
    mkt = Market()
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    
    analyses = StockAnalysis.objects.select_related('symbol').all()
    total = analyses.count()
    update_progress('streak', f'📊 Đang tính streak cho {total} mã...', 60)
    
    for i, analysis in enumerate(analyses):
        symbol = analysis.symbol.symbol
        try:
            hist = mkt.equity(symbol).foreign_flow(start=start, end=end)
            if hist is None or hist.empty:
                continue
            hist = hist.sort_values('trading_date', ascending=False)
            
            # Calculate buy streak - count consecutive days with net > 0
            # Buy streak START = the LAST day in the consecutive buy sequence (oldest day)
            buy_rows = []
            for idx, row in hist.iterrows():
                net = row.get('net_val', 0) or 0
                if net > 0:
                    buy_rows.append(row)
                else:
                    break
            
            buy_count = len(buy_rows)
            buy_start_date = buy_rows[-1]['trading_date'] if buy_rows else None  # Last = oldest = start
            
            # Calculate sell streak
            sell_rows = []
            for idx, row in hist.iterrows():
                net = row.get('net_val', 0) or 0
                if net < 0:
                    sell_rows.append(row)
                else:
                    break
            
            sell_count = len(sell_rows)
            sell_start_date = sell_rows[-1]['trading_date'] if sell_rows else None  # Last = oldest = start
            
            analysis.foreign_buy_streak = buy_count
            analysis.foreign_sell_streak = sell_count
            analysis.foreign_buy_streak_start = buy_start_date.date() if buy_start_date else None
            analysis.foreign_sell_streak_start = sell_start_date.date() if sell_start_date else None
            analysis.save()
        except Exception:
            pass
        
        if (i + 1) % 10 == 0:
            pct = 60 + int(40 * (i + 1) / total)
            update_progress('streak', f'📊 Đã xử lý {i + 1}/{total} mã...', pct)

def main():
    update_progress('starting', '🚀 Bắt đầu sync dữ liệu khối ngoại...', 0)
    
    try:
        from vnstock_data import Insights
    except ImportError:
        update_progress('error', 'vnstock_data not installed', 0)
        return

    insights = Insights()
    
    # 1. Get foreign buy ranking
    update_progress('buy', '📥 Đang lấy danh sách mua ròng...', 10)
    df_buy = insights.ranking().foreign_buy(limit=100)
    if df_buy is not None and not df_buy.empty:
        update_progress('buy', f'📥 Đang xử lý {len(df_buy)} mã mua ròng...', 15)
        # Lấy ngày dữ liệu từ dòng đầu tiên
        ranking_date = df_buy.iloc[0]['date'] if 'date' in df_buy.columns else None
        if isinstance(ranking_date, str):
            from datetime import datetime
            ranking_date = datetime.strptime(ranking_date, '%Y-%m-%d').date()
        for _, row in df_buy.iterrows():
            symbol = row.get('symbol', '')
            net_val = row.get('net_value', 0) or 0
            date = row.get('date', '')
            update_symbol(symbol, 'buy', net_val, date, ranking_date)
    
    # 2. Get foreign sell ranking  
    update_progress('sell', '📤 Đang lấy danh sách bán ròng...', 40)
    df_sell = insights.ranking().foreign_sell(limit=100)
    if df_sell is not None and not df_sell.empty:
        update_progress('sell', f'📤 Đang xử lý {len(df_sell)} mã bán ròng...', 45)
        for _, row in df_sell.iterrows():
            symbol = row.get('symbol', '')
            net_val = row.get('net_value', 0) or 0
            date = row.get('date', '')
            update_symbol(symbol, 'sell', net_val, date, None)
    
    # 3. Calculate streaks
    update_progress('streak', '📊 Đang tính chuỗi mua/bán...', 60)
    calculate_streaks()
    
    update_progress('done', '✅ Hoàn thành!', 100)
    print("Sync completed!")

if __name__ == '__main__':
    main()
