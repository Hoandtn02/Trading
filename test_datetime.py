import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '.')

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'vnstock_web.settings'
import django
django.setup()

from datetime import date
from dashboard.runners import (
    real_index_history, real_stock_historical, real_stock_quote_realtime,
    real_stock_intraday, real_stock_financial_reports, real_stock_financial_ratios,
    real_listing_by_group, real_listing_all_symbols, real_listing_by_exchange,
    real_listing_all_indices, real_company_profile, real_stock_news,
    real_price_board, real_cw_listing, real_cw_price,
    real_gold_domestic, real_gold_global, real_forex_vcb,
    real_vn30f_history, real_futures_listing, real_fund_etf_listing,
    real_fund_open_listing, real_fund_nav, real_gov_bonds_listing,
    real_crypto_price, real_financial_news, real_corporate_disclosure
)

params_date = {'start_date': date(2025, 4, 1), 'end_date': date(2026, 4, 15)}

tests = [
    ("VNIndex",              lambda: real_index_history(symbol='VNINDEX', source='vci', **params_date, resolution='daily')),
    ("HNXIndex",             lambda: real_index_history(symbol='HNXIndex', source='vci', **params_date, resolution='daily')),
    ("StockHistorical",      lambda: real_stock_historical(symbol='ACB', source='vci', **params_date, resolution='daily')),
    ("StockQuoteRT",         lambda: real_stock_quote_realtime(symbol='ACB', source='vci')),
    ("StockIntraday",        lambda: real_stock_intraday(symbol='ACB', source='vci')),
    ("ListingAllSymbols",     lambda: real_listing_all_symbols(source='vci')),
    ("ListingByExchange",     lambda: real_listing_by_exchange(source='vci')),
    ("ListingByGroup",       lambda: real_listing_by_group(group='VN30', source='vci')),
    ("ListingAllIndices",     lambda: real_listing_all_indices()),
    ("CompanyProfile",       lambda: real_company_profile(symbol='ACB', source='vci')),
    ("StockNews",            lambda: real_stock_news(symbol='ACB', source='vci')),
    ("PriceBoard",          lambda: real_price_board(symbols='ACB,VNM,FPT', source='kbs')),
    ("FinancialReports",     lambda: real_stock_financial_reports(symbol='ACB', source='vci', report_type='income_statement', period='quarter')),
    ("FinancialRatios",     lambda: real_stock_financial_ratios(symbol='ACB', source='vci', period='quarter')),
    ("GoldDomestic",         lambda: real_gold_domestic()),
    ("ForexVCB",             lambda: real_forex_vcb()),
    ("GovBonds",             lambda: real_gov_bonds_listing(source='vci')),
    ("CryptoPrice",         lambda: real_crypto_price()),
    ("FinancialNews",       lambda: real_financial_news()),
    ("CorporateDisclosure",  lambda: real_corporate_disclosure(symbol='ACB')),
]

for name, fn in tests:
    try:
        r = fn()
        kind = r.get('kind', '?')
        rows = r.get('rows', [])
        cols = r.get('columns', [])
        err = r.get('data', {}).get('error', '')
        if err:
            print(f"KO  {name:25s} ERROR: {err[:80]}")
        elif rows:
            print(f"OK  {name:25s} rows={len(rows)}, cols={len(cols)}")
        else:
            print(f"OK  {name:25s} rows=0 (kind={kind}, no error)")
    except Exception as e:
        print(f"ERR {name:25s} EXCEPTION: {str(e)[:100]}")
