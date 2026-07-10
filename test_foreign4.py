from vnstock_data import Market
import pandas as pd
m = Market()

for sym in ['VHM', 'VIC']:
    print(f'=== {sym} ===')

    # 1. Check session_stats columns vs code
    sess = m.equity(sym).session_stats()
    cols = sess.columns.tolist()
    print(f'  Has total_value? {"total_value" in cols}')
    print(f'  Has total_match_value? {"total_match_value" in cols}')
    if 'total_match_value' in cols:
        v = sess['total_match_value'].iloc[0]
        print(f'  total_match_value: {v:,.0f} VND = {v/1e12:.2f}T (very large = cumulative)')

    # 2. Check OHLCV for today's total value
    from datetime import datetime, timedelta
    ohlcv = m.equity(sym).ohlcv(
        start=(datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
        end=datetime.now().strftime('%Y-%m-%d')
    )
    if ohlcv is not None and not ohlcv.empty:
        latest = ohlcv.iloc[-1]
        print(f'  OHLCV latest: {latest.to_dict()}')
        price = float(latest.get('close', 0) or latest.get('close', 0) or 0)
        vol = float(latest.get('volume', 0) or 0)
        print(f'  OHLCV price={price}, volume={vol}, estimated_total={price*vol/1e9:.2f}B')

    # 3. Check foreign_flow net_val values
    ff = m.equity(sym).foreign_flow()
    if ff is not None and not ff.empty:
        ff2 = ff.sort_values('trading_date', ascending=False).reset_index(drop=True)
        print(f'  FF shape: {ff2.shape}')
        for i in range(min(3, len(ff2))):
            row = ff2.iloc[i]
            d = str(row['trading_date'])[:10]
            net_b = row['net_val'] / 1e9
            print(f'    [{i}] {d}: net_val={net_b:.2f}B')
        print(f'  -> latest_net_val_2 (row 1): {ff2.iloc[1]["net_val"]/1e9:.2f}B')
    else:
        print('  FF: EMPTY')

    print()
