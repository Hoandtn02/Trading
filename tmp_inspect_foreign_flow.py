from vnstock_data import Market
import pandas as pd

mkt = Market()
symbol = 'HDB'

df = mkt.equity(symbol).foreign_flow()
print('type:', type(df))
print('empty:', df.empty if df is not None else 'None')
if df is not None and not df.empty:
    print('columns:', list(df.columns))
    print(df.head(5).to_string(index=False))
else:
    print('No data')
