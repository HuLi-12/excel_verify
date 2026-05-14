from __future__ import annotations

from datetime import datetime
import re
from typing import Any


SPECIAL_EMPTY_VALUES = {"/", "", "无", "暂无", "未提供", "不涉及"}
STRUCTURED_RULE_TYPES = {"positive_integer", "number", "number_with_unit", "list", "date", "phone", "id_card"}


def validate_cell(
    value: Any,
    rule: dict[str, Any],
    required: bool = False,
    allow_special_empty: bool = True,
) -> dict[str, str] | None:
    original = _raw_text(value)
    text, clean_messages = clean_value(original)
    result = _validate_cleaned_cell(text, rule, required, allow_special_empty)
    return _merge_cleaning_result(original, text, clean_messages, result)


def clean_value(value: Any) -> tuple[str, list[str]]:
    text = _raw_text(value)
    messages: list[str] = []

    without_spaces = re.sub(r"[ \u3000\t\n\r]+", "", text)
    if without_spaces != text:
        messages.append("删除空白字符")
    text = without_spaces

    without_periods = text.rstrip("。.")
    if without_periods != text:
        messages.append("删除末尾句号")
    text = without_periods

    normalized_semicolon = text.replace(";", "；")
    if normalized_semicolon != text:
        messages.append("英文分号已统一为中文分号")
    text = normalized_semicolon

    return text, messages


def _validate_cleaned_cell(
    text: str,
    rule: dict[str, Any],
    required: bool = False,
    allow_special_empty: bool = True,
) -> dict[str, str] | None:
    rule_type = rule.get("type", "string")
    if text == "无" and rule_type in STRUCTURED_RULE_TYPES:
        return _warning("结构化字段填写无", text, text, "该字段应填写结构化数据，当前填写“无”，请人工确认")
    if text in SPECIAL_EMPTY_VALUES:
        if required and not allow_special_empty:
            return _error("必填项为空", text, "/", "必填字段不能为空或特殊空值")
        return None

    if rule_type == "any":
        return None
    if rule_type == "string":
        return None
    if rule_type == "enum":
        allowed = rule.get("allowed_values", [])
        if text not in allowed:
            return _error("枚举错误", text, "/", f"允许值：{'/'.join(allowed)}")
        return None
    if rule_type == "positive_integer":
        if not re.fullmatch(r"[1-9]\d*", text):
            return _error("正整数错误", text, "/", "应填写大于0的整数")
        return None
    if rule_type == "number":
        try:
            number = float(text)
        except ValueError:
            return _error("数值错误", text, "/", "应填写数字")
        if number < 0:
            return _error("数值错误", text, "/", "数字不能小于0")
        return None
    if rule_type == "number_with_unit":
        unit = rule["unit"]
        if not re.fullmatch(rf"\d+(?:\.\d+)?{re.escape(unit)}", text):
            return _error("单位数值错误", text, "/", f"应填写数字+{unit}")
        return None
    if rule_type == "list":
        return _validate_list(text, rule)
    if rule_type == "date":
        return _validate_date(text, rule)
    if rule_type == "phone":
        return _validate_phone(text)
    if rule_type == "id_card":
        return _validate_id_card(text)
    return None


def _validate_list(text: str, rule: dict[str, Any]) -> dict[str, str] | None:
    separator = rule.get("separator", "；")
    if ";" in text:
        normalized_text = text.replace(";", separator)
        item_error = _validate_list_items(normalized_text, rule)
        if item_error:
            return item_error
        return _normalized(text, normalized_text, "英文分号已统一为中文分号")

    risky_separators = ["，", ",", "、"]
    if any(sep in text for sep in risky_separators):
        return _warning("列表分隔符不规范", text, text, f"疑似列表字段使用了非标准分隔符，请确认是否应使用{separator}")

    if separator not in text:
        item_rule = _item_rule(rule)
        return validate_cell(text, item_rule, required=True, allow_special_empty=False)

    return _validate_list_items(text, rule)


def _validate_list_items(text: str, rule: dict[str, Any]) -> dict[str, str] | None:
    separator = rule.get("separator", "；")
    parts = [part.strip() for part in text.split(separator)]
    if len(parts) > 1 and any(part == "无" for part in parts):
        return _error("列表格式错误", text, "/", "列表中不能混入“无”，请删除该项或将整个字段填写为“无”")

    item_rule = _item_rule(rule)
    for item in parts:
        error = validate_cell(item, item_rule, required=True, allow_special_empty=False)
        if error and error.get("status") != "NORMALIZED":
            return _error("列表格式错误", text, "/", error.get("错误说明", "列表元素不符合子类型"))
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


def _validate_date(text: str, rule: dict[str, Any]) -> dict[str, str] | None:
    parsed = _parse_date(text)
    if parsed is None:
        return _error("日期错误", text, "/", "无法解析为合法日期")
    output = _format_date(parsed, rule.get("format", "yyyy-MM-dd"))
    if output != text:
        return _normalized(text, output, "日期格式已统一为模板格式")
    return None


def _validate_phone(text: str) -> dict[str, str] | None:
    if not re.fullmatch(r"1[3-9]\d{9}", text):
        return _error("手机号错误", text, "/", "手机号格式不正确，应为11位手机号")
    return None


def _validate_id_card(text: str) -> dict[str, str] | None:
    if not re.fullmatch(r"\d{17}[\dXx]", text):
        return _error("身份证号错误", text, "/", "身份证号应为18位，前17位为数字，最后一位为数字或X")
    output = text[:-1] + text[-1].upper()
    if output != text:
        return _normalized(text, output, "身份证号末位x已统一为大写X")
    return None


def _parse_date(text: str) -> datetime | None:
    candidates = [
        ("%Y.%m.%d", text),
        ("%Y-%m-%d", text),
        ("%Y/%m/%d", text),
        ("%Y年%m月%d日", text),
        ("%Y%m%d", text),
    ]
    for fmt, value in candidates:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _format_date(value: datetime, fmt: str) -> str:
    if fmt == "yyyy.MM.dd":
        return value.strftime("%Y.%m.%d")
    if fmt == "yyyyMMdd":
        return value.strftime("%Y%m%d")
    return value.strftime("%Y-%m-%d")


def _raw_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _merge_cleaning_result(
    original: str,
    cleaned: str,
    clean_messages: list[str],
    result: dict[str, str] | None,
) -> dict[str, str] | None:
    if result is None:
        if clean_messages:
            return _normalized(original, cleaned, _clean_message(clean_messages))
        return None

    status = result.get("status", "ERROR")
    if status == "NORMALIZED":
        messages = [*clean_messages, result.get("修正说明", "")]
        return _normalized(original, result.get("输出值", cleaned), _clean_message(messages))

    result["原始值"] = original
    if status == "WARNING":
        result["输出值"] = original
    return result


def _clean_message(messages: list[str]) -> str:
    compact_messages = [message for message in messages if message]
    if not compact_messages:
        return "格式已规范化"
    return "；".join(compact_messages) + "后通过校验"


def _normalized(original: str, output: str, message: str) -> dict[str, str]:
    return {
        "status": "NORMALIZED",
        "原始值": original,
        "输出值": output,
        "修正说明": message,
    }


def _warning(warning_type: str, original: str, output: str, message: str) -> dict[str, str]:
    return {
        "status": "WARNING",
        "原始值": original,
        "输出值": output,
        "警告类型": warning_type,
        "警告说明": message,
    }


def _error(error_type: str, original: str, output: str, message: str) -> dict[str, str]:
    return {
        "status": "ERROR",
        "原始值": original,
        "输出值": output,
        "错误类型": error_type,
        "错误说明": message,
    }
