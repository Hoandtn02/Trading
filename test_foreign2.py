from vnstock_data import Market
m = Market()

for sym in ['VHM', 'VIC']:
    print(f'=== {sym} ===')

    # Test session_stats
    try:
        sess = m.equity(sym).session_stats()
        if sess is None or sess.empty:
            print('  session_stats: EMPTY')
        else:
            print('  session_stats columns:', sess.columns.tolist())
            print('  session_stats:')
            print(sess.to_string())
    except Exception as e:
        print(f'  session_stats ERROR: {e}')

    # Test foreign_flow
    ff = m.equity(sym).foreign_flow()
    if ff is not None and not ff.empty:
        ff = ff.sort_values('trading_date', ascending=False).reset_index(drop=True)
        print('  foreign_flow top 3:')
        for i, row in ff.head(3).iterrows():
            net_b = row['net_val'] / 1e9
            d = row['trading_date']
            print(f'    {d}: net_val={net_b:.2f}B')

    print()
