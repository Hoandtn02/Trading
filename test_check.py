"""
Check individual stock data
"""
import warnings
warnings.filterwarnings('ignore')

from vnstock_data import Quote

q = Quote(symbol='VCB')

print("Check individual stock data:")
for sym in ['VCB', 'FPT', 'VNM', 'SAB']:
    df = q.history(symbol=sym, length='5D', interval='1D')
    print(f"{sym}: close = {df['close'].tolist()}")
