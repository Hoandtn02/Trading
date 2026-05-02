from django.urls import path  # pyright: ignore[reportMissingImports]

from .views import history, home, run_function, save_preset, load_presets, market_overview, backtest, top_picks, scan_vn30_api, stock_list, export_stocks_csv, export_stock_detail_csv, strategy_lab, api_simulate, api_backtest, api_get_stock_data, api_get_all_symbols, wealth_guard_backtest, api_wealth_guard_data, fetch_quarterly_financial

urlpatterns = [
    path("", home, name="home"),
    path("overview/", market_overview, name="market_overview"),
    path("top-picks/", top_picks, name="top_picks"),
    path("stocks/", stock_list, name="stock_list"),
    path("stocks/export/", export_stocks_csv, name="export_stocks_csv"),
    path("stocks/<str:symbol>/export/", export_stock_detail_csv, name="export_stock_detail_csv"),
    path("api/scan/vn30/", scan_vn30_api, name="scan_vn30_api"),
    path("history/", history, name="history"),
    path("backtest/", backtest, name="backtest"),
    path("run/<str:function_id>/", run_function, name="run_function"),
    path("preset/save/", save_preset, name="save_preset"),
    path("preset/load/<str:function_id>/", load_presets, name="load_presets"),
    path("strategy-lab/", strategy_lab, name="strategy_lab"),
    path("api/simulate/", api_simulate, name="api_simulate"),
    path("api/backtest/", api_backtest, name="api_backtest"),
    path("api/lab/stock-data/", api_get_stock_data, name="api_get_stock_data"),
    path("api/lab/symbols/", api_get_all_symbols, name="api_get_all_symbols"),
    path("wealth-guard-backtest/", wealth_guard_backtest, name="wealth_guard_backtest"),
    path("api/wealth-guard/data/", api_wealth_guard_data, name="api_wealth_guard_data"),
    path("api/quarterly-financial/", fetch_quarterly_financial, name="fetch_quarterly_financial"),
    path('wealth-guard-backtest/', wealth_guard_backtest, name='wealth_guard_backtest'),
    path('api/wealth-guard-data/', api_wealth_guard_data, name='api_wealth_guard_data'),
]
