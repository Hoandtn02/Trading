from vnstock_data import Market
import pandas as pd
m = Market()

for sym in ['VHM', 'VIC']:
    print(f'=== {sym} ===')

    # Test session_stats type
    sess = m.equity(sym).session_stats()
    print(f'  type: {type(sess)}')
    print(f'  shape: {getattr(sess, "shape", "N/A")}')
    if isinstance(sess, pd.DataFrame):
        print(f'  columns: {sess.columns.tolist()}')
        print(f'  head: {sess.head(1).to_dict()}')
    elif isinstance(sess, pd.Series):
        print(f'  index: {sess.index.tolist()}')
        print(f'  values: {sess.values}')

    # Test foreign_flow
    ff = m.equity(sym).foreign_flow()
    if ff is not None and not ff.empty:
        print(f'  ff columns: {ff.columns.tolist()}')
        print(f'  ff dtypes: {ff.dtypes.to_dict()}')
        ff2 = ff.sort_values('trading_date', ascending=False).reset_index(drop=True)
        print(f'  ff sorted top 3:')
        for i, row in ff2.head(3).iterrows():
            net_b = row['net_val'] / 1e9
            print(f'    {row["trading_date"]}: net_val={net_b:.2f}B')
    else:
        print('  ff: EMPTY')

    print()
