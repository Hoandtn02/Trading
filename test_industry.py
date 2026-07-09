from vnstock_data import Insights
ins = Insights()
df = ins.screener().filter()
if df is not None:
    for sym in ['VJC', 'MSB', 'LPB', 'VHM']:
        match = df[df['symbol'] == sym]
        if not match.empty:
            ind_en = match.iloc[0].get('industry_en', 'N/A')
            vi_sec = match.iloc[0].get('vi_sector', 'N/A')
            print(f'{sym}: industry_en={ind_en}, vi_sector={vi_sec}')
