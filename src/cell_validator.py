from __future__ import annotations

import re
from typing import Any

from src.excel_loader import normalize_cell


SPECIAL_EMPTY_VALUES = {"/", "", "无", "暂无", "未提供", "不涉及"}


def validate_cell(
    value: Any,
    rule: dict[str, Any],
    required: bool = False,
    allow_special_empty: bool = True,
) -> dict[str, str] | None:
    text = normalize_cell(value)
    if text in SPECIAL_EMPTY_VALUES:
        if required and not allow_special_empty:
            return {"错误类型": "必填项为空", "错误说明": "必填字段不能为空或特殊空值"}
        return None

    rule_type = rule.get("type", "string")
    if rule_type == "any":
        return None
    if rule_type == "string":
        return None
    if rule_type == "enum":
        allowed = rule.get("allowed_values", [])
        if text not in allowed:
            return {"错误类型": "枚举错误", "错误说明": f"允许值：{'/'.join(allowed)}"}
        return None
    if rule_type == "positive_integer":
        if not re.fullmatch(r"[1-9]\d*", text):
            return {"错误类型": "正整数错误", "错误说明": "应填写大于0的整数"}
        return None
    if rule_type == "number":
        try:
            number = float(text)
        except ValueError:
            return {"错误类型": "数值错误", "错误说明": "应填写数字"}
        if number < 0:
            return {"错误类型": "数值错误", "错误说明": "数字不能小于0"}
        return None
    if rule_type == "number_with_unit":
        unit = rule["unit"]
        if not re.fullmatch(rf"\d+(?:\.\d+)?{re.escape(unit)}", text):
            return {"错误类型": "单位数值错误", "错误说明": f"应填写数字+{unit}"}
        return None
    if rule_type == "list":
        return _validate_list(text, rule)
    return None


def _validate_list(text: str, rule: dict[str, Any]) -> dict[str, str] | None:
    separator = rule.get("separator", "；")
    if separator not in text:
        return {"错误类型": "列表格式错误", "错误说明": f"应使用{separator}分隔"}
    wrong_separators = [";", "，", ",", "、"]
    if any(sep in text for sep in wrong_separators):
        return {"错误类型": "列表格式错误", "错误说明": f"应使用{separator}分隔"}

    item_rule = _item_rule(rule)
    for item in text.split(separator):
        error = validate_cell(item, item_rule, required=True, allow_special_empty=False)
        if error:
            return {"错误类型": "列表格式错误", "错误说明": error["错误说明"]}
    return None


def _item_rule(rule: dict[str, Any]) -> dict[str, Any]:
    item_type = rule.get("item_type", "string")
    if item_type == "number_with_unit":
        return {
            "type": "number_with_unit",
            "unit": rule["unit"],
            "unit_required": rule.get("unit_required", True),
        }
    return {"type": item_type}
