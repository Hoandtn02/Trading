"""
Sync foreign ranking data vào DB (chạy thủ công, cache vĩnh viễn)
Usage: python manage.py sync_foreign_ranking
"""
import warnings
warnings.filterwarnings('ignore')  # Suppress vnstock warnings

from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import StockData, StockAnalysis
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

# Progress file path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROGRESS_FILE = os.path.join(PROJECT_ROOT, 'sync_progress.json')

def update_progress(step, message, progress=-1):
    """Update progress file for real-time display"""
    import json
    data = {'status': 'running', 'step': step, 'message': message}
    if progress >= 0:
        data['progress'] = progress
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass


class Command(BaseCommand):
    help = 'Sync foreign ranking (buy/sell streaks, trading data) vào DB'

    def handle(self, *args, **options):
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
            for i, row in df_buy.iterrows():
                symbol = row.get('symbol', '')
                net_val = row.get('net_value', 0) or 0
                date = row.get('date', '')
                self._update_symbol(symbol, 'buy', net_val, date)
        
        # 2. Get foreign sell ranking  
        update_progress('sell', '📤 Đang lấy danh sách bán ròng...', 40)
        df_sell = insights.ranking().foreign_sell(limit=100)
        if df_sell is not None and not df_sell.empty:
            update_progress('sell', f'📤 Đang xử lý {len(df_sell)} mã bán ròng...', 45)
            for _, row in df_sell.iterrows():
                symbol = row.get('symbol', '')
                net_val = row.get('net_value', 0) or 0
                date = row.get('date', '')
                self._update_symbol(symbol, 'sell', net_val, date)
        
        # 3. Tính streaks từ historical data
        update_progress('streak', '📊 Đang tính chuỗi mua/bán...', 60)
        self._calculate_streaks()
        
        update_progress('done', '✅ Hoàn thành!', 100)

    def _update_symbol(self, symbol: str, action: str, net_val: float, date: str):
        """Cập nhật dữ liệu buy/sell cho symbol"""
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
            
            analysis.save()
        except Exception as e:
            logger.error(f"Error updating {symbol}: {e}")

    def _calculate_streaks(self):
        """Tính chuỗi mua/bán từ lịch sử khối ngoại"""
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
                
                buy_count = 0
                for _, row in hist.iterrows():
                    net = row.get('net_val', 0) or 0
                    if net > 0:
                        buy_count += 1
                    else:
                        break
                
                sell_count = 0
                for _, row in hist.iterrows():
                    net = row.get('net_val', 0) or 0
                    if net < 0:
                        sell_count += 1
                    else:
                        break
                
                analysis.foreign_buy_streak = buy_count
                analysis.foreign_sell_streak = sell_count
                analysis.save()
                
            except Exception:
                pass
            
            if (i + 1) % 10 == 0:
                pct = 60 + int(40 * (i + 1) / total)
                update_progress('streak', f'📊 Đã xử lý {i + 1}/{total} mã...', pct)
