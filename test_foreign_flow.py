from vnstock_data import Market
import pandas as pd

mkt = Market()
symbols = ["VCB", "FPT"]

for sym in symbols:
    try:
        df = mkt.equity(sym).foreign_flow()
        print(f"{sym}: type={type(df)}, empty={df.empty if df is not None else 'None'}")
        if df is not None and not df.empty:
            print(df.head(3).to_string())
        else:
            print("No data")
    except Exception as e:
        print(f"{sym}: ERROR={e}")
