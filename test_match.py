from vnstock_data import Market
from datetime import datetime, timedelta
import pandas as pd

m = Market()
for sym in ['VHM', 'VIC']:
    print(f'=== {sym} ===')

    ff = m.equity(sym).foreign_flow()
    ff = ff.sort_values('trading_date', ascending=False).reset_index(drop=True)
    net_val = ff.iloc[0]['net_val']
    net_vol = ff.iloc[0]['net_vol']
    latest_date = ff.iloc[0]['trading_date']

    ohlcv = m.equity(sym).ohlcv(
        start=(pd.Timestamp(latest_date) - pd.Timedelta(days=3)).strftime('%Y-%m-%d'),
        end=(pd.Timestamp(latest_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    )
    date_col = 'time' if 'time' in ohlcv.columns else 'trading_date'
    ohlcv2 = ohlcv.sort_values(date_col, ascending=False).reset_index(drop=True)

    # Find the exact matching row
    matching_row = None
    for _, row in ohlcv2.iterrows():
        row_date = pd.Timestamp(row[date_col]).normalize()
        if row_date == pd.Timestamp(latest_date).normalize():
            matching_row = row
            break

    if matching_row is not None:
        vol = float(matching_row.get('volume', 0))
        price = float(matching_row.get('close', 0))
        print(f'  Matched date: {matching_row[date_col]}, vol={vol}, close={price}')
        print(f'  FF net_val={net_val/1e9:.2f}B, net_vol={net_vol:,.0f}')
        print(f'  Absorption (net_vol/vol): {abs(net_vol)/vol*100:.1f}%')
        print(f'  Absorption (net_val/(close*vol)): {abs(net_val)/(price*vol)*100:.1f}%')
    else:
        print(f'  No matching date found for {latest_date}')
        print(f'  OHLCV dates: {ohlcv2[date_col].head(5).tolist()}')

    print()
