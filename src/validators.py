from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.excel_loader import ColumnMeta, TableMeta, load_rules, normalize_cell


PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


def validate_structure(
    template_meta: TableMeta,
    summary_meta: TableMeta,
    summary_df: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    template_fields = template_meta.field_names
    summary_fields = summary_meta.field_names
    template_keys = template_meta.field_keys
    summary_keys = summary_meta.field_keys
    template_set = set(template_keys)
    summary_set = set(summary_keys)
    template_by_key = {column.compare_key: column for column in template_meta.columns if column.name}
    summary_by_key = {column.compare_key: column for column in summary_meta.columns if column.name}

    for key, field in zip(template_keys, template_fields):
        if key not in summary_set:
            errors.append(
                {
                    "错误类型": "缺少字段",
                    "Excel行号": "",
                    "Excel列号": "",
                    "模板字段": field,
                    "当前字段": "",
                    "错误值": "",
                    "错误说明": "汇总表缺少模板字段",
                }
            )

    for column in summary_meta.columns:
        if column.name and column.compare_key not in template_set:
            errors.append(
                {
                    "错误类型": "多余字段",
                    "Excel行号": "",
                    "Excel列号": column.excel_column,
                    "模板字段": "",
                    "当前字段": column.name,
                    "错误值": "",
                    "错误说明": "汇总表存在模板外字段",
                }
            )

    for position, (template_key, summary_key) in enumerate(
        zip(template_keys, summary_keys),
        start=1,
    ):
        if template_key != summary_key:
            template_column = template_by_key.get(template_key)
            summary_column = summary_by_key.get(summary_key)
            errors.append(
                {
                    "错误类型": "字段顺序不一致",
                    "Excel行号": "",
                    "Excel列号": summary_meta.columns[position - 1].excel_column,
                    "模板字段": template_column.name if template_column else template_fields[position - 1],
                    "当前字段": summary_column.name if summary_column else summary_fields[position - 1],
                    "错误值": "",
                    "错误说明": "汇总表字段顺序与模板不一致",
                }
            )

    if len(template_keys) != len(summary_keys):
        errors.append(
            {
                "错误类型": "字段数量不一致",
                "Excel行号": "",
                "Excel列号": "",
                "模板字段": len(template_keys),
                "当前字段": len(summary_keys),
                "错误值": "",
                "错误说明": "汇总表字段数量与模板不一致",
            }
        )

    if summary_df is not None and not summary_df.empty:
        errors.extend(_blank_header_value_errors(summary_meta, summary_df))

    return errors


def validate_data(
    summary_df: pd.DataFrame,
    summary_meta: TableMeta,
    rule_path: str | Path,
) -> list[dict[str, Any]]:
    rules = load_rules(rule_path)
    special_empty_values = {normalize_cell(value) for value in rules.get("special_empty_values", [])}
    numeric_special_values = {normalize_cell(value) for value in rules.get("numeric_special_values", [])}
    numeric_status_suffix_values = {normalize_cell(value) for value in rules.get("numeric_status_suffix_values", [])}
    data_rows = _content_rows(summary_df)
    errors: list[dict[str, Any]] = []

    for column in summary_meta.columns:
        if not column.name or column.data_key not in summary_df.columns:
            continue

        if _matches_any(column.name, rules.get("required_keywords", [])):
            errors.extend(_validate_required(data_rows, column, special_empty_values))

        if _matches_any(column.name, rules.get("free_text_numeric_keywords", [])):
            continue
        if _matches_any(column.name, rules.get("comparison_numeric_keywords", [])):
            errors.extend(_validate_numeric_with_unit(data_rows, column, special_empty_values, numeric_special_values))
        elif _matches_any(column.name, rules.get("strict_numeric_keywords", rules.get("numeric_keywords", []))):
            errors.extend(_validate_numeric(data_rows, column, special_empty_values, numeric_status_suffix_values))
        elif _matches_any(column.name, rules.get("numeric_with_unit_keywords", [])):
            errors.extend(_validate_numeric_with_unit(data_rows, column, special_empty_values, numeric_special_values))
        elif _matches_any(column.name, rules.get("range_or_description_keywords", [])):
            errors.extend(_validate_numeric_description(data_rows, column, special_empty_values, numeric_special_values))

        enum_values = _enum_values_for_column(column.name, rules.get("enum_rules", {}))
        if enum_values:
            errors.extend(_validate_enum(data_rows, column, enum_values, special_empty_values))

        if _matches_any(column.name, rules.get("phone_rules", [])):
            errors.extend(_validate_phone(data_rows, column, special_empty_values))

    return errors


def _content_rows(summary_df: pd.DataFrame) -> pd.DataFrame:
    if "__has_named_value__" not in summary_df.columns:
        return summary_df
    return summary_df[summary_df["__has_named_value__"] == True]


def _blank_header_value_errors(summary_meta: TableMeta, summary_df: pd.DataFrame) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for column in summary_meta.columns:
        if not column.raw_header_empty or column.data_key not in summary_df.columns:
            continue
        for _, row in summary_df.iterrows():
            value = normalize_cell(row.get(column.data_key))
            if value:
                errors.append(
                    {
                        "错误类型": "空表头列有数据",
                        "Excel行号": int(row["__excel_row__"]),
                        "Excel列号": column.excel_column,
                        "模板字段": "",
                        "当前字段": "空表头列",
                        "错误值": value,
                        "错误说明": "该列没有模板字段，但存在数据",
                    }
                )
    return errors


def _validate_required(
    summary_df: pd.DataFrame,
    column: ColumnMeta,
    special_empty_values: set[str],
) -> list[dict[str, Any]]:
    errors = []
    for _, row in summary_df.iterrows():
        value = normalize_cell(row.get(column.data_key))
        if value in special_empty_values:
            errors.append(_data_error("必填项为空", row, column, value or "空", f"{column.name}不能为空"))
    return errors


def _validate_numeric(
    summary_df: pd.DataFrame,
    column: ColumnMeta,
    special_empty_values: set[str],
    numeric_status_suffix_values: set[str] | None = None,
) -> list[dict[str, Any]]:
    numeric_status_suffix_values = numeric_status_suffix_values or set()
    errors = []
    for _, row in summary_df.iterrows():
        value = normalize_cell(row.get(column.data_key))
        if value in special_empty_values:
            continue
        try:
            number = float(value.replace(",", ""))
        except ValueError:
            number = _number_with_allowed_status(value, numeric_status_suffix_values)
            if number is None:
                errors.append(_data_error("数值格式错误", row, column, value, "应填写数字"))
                continue
        if number < 0:
            errors.append(_data_error("数值格式错误", row, column, value, "数字不能小于0"))
    return errors


def _validate_numeric_with_unit(
    summary_df: pd.DataFrame,
    column: ColumnMeta,
    special_empty_values: set[str],
    numeric_special_values: set[str],
) -> list[dict[str, Any]]:
    errors = []
    for _, row in summary_df.iterrows():
        value = normalize_cell(row.get(column.data_key))
        if value in special_empty_values or value in numeric_special_values:
            continue
        number = _first_number(value)
        if number is None:
            errors.append(_data_error("数值格式错误", row, column, value, "应填写数字，可带单位或约数"))
            continue
        if number < 0:
            errors.append(_data_error("数值格式错误", row, column, value, "数字不能小于0"))
    return errors


def _validate_numeric_description(
    summary_df: pd.DataFrame,
    column: ColumnMeta,
    special_empty_values: set[str],
    numeric_special_values: set[str],
) -> list[dict[str, Any]]:
    errors = []
    for _, row in summary_df.iterrows():
        value = normalize_cell(row.get(column.data_key))
        if value in special_empty_values or value in numeric_special_values:
            continue
        if _first_number(value) is None:
            errors.append(_data_error("数值格式错误", row, column, value, "应填写数字、区间或含数字说明"))
    return errors


def _validate_enum(
    summary_df: pd.DataFrame,
    column: ColumnMeta,
    allowed_values: list[str],
    special_empty_values: set[str],
) -> list[dict[str, Any]]:
    errors = []
    allowed = {normalize_cell(value) for value in allowed_values}
    for _, row in summary_df.iterrows():
        value = normalize_cell(row.get(column.data_key))
        if value in special_empty_values or value in allowed:
            continue
        allowed_text = "、".join(allowed_values)
        errors.append(_data_error("枚举错误", row, column, value, f"允许值为：{allowed_text}"))
    return errors


def _validate_phone(
    summary_df: pd.DataFrame,
    column: ColumnMeta,
    special_empty_values: set[str],
) -> list[dict[str, Any]]:
    errors = []
    for _, row in summary_df.iterrows():
        value = _normalize_phone(row.get(column.data_key))
        if value in special_empty_values:
            continue
        if not PHONE_PATTERN.match(value):
            errors.append(_data_error("手机号错误", row, column, value, "手机号格式不正确"))
    return errors


def _data_error(error_type: str, row: pd.Series, column: ColumnMeta, value: str, message: str) -> dict[str, Any]:
    return {
        "错误类型": error_type,
        "Excel行号": int(row["__excel_row__"]),
        "Excel列号": column.excel_column,
        "字段名": column.name,
        "错误值": value,
        "错误说明": message,
    }


def _matches_any(field_name: str, keywords: list[str]) -> bool:
    return any(keyword and keyword in field_name for keyword in keywords)


def _enum_values_for_column(field_name: str, enum_rules: dict[str, list[str]]) -> list[str] | None:
    for keyword, values in enum_rules.items():
        if keyword in field_name:
            return values
    return None


def _first_number(value: str) -> float | None:
    match = NUMBER_PATTERN.search(value.replace(",", ""))
    if not match:
        return None
    return float(match.group())


def _normalize_phone(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    text = normalize_cell(value)
    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]
    return text


def _number_with_allowed_status(value: str, allowed_status_values: set[str]) -> float | None:
    if not allowed_status_values:
        return None
    normalized = value.translate(str.maketrans({"（": "(", "）": ")"}))
    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*\(([^)]+)\)\s*", normalized)
    if not match:
        return None
    status = normalize_cell(match.group(2))
    if status not in allowed_status_values:
        return None
    return float(match.group(1))
