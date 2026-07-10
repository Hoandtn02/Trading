from vnstock_data import Market
from datetime import datetime, timedelta
import pandas as pd

m = Market()
for sym in ['VHM', 'VIC']:
    print(f'=== {sym} ===')

    ff = m.equity(sym).foreign_flow()
    ff = ff.sort_values('trading_date', ascending=False).reset_index(drop=True)
    net_val = ff.iloc[0]['net_val']
    latest_date = ff.iloc[0]['trading_date']

    ohlcv = m.equity(sym).ohlcv(
        start=(pd.Timestamp(latest_date) - pd.Timedelta(days=3)).strftime('%Y-%m-%d'),
        end=(pd.Timestamp(latest_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    )
    date_col = 'time' if 'time' in ohlcv.columns else 'trading_date'
    ohlcv2 = ohlcv.sort_values(date_col, ascending=False).reset_index(drop=True)
    latest = ohlcv2.iloc[0]

    print(f'  FF net_val = {net_val/1e9:.2f}B VND')
    print(f'  OHLCV cols: {ohlcv.columns.tolist()}')
    print(f'  OHLCV latest row:')
    for c in ohlcv.columns:
        v = latest[c]
        print(f'    {c}: {v}')

    # Tính absorption với các cột khác nhau
    vol_col = None
    for c in ['volume', 'vol', 'total_vol', 'total_volume', 'match_vol']:
        if c in ohlcv.columns:
            vol_col = c
            break

    if vol_col:
        vol = float(latest[vol_col])
        price = float(latest.get('close', 0) or 0)
        avg_price = float(latest.get('avg_price', 0) or 0) or price

        print(f'  Using vol_col={vol_col}, vol={vol}, close={price}, avg_price={avg_price}')

        # Option A: dùng avg_price
        total_a = price * vol
        total_b = avg_price * vol
        abs_a = abs(net_val) / total_a * 100
        abs_b = abs(net_val) / total_b * 100

        print(f'  Absorption (close*vol={total_a/1e9:.2f}B): {abs_a:.1f}%')
        print(f'  Absorption (avg*vol={total_b/1e9:.2f}B): {abs_b:.1f}%')
        print(f'  Absorption (net_vol/vol): {abs(ff.iloc[0]["net_vol"])/vol*100:.1f}%')

    print()
