from vnstock_data import Market
import pandas as pd

m = Market()
for sym in ['VHM', 'VIC']:
    print(f'=== {sym} ===')

    ff = m.equity(sym).foreign_flow()
    ff = ff.sort_values('trading_date', ascending=False).reset_index(drop=True)

    # Lay cot buy_val, sell_val de xac dinh don vi
    row = ff.iloc[0]
    print(f'  FF net_val={row["net_val"]:,.0f}')
    print(f'  FF buy_val={row["buy_val"]:,.0f}')
    print(f'  FF sell_val={row["sell_val"]:,.0f}')

    # Tinh gia tri trung binh
    if row['buy_vol'] > 0:
        avg_buy = row['buy_val'] / row['buy_vol']
        print(f'  FF avg buy price = {avg_buy:,.0f} VND/share')

    # OHLCV
    ohlcv = m.equity(sym).ohlcv(
        start='2026-07-05', end='2026-07-09'
    )
    ohlcv2 = ohlcv.sort_values('time', ascending=False).reset_index(drop=True)
    latest = ohlcv2.iloc[0]
    print(f'  OHLCV close={latest["close"]}')
    print(f'  OHLCV volume={latest["volume"]:,.0f}')

    # So sanh
    close_price = float(latest['close'])
    net_val = float(row['net_val'])
    net_vol = float(row['net_vol'])
    vol = float(latest['volume'])

    print(f'  close*vol = {close_price*vol:,.0f}')
    print(f'  net_val = {net_val:,.0f}')
    print(f'  ratio net_val/(close*vol) = {net_val/(close_price*vol):.4f}')
    print(f'  ratio net_vol/vol = {abs(net_vol)/vol:.4f}')
    print()
