from django.urls import path

from .views import history, home, run_function, save_preset, load_presets, market_overview, backtest, top_picks, scan_vn30_api

urlpatterns = [
    path("", home, name="home"),
    path("overview/", market_overview, name="market_overview"),
    path("top-picks/", top_picks, name="top_picks"),
    path("api/scan/vn30/", scan_vn30_api, name="scan_vn30_api"),
    path("history/", history, name="history"),
    path("backtest/", backtest, name="backtest"),
    path("run/<str:function_id>/", run_function, name="run_function"),
    path("preset/save/", save_preset, name="save_preset"),
    path("preset/load/<str:function_id>/", load_presets, name="load_presets"),
]
