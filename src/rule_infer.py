from __future__ import annotations

import re
from typing import Any


SPECIAL_EMPTY = {"/", "", "无", "暂无", "未提供", "不涉及"}
UNIT_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)([\u4e00-\u9fa5a-zA-Z㎡]+)$")
DECIMAL_ALLOWED_KEYWORDS = ["面积", "容积率", "建筑密度", "绿地率", "单价", "金额", "价格", "层高"]
ID_CARD_KEYWORDS = ["身份证", "身份证号", "证件号码", "居民身份证"]
PHONE_KEYWORDS = ["手机", "手机号", "联系电话", "联系人电话", "电话"]


def infer_rule(field_name: str, sample_value: Any) -> dict[str, Any]:
    text = _normalize(sample_value)
    if _matches_any_keyword(field_name, ID_CARD_KEYWORDS):
        return {"type": "id_card"}
    if _matches_any_keyword(field_name, PHONE_KEYWORDS):
        return {"type": "phone"}
    if "X" in text.upper():
        return {"type": "string"}
    field_enum = _enum_from_field_name(field_name, text)
    if field_enum:
        return field_enum
    date_rule = _date_rule(field_name, text)
    if date_rule:
        return date_rule
    if text in SPECIAL_EMPTY:
        return {"type": "any", "allow_special_empty": True}
    if "；" in text:
        return _infer_list(field_name, text)
    if _looks_like_enum(text) and _is_compact_enum_options(text.split("/")):
        return {"type": "enum", "allowed_values": text.split("/")}
    unit_match = UNIT_PATTERN.fullmatch(text)
    if unit_match:
        return {
            "type": "number_with_unit",
            "number_type": "positive_number",
            "unit": unit_match.group(2),
            "unit_required": True,
        }
    if re.fullmatch(r"[1-9]\d*", text):
        if _allows_decimal(field_name):
            return {"type": "number", "min": 0}
        return {"type": "positive_integer"}
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return {"type": "number", "min": 0}
    return {"type": "string"}


def _infer_list(field_name: str, text: str) -> dict[str, Any]:
    parts = [_clean_list_item(part) for part in text.split("；")]
    item_rules = [infer_rule(field_name, part) for part in parts]
    first = item_rules[0]
    if all(
        rule.get("type") == "number_with_unit" and rule.get("unit") == first.get("unit")
        for rule in item_rules
    ):
        return {
            "type": "list",
            "separator": "；",
            "item_type": "number_with_unit",
            "unit": first["unit"],
            "unit_required": True,
        }
    if all(rule.get("type") == "positive_integer" for rule in item_rules):
        return {"type": "list", "separator": "；", "item_type": "positive_integer"}
    if all(rule.get("type") == "number" for rule in item_rules):
        return {"type": "list", "separator": "；", "item_type": "number"}
    return {"type": "list", "separator": "；", "item_type": "string"}


def _looks_like_enum(text: str) -> bool:
    return "/" in text and len([part for part in text.split("/") if part]) >= 2


def _enum_from_field_name(field_name: str, sample_text: str) -> dict[str, Any] | None:
    last_part = field_name.split("_")[-1]
    if not _looks_like_enum(last_part):
        return None
    allowed_values = [part for part in last_part.split("/") if part]
    if not _is_compact_enum_options(allowed_values):
        return None
    if sample_text and sample_text not in allowed_values:
        return None
    return {"type": "enum", "allowed_values": allowed_values}


def _is_compact_enum_options(values: list[str]) -> bool:
    return all(1 <= len(value) <= 8 and "X" not in value.upper() for value in values)


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).strip().split())
    for prefix in ["填报示例：", "填报示例:", "示例：", "示例:"]:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _clean_list_item(value: str) -> str:
    return value.strip().rstrip("。.")


def _allows_decimal(field_name: str) -> bool:
    return any(keyword in field_name for keyword in DECIMAL_ALLOWED_KEYWORDS)


def _matches_any_keyword(field_name: str, keywords: list[str]) -> bool:
    return any(keyword in field_name for keyword in keywords)


def _date_rule(field_name: str, text: str) -> dict[str, str] | None:
    if re.fullmatch(r"\d{4}\.\d{1,2}\.\d{1,2}", text):
        return {"type": "date", "format": "yyyy.MM.dd"}
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", text):
        return {"type": "date", "format": "yyyy-MM-dd"}
    if re.fullmatch(r"\d{8}", text) and "日期" in field_name:
        return {"type": "date", "format": "yyyyMMdd"}
    return None
