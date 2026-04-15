import requests
from io import BytesIO
import pandas as pd
import base64
import datetime
import warnings
from vnai import optimize_execution
warnings.filterwarnings("ignore", message="Workbook contains no default style, apply openpyxl's default")
from vnstock.core.utils.parser import camel_to_snake


@optimize_execution('MISC')
def vcb_exchange_rate(date='2023-12-26'):
    """
    Get exchange rate from Vietcombank for a specific date.

    Parameters:
        date (str): Date in format YYYY-MM-DD. If left blank, the current date will be used.
    """
    if date == '' or date is None:
        date = datetime.datetime.now().strftime('%d/%m/%Y')
    else:
        try:
            parsed = datetime.datetime.strptime(str(date), '%Y-%m-%d')
            date = parsed.strftime('%d/%m/%Y')
        except ValueError:
            try:
                parsed = datetime.datetime.strptime(str(date), '%d/%m/%Y')
                date = parsed.strftime('%d/%m/%Y')
            except ValueError:
                raise ValueError(f"Định dạng ngày không hợp lệ: {date}. Sử dụng YYYY-MM-DD hoặc DD/MM/YYYY.")

    url = f"https://www.vietcombank.com.vn/api/exchangerates/exportexcel?date={date}"
    response = requests.get(url, timeout=15)
    if response.status_code == 200:
        json_data = response.json()
        if not json_data or "Data" not in json_data or not json_data["Data"]:
            return pd.DataFrame(columns=['currency_code', 'currency_name', 'buy_cash', 'buy_transfer', 'sell', 'date'])
        excel_data = base64.b64decode(json_data["Data"])  # Decode base64 data
        columns = ['CurrencyCode', 'CurrencyName', 'Buy Cash', 'Buy Transfer', 'Sell' ]
        df = pd.read_excel(BytesIO(excel_data), sheet_name='ExchangeRate')
        df.columns = columns
        df = df.iloc[2:-4]
        df['date'] = date
        df.columns = [camel_to_snake(col) for col in df.columns]
        return df
    else:
        raise RuntimeError(f"Không lấy được dữ liệu từ VCB. HTTP {response.status_code}: {response.text[:200]}")