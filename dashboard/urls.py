from django.urls import path

from .views import history, home, run_function, save_preset, load_presets, market_overview, backtest, top_picks, scan_vn30_api, stock_list, export_stocks_csv, export_stock_detail_csv

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
]
