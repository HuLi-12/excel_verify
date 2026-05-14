from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.cell_validator import validate_cell
from src.data_region import find_data_start_row
from src.excel_loader import ColumnMeta, load_sheet_values, normalize_cell, parse_columns
from src.template_parser import FieldRule, parse_template_rules


@dataclass(frozen=True)
class ValidationResult:
    data_start_row: int
    errors: list[dict[str, Any]]


def validate_workbook(
    template_path: str | Path,
    data_path: str | Path,
    sheet_name: str | None,
) -> ValidationResult:
    template_rules = parse_template_rules(template_path, sheet_name)
    data_rows = load_sheet_values(data_path, sheet_name)
    data_columns = parse_columns(data_rows, {"category": 2, "field": 3, "sub_field": 4})
    data_start_row = find_data_start_row(data_rows, data_columns)

    rules_by_key = {rule.field_key: rule for rule in template_rules}
    errors: list[dict[str, Any]] = []

    for excel_row_number in range(data_start_row, len(data_rows) + 1):
        row = data_rows[excel_row_number - 1]
        if _is_empty_row(row):
            continue
        for column in data_columns:
            field_rule = rules_by_key.get(column.compare_key)
            if not field_rule:
                continue
            value = row[column.index] if column.index < len(row) else None
            error = validate_cell(
                value,
                field_rule.rule,
                required=field_rule.required,
                allow_special_empty=field_rule.allow_special_empty,
            )
            if error:
                errors.append(_cell_error(error, excel_row_number, column, field_rule, value))

    return ValidationResult(data_start_row=data_start_row, errors=errors)


def _cell_error(
    error: dict[str, str],
    excel_row_number: int,
    column: ColumnMeta,
    field_rule: FieldRule,
    value: Any,
) -> dict[str, Any]:
    return {
        "status": error.get("status", "ERROR"),
        "Excel行号": excel_row_number,
        "Excel列号": column.excel_column,
        "字段名": field_rule.field_name,
        "原始值": error.get("原始值", normalize_cell(value)),
        "输出值": error.get("输出值", "/"),
        "错误类型": error.get("错误类型", ""),
        "错误说明": error.get("错误说明", ""),
        "警告类型": error.get("警告类型", ""),
        "警告说明": error.get("警告说明", ""),
        "修正说明": error.get("修正说明", ""),
    }


def _is_empty_row(row: list[Any]) -> bool:
    return not any(normalize_cell(value) for value in row)
