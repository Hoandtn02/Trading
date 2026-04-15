from __future__ import annotations

import importlib
from typing import Any

from .registry import FUNCTION_REGISTRY


def iter_registry_functions() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for group_entry in FUNCTION_REGISTRY:
        group = group_entry["group"]
        for func in group_entry["functions"]:
            items.append({"group": group, **func})
    return items


def get_function_definition(function_id: str) -> dict[str, Any] | None:
    for item in iter_registry_functions():
        if item["function_id"] == function_id:
            return item
    return None


def run_registry_function(function_id: str, params: dict[str, Any]) -> dict[str, Any]:
    definition = get_function_definition(function_id)
    if definition is None:
        raise ValueError(f"Unknown function_id: {function_id}")

    module_name, function_name = definition["runner_path"].rsplit(".", 1)
    module = importlib.import_module(module_name)
    runner = getattr(module, function_name)
    return runner(**params)
