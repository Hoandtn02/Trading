from __future__ import annotations

import json
from datetime import date, datetime

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .forms import DynamicFunctionForm
from .models import ExecutionResult, FunctionDefinition, FunctionGroup, UserPreset
from .services import get_function_definition, iter_registry_functions, run_registry_function


def _seed_missing_registry_rows() -> None:
    for item in iter_registry_functions():
        group_data = item["group"]
        group, _ = FunctionGroup.objects.get_or_create(
            slug=group_data["slug"],
            defaults={"name": group_data["name"], "description": group_data.get("description", "")},
        )
        FunctionDefinition.objects.update_or_create(
            function_id=item["function_id"],
            defaults={
                "group": group,
                "label": item["label"],
                "description": item.get("description", ""),
                "runner_path": item["runner_path"],
                "param_schema": item.get("param_schema", {}),
                "output_type": item.get("output_type", "table"),
                "is_active": item.get("status") != "disabled",
            },
        )
        # Sync is_active and status: re-fetch and patch if stale
        fd = FunctionDefinition.objects.filter(function_id=item["function_id"]).first()
        if fd:
            # is_active maps from registry status; planned/partial/ready → True, disabled → False
            registry_status = item.get("status", "planned")
            fresh_active = registry_status != "disabled"
            if fd.is_active != fresh_active or fd.runner_path != item["runner_path"]:
                fd.is_active = fresh_active
                fd.runner_path = item["runner_path"]
                fd.param_schema = item.get("param_schema", {})
                fd.output_type = item.get("output_type", "table")
                fd.save(update_fields=["is_active", "runner_path", "param_schema", "output_type"])


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
