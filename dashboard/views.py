from __future__ import annotations

import json
import time
import sqlite3
from datetime import date, datetime
from functools import wraps

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.db import OperationalError
from django.views.decorators.csrf import csrf_exempt

from .forms import DynamicFunctionForm
from .models import ExecutionResult, FunctionDefinition, FunctionGroup, UserPreset
from .services import get_function_definition, iter_registry_functions, run_registry_function
from dashboard.sync_service import sync_market_data, get_top_picks_from_db, get_sync_status


def retry_on_db_lock(max_retries: int = 3, delay: float = 0.5):
    """Decorator to retry database operations on lock errors."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        last_error = e
                        time.sleep(delay * (attempt + 1))
                        continue
                    raise
            raise last_error
        return wrapper
    return decorator


def _seed_missing_registry_rows() -> None:
    @retry_on_db_lock(max_retries=3, delay=0.3)
    def _seed():
        for item in iter_registry_functions():
            group_data = item["group"]
            group, _ = FunctionGroup.objects.get_or_create(
                slug=group_data["slug"],
                defaults={"name": group_data["name"], "description": group_data.get("description", "")},
            )
            new_schema = item.get("param_schema", {})

            # Use update_or_create to ensure param_schema is always synced
            fd, created = FunctionDefinition.objects.update_or_create(
                function_id=item["function_id"],
                defaults={
                    "group": group,
                    "label": item["label"],
                    "description": item.get("description", ""),
                    "runner_path": item["runner_path"],
                    "param_schema": new_schema,
                    "output_type": item.get("output_type", "table"),
                    "is_active": item.get("status") != "disabled",
                },
            )
            # Always sync param_schema from registry (source of truth)
            if fd.param_schema != new_schema:
                fd.param_schema = new_schema
                fd.save(update_fields=["param_schema"])
    _seed()


def _serialize_params(params: dict) -> dict:
    """Convert date/datetime values to strings for JSON serialization."""
    def _conv(v):
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v
    return {k: _conv(v) for k, v in params.items()}


def home(request: HttpRequest) -> HttpResponse:
    _seed_missing_registry_rows()

    selected_group = request.GET.get("group", "").strip()
    selected_status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()
    selected_function_id = request.GET.get("function", "").strip()

    groups = FunctionGroup.objects.prefetch_related("functions").order_by("name")
    all_items = iter_registry_functions()

    # Start: all function IDs
    filtered_ids = [item["function_id"] for item in all_items]

    # Filter by group
    if selected_group:
        filtered_ids = [
            i["function_id"] for i in iter_registry_functions()
            if i["group"]["slug"] == selected_group
        ]

    # Filter by status
    if selected_status:
        filtered_ids = [
            i["function_id"] for i in iter_registry_functions()
            if i.get("status", "planned") == selected_status
            and i["function_id"] in filtered_ids
        ]

    # Filter by text search
    if query:
        filtered_ids = [
            i["function_id"] for i in iter_registry_functions()
            if (query.lower() in i["label"].lower() or query.lower() in i.get("description", "").lower())
            and i["function_id"] in filtered_ids
        ]

    # Only show functions that are in filtered_ids
    functions = FunctionDefinition.objects.filter(function_id__in=filtered_ids).order_by("group__name", "label")

    # Selected function: from URL param, or first in filtered list
    selected_function = (
        FunctionDefinition.objects.filter(function_id=selected_function_id).first()
        or (functions.first() if filtered_ids else None)
    )

    form = DynamicFunctionForm(selected_function.function_id) if selected_function else None

    return render(
        request,
        "dashboard/home.html",
        {
            "groups": groups,
            "functions": functions,
            "selected_function": selected_function,
            "form": form,
            "selected_group": selected_group,
            "selected_status": selected_status,
            "query": query,
        },
    )


@csrf_exempt
@retry_on_db_lock(max_retries=3, delay=0.5)
def run_function(request: HttpRequest, function_id: str) -> HttpResponse:
    _seed_missing_registry_rows()
    definition = get_function_definition(function_id)
    if definition is None:
        return render(request, "dashboard/result_partial.html", {"error": f"Không tìm thấy function: {function_id}"})

    form = DynamicFunctionForm(function_id, request.POST)
    if not form.is_valid():
        return render(request, "dashboard/result_partial.html", {"error": form.errors.as_json()})

    try:
        payload = run_registry_function(function_id, form.cleaned_data)
        function_obj = FunctionDefinition.objects.get(function_id=function_id)
        ExecutionResult.objects.create(function=function_obj, params=_serialize_params(form.cleaned_data), status="success", result_payload=payload)
        return render(request, "dashboard/result_partial.html", {"result": payload})
    except Exception as exc:
        function_obj = FunctionDefinition.objects.get(function_id=function_id)
        ExecutionResult.objects.create(function=function_obj, params=_serialize_params(form.cleaned_data), status="error", result_payload={"error": str(exc)})
        return render(request, "dashboard/result_partial.html", {"error": str(exc)})


def history(request: HttpRequest) -> HttpResponse:
    _seed_missing_registry_rows()
    executions = ExecutionResult.objects.select_related("function", "function__group").order_by("-created_at")[:100]
    return render(request, "dashboard/history.html", {"executions": executions})


def save_preset(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    function_id = request.POST.get("function_id", "").strip()
    name = request.POST.get("name", "").strip()
    params_raw = request.POST.get("params", "{}")

    if not function_id or not name:
        return render(request, "dashboard/result_partial.html", {"error": "Thiếu function_id hoặc tên preset."})

    import json
    try:
        params = json.loads(params_raw)
    except json.JSONDecodeError:
        params = {}

    function_obj = FunctionDefinition.objects.filter(function_id=function_id).first()
    if not function_obj:
        return render(request, "dashboard/result_partial.html", {"error": f"Không tìm thấy function: {function_id}"})

    preset = UserPreset.objects.create(function=function_obj, name=name, params=params)
    return render(request, "dashboard/result_partial.html", {"result": {"saved": True, "preset_id": preset.id, "name": preset.name}})


def load_presets(request: HttpRequest, function_id: str) -> HttpResponse:
    presets = UserPreset.objects.filter(function__function_id=function_id).order_by("-created_at")
    html_lines = []
    if presets:
        for p in presets:
            params_json = json.dumps(p.params)
            html_lines.append(
                f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #1e2b42;">'
                f'<div><strong>{p.name}</strong><br><span class="muted compact">{p.created_at.strftime("%Y-%m-%d %H:%M")}</span></div>'
                f'<div style="display:flex;gap:8px;">'
                f'<button class="btn-secondary" style="padding:6px 10px;font-size:12px;" onclick="loadPreset({params_json})">Áp dụng</button>'
                f'</div></div>'
            )
    else:
        html_lines.append('<p class="muted compact">Chưa có preset nào cho chức năng này.</p>')
    return HttpResponse("\n".join(html_lines), content_type="text/html")


def market_overview(request: HttpRequest) -> HttpResponse:
    """Market Overview Dashboard - Shows all products from Phase 1-5"""
    return render(request, "dashboard/market_overview.html", {})


@csrf_exempt
def top_picks(request: HttpRequest) -> HttpResponse:
    """
    Top Picks Dashboard - Database-First Architecture v7
    Mục tiêu: Tìm mã tốt nhất để đánh T+ (Swing Trading)

    v7 Features:
    - Database-First: Đọc từ SQLite thay vì gọi API trực tiếp
    - Sync Engine: ThreadPoolExecutor để đồng bộ song song
    - Status Indicator: Hiển thị thời gian cập nhật
    """
    # Lấy sync status
    sync_status = get_sync_status()
    is_data_available = sync_status and sync_status.get("completed_at")

    if is_data_available:
        # Đọc từ Database - CỰC NHANH
        top_picks = get_top_picks_from_db(limit=8)
        all_stocks = get_top_picks_from_db(limit=15)

        # Thống kê
        from .models import StockAnalysis
        total = StockAnalysis.objects.count()
        vetoed = StockAnalysis.objects.filter(is_vetoed=True).count()
        fast = StockAnalysis.objects.filter(is_fast_pick=True, is_vetoed=False).count()

        # Market RSI từ record đầu tiên
        market_rsi = top_picks[0]["market_rsi"] if top_picks else 50

        context = {
            "top_picks": top_picks,
            "all_stocks": all_stocks,
            "scan_time": sync_status.get("completed_at", "")[:19] if sync_status.get("completed_at") else "N/A",
            "market_rsi": market_rsi,
            "market_status": "SELL ZONE" if market_rsi > 70 else "NEUTRAL",
            "bullish_count": StockAnalysis.objects.filter(signal__in=["BUY", "STRONG_BUY"]).count(),
            "vetoed_count": vetoed,
            "fast_count": fast,
            "total_scanned": total,
            "high_risk_count": StockAnalysis.objects.filter(is_high_risk=True).count(),
            "is_syncing": sync_status.get("is_running", False),
            "sync_progress": sync_status.get("progress_percent", 0),
            "has_market_warning": market_rsi > 70,
            "market_warning_message": f"⚠️ SELL ZONE - VNIndex RSI: {market_rsi:.0f}" if market_rsi > 70 else "",
            "has_hot_pick": any(p["master_score"] >= 80 for p in top_picks),
        }
    else:
        # Không có dữ liệu
        context = {
            "top_picks": [],
            "all_stocks": [],
            "scan_time": "Chưa đồng bộ",
            "market_rsi": 50,
            "market_status": "NEUTRAL",
            "bullish_count": 0,
            "vetoed_count": 0,
            "fast_count": 0,
            "total_scanned": 0,
            "high_risk_count": 0,
            "is_syncing": False,
            "sync_progress": 0,
            "has_market_warning": False,
            "market_warning_message": "",
            "has_hot_pick": False,
        }

    return render(request, "dashboard/top_picks.html", context)


@csrf_exempt
def scan_vn30_api(request: HttpRequest) -> HttpResponse:
    """
    API endpoint để trigger sync và lấy kết quả
    POST: Trigger sync (chạy ngầm)
    GET: Lấy kết quả từ DB
    """
    import json

    if request.method == "POST":
        # Trigger sync in background
        from django.contrib.auth.models import AnonymousUser
        import threading

        def run_sync():
            sync_market_data(force=True)

        thread = threading.Thread(target=run_sync)
        thread.daemon = True
        thread.start()

        return JsonResponse({
            "status": "started",
            "message": "Đang đồng bộ dữ liệu 100 mã..."
        })

    # GET: Lấy kết quả từ DB - CỰC NHANH
    sync_status = get_sync_status()
    top_picks = get_top_picks_from_db(limit=5)

    from .models import StockAnalysis
    total = StockAnalysis.objects.count()
    vetoed = StockAnalysis.objects.filter(is_vetoed=True).count()
    fast = StockAnalysis.objects.filter(is_fast_pick=True, is_vetoed=False).count()
    market_rsi = top_picks[0]["market_rsi"] if top_picks else 50

    return JsonResponse({
        "status": "success",
        "scan_time": sync_status.get("completed_at", "")[:19] if sync_status and sync_status.get("completed_at") else "N/A",
        "market_status": "SELL ZONE" if market_rsi > 70 else "NEUTRAL",
        "market_rsi": market_rsi,
        "top_picks": top_picks,
        "bullish_count": StockAnalysis.objects.filter(signal__in=["BUY", "STRONG_BUY"]).count(),
        "fast_count": fast,
        "vetoed_count": vetoed,
        "high_risk_count": StockAnalysis.objects.filter(is_high_risk=True).count(),
        "is_syncing": sync_status.get("is_running", False) if sync_status else False,
        "sync_progress": sync_status.get("progress_percent", 0) if sync_status else 0,
        "has_market_warning": market_rsi > 70,
        "market_warning_message": f"⚠️ SELL ZONE - VNIndex RSI: {market_rsi:.0f}" if market_rsi > 70 else "",
        "has_hot_pick": any(p["master_score"] >= 80 for p in top_picks),
    })


@csrf_exempt
def backtest(request: HttpRequest) -> HttpResponse:
    """Backtesting Dashboard - For validating predictions"""
    if request.method == "POST":
        # Handle AJAX backtest request
        symbol = request.POST.get("symbol", "VCB")
        start_date = request.POST.get("start_date", "")
        end_date = request.POST.get("end_date", "")
        strategy = request.POST.get("strategy", "ma_cross")
        capital = float(request.POST.get("capital", 10000000))
        
        try:
            result = run_backtest(symbol, start_date, end_date, strategy, capital)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({"status": "error", "error": str(e)})
    
    symbol = request.GET.get("symbol", "VCB")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")
    
    return render(request, "dashboard/backtest.html", {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
    })


def run_backtest(symbol: str, start_date: str, end_date: str, strategy: str, capital: float) -> dict:
    """
    Run backtest for a given symbol and strategy.
    Returns trading statistics and equity curve.
    """
    import pandas as pd
    from dashboard.analyzers import StockAnalyzer
    
    try:
        # Get historical data
        analyzer = StockAnalyzer(period_ta=90)
        ohlcv = analyzer._get_ohlcv(symbol)
        
        if ohlcv is None or len(ohlcv) < 50:
            return {"status": "error", "error": "Không đủ dữ liệu để backtest"}
        
        # Filter by date range if provided
        if start_date:
            ohlcv = ohlcv[ohlcv['time'] >= start_date]
        if end_date:
            ohlcv = ohlcv[ohlcv['time'] <= end_date]
        
        if len(ohlcv) < 50:
            return {"status": "error", "error": "Không đủ dữ liệu sau khi lọc"}
        
        # Generate signals based on strategy
        trades = []
        position = None
        equity_curve = [capital]
        wins = 0
        losses = 0
        
        df = ohlcv.copy()
        
        # Calculate indicators based on strategy
        if strategy == "ma_cross":
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            
            for i in range(50, len(df)):
                row = df.iloc[i]
                prev = df.iloc[i-1]
                
                if prev['sma_20'] <= prev['sma_50'] and row['sma_20'] > row['sma_50']:
                    # Golden Cross - BUY
                    if position is None:
                        position = {
                            'entry_date': str(row['time'])[:10],
                            'entry_price': row['close'],
                            'type': 'LONG'
                        }
                elif prev['sma_20'] >= prev['sma_50'] and row['sma_20'] < row['sma_50']:
                    # Death Cross - SELL
                    if position is not None:
                        trade_return = (row['close'] - position['entry_price']) / position['entry_price'] * 100
                        trades.append({
                            'date': str(row['time'])[:10],
                            'type': 'BUY',
                            'entry_price': position['entry_price'],
                            'exit_price': row['close'],
                            'return': trade_return
                        })
                        if trade_return > 0:
                            wins += 1
                        else:
                            losses += 1
                        position = None
                
                # Calculate equity
                if position:
                    current_value = capital * (1 + (row['close'] - position['entry_price']) / position['entry_price'])
                else:
                    current_value = capital
                equity_curve.append(current_value)
        
        elif strategy == "rsi":
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            for i in range(14, len(df)):
                row = df.iloc[i]
                prev = df.iloc[i-1]
                
                # RSI Oversold -> BUY, RSI Overbought -> SELL
                if prev['rsi'] < 30 and row['rsi'] >= 30:
                    if position is None:
                        position = {
                            'entry_date': str(row['time'])[:10],
                            'entry_price': row['close'],
                            'type': 'LONG'
                        }
                elif prev['rsi'] > 70 and row['rsi'] <= 70:
                    if position is not None:
                        trade_return = (row['close'] - position['entry_price']) / position['entry_price'] * 100
                        trades.append({
                            'date': str(row['time'])[:10],
                            'type': 'BUY',
                            'entry_price': position['entry_price'],
                            'exit_price': row['close'],
                            'return': trade_return
                        })
                        if trade_return > 0:
                            wins += 1
                        else:
                            losses += 1
                        position = None
                
                if position:
                    current_value = capital * (1 + (row['close'] - position['entry_price']) / position['entry_price'])
                else:
                    current_value = capital
                equity_curve.append(current_value)
        
        elif strategy == "macd":
            ema12 = df['close'].ewm(span=12, adjust=False).mean()
            ema26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema12 - ema26
            df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            
            for i in range(26, len(df)):
                row = df.iloc[i]
                prev = df.iloc[i-1]
                
                if prev['macd'] <= prev['signal'] and row['macd'] > row['signal']:
                    if position is None:
                        position = {
                            'entry_date': str(row['time'])[:10],
                            'entry_price': row['close'],
                            'type': 'LONG'
                        }
                elif prev['macd'] >= prev['signal'] and row['macd'] < row['signal']:
                    if position is not None:
                        trade_return = (row['close'] - position['entry_price']) / position['entry_price'] * 100
                        trades.append({
                            'date': str(row['time'])[:10],
                            'type': 'BUY',
                            'entry_price': position['entry_price'],
                            'exit_price': row['close'],
                            'return': trade_return
                        })
                        if trade_return > 0:
                            wins += 1
                        else:
                            losses += 1
                        position = None
                
                if position:
                    current_value = capital * (1 + (row['close'] - position['entry_price']) / position['entry_price'])
                else:
                    current_value = capital
                equity_curve.append(current_value)
        
        # Close any open position at the end
        if position is not None:
            last_row = df.iloc[-1]
            trade_return = (last_row['close'] - position['entry_price']) / position['entry_price'] * 100
            trades.append({
                'date': str(last_row['time'])[:10],
                'type': 'CLOSE',
                'entry_price': position['entry_price'],
                'exit_price': last_row['close'],
                'return': trade_return
            })
            if trade_return > 0:
                wins += 1
            else:
                losses += 1
        
        # Calculate statistics
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        returns = [t['return'] for t in trades] if trades else [0]
        avg_return = sum(returns) / len(returns) if returns else 0
        total_return = (equity_curve[-1] - capital) / capital * 100 if equity_curve else 0
        
        # Profit factor
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Max drawdown
        peak = capital
        max_drawdown = 0
        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Sharpe ratio (simplified)
        import statistics
        if len(returns) > 1:
            returns_std = statistics.stdev(returns)
            sharpe_ratio = (sum(returns) / len(returns)) / returns_std if returns_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            "status": "success",
            "symbol": symbol,
            "strategy": strategy,
            "total_trades": total_trades,
            "win_trades": wins,
            "loss_trades": losses,
            "win_rate": win_rate,
            "total_return": total_return,
            "avg_return": avg_return,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "equity_curve": equity_curve,
            "trades": trades[-20:]  # Last 20 trades
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
