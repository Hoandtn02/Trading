import json
from pprint import pformat

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    if isinstance(mapping, dict):
        return mapping.get(key, "")
    return ""


@register.filter
def pprint(obj):
    try:
        return pformat(obj)
    except Exception:
        return str(obj)


@register.filter
def json_dumps(obj):
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(obj)
