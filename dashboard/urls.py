from django.urls import path

from .views import history, home, run_function, save_preset, load_presets, market_overview, backtest

urlpatterns = [
    path("", home, name="home"),
    path("overview/", market_overview, name="market_overview"),
    path("history/", history, name="history"),
    path("backtest/", backtest, name="backtest"),
    path("run/<str:function_id>/", run_function, name="run_function"),
    path("preset/save/", save_preset, name="save_preset"),
    path("preset/load/<str:function_id>/", load_presets, name="load_presets"),
]
