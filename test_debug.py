"""
Debug screener - xem nó trả về những mã nào
"""
import warnings
warnings.filterwarnings('ignore')

from vnstock_data import Insights

ins = Insights()
df = ins.screener().filter()

print(f"Screener trả về {len(df)} cổ phiếu")
print("\nDanh sách symbol:")
print(df['symbol'].tolist())

print("\n\nTop 10 RS:")
top_rs = df.nlargest(10, 'rs_3m')[['symbol', 'rs_3m', 'outperforms_index_3m', 'price_return_3m']]
print(top_rs.to_string())
