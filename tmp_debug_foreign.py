from vnstock_data import Market
import pandas as pd
import numpy as np

mkt = Market()
symbol = 'HDB'
df = mkt.equity(symbol).foreign_flow()

if df is None or df.empty:
    print('No data')
else:
    date_col = 'trading_date' if 'trading_date' in df.columns else 'time'
    df = df.sort_values(date_col, ascending=False).reset_index(drop=True)
    row0 = df.iloc[0]
    row1 = df.iloc[1] if len(df) > 1 else None

    def _net(row):
        return float(row.get('net_val', 0) or row.get('fr_net_value_total', 0) or 0)

    print('columns:', list(df.columns))
    print('row0 type:', type(row0))
    print('buy_val in index:', 'buy_val' in row0.index)
    print('sell_val in index:', 'sell_val' in row0.index)
    print('row0 buy_val raw:', repr(row0.get('buy_val')))
    print('row0 sell_val raw:', repr(row0.get('sell_val')))
    print('row0 net_val raw:', repr(row0.get('net_val')))

    buy_val = 0.0
    sell_val = 0.0
    for col in ['buy_val', 'fr_buy_value_matched', 'buy_value']:
        if col in row0.index:
            v = row0.get(col)
            print(f'  trying {col}: {repr(v)}')
            buy_val = float(v or 0)
            print(f'  -> buy_val after float: {buy_val}')
            if buy_val:
                break

    for col in ['sell_val', 'fr_sell_value_matched', 'sell_value']:
        if col in row0.index:
            v = row0.get(col)
            print(f'  trying {col}: {repr(v)}')
            sell_val = float(v or 0)
            print(f'  -> sell_val after float: {sell_val}')
            if sell_val:
                break

    print('final buy_val:', buy_val)
    print('final sell_val:', sell_val)

    latest_date = row0['trading_date']
    ohlcv = mkt.equity(symbol).ohlcv(
        start=(pd.Timestamp(latest_date) - pd.Timedelta(days=3)).strftime('%Y-%m-%d'),
        end=(pd.Timestamp(latest_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    )
    print('ohlcv empty:', ohlcv.empty if ohlcv is not None else 'None')
    total_val = 0.0
    if ohlcv is not None and not ohlcv.empty:
        date_col_ohlcv = 'time' if 'time' in ohlcv.columns else 'trading_date'
        ohlcv2 = ohlcv.sort_values(date_col_ohlcv, ascending=False).reset_index(drop=True)
        for _, row in ohlcv2.iterrows():
            row_date = pd.Timestamp(row[date_col_ohlcv]).normalize()
            print('ohlcv row_date', row_date, 'latest_date', pd.Timestamp(latest_date).normalize())
            if row_date == pd.Timestamp(latest_date).normalize():
                vol = float(row.get('volume', 0))
                close_k = float(row.get('close', 0) or 0)
                print('matched ohlcv row:', row.to_dict())
                print('close_k', close_k, 'vol', vol)
                if close_k > 0 and vol > 0:
                    close_vnd = close_k * 1000
                    total_val = close_vnd * vol
                break
    print('total_val', total_val)
    print('absorption', round(abs(_net(row0)) / total_val * 100, 2) if total_val > 0 else 0.0)
    print('trading_share', round((buy_val + sell_val) / total_val * 100, 2) if total_val > 0 and (buy_val or sell_val) else (abs(_net(row0)) / total_val * 100 if total_val > 0 else 0.0))

    work_df = df.head(min(30, len(df))).copy()
    work_df['_net'] = work_df.apply(lambda r: _net(r), axis=1)
    work_df = work_df.sort_values(date_col, ascending=True).reset_index(drop=True)
    cum_net = work_df['_net'].cumsum()
    print('cum_net len', len(cum_net), 'last', cum_net.iloc[-1] if len(cum_net) else None)
    if len(cum_net) >= 5:
        x = np.arange(len(cum_net))
        slope = np.polyfit(x, cum_net.values, 1)[0] if len(cum_net) > 1 else 0.0
        slope_pct = slope / (abs(cum_net.iloc[-1]) if cum_net.iloc[-1] != 0 else 1)
        print('slope', round(float(slope), 2), 'slope_pct', slope_pct)
        trend = 'ACCUMULATING' if slope_pct > 0.05 else 'DISTRIBUTING' if slope_pct < -0.05 else 'NEUTRAL'
        print('trend', trend)
    else:
        print('not enough rows for trend')
