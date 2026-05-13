from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.excel_loader import TableMeta, load_rules, load_sheet_values, parse_columns
from src.rule_infer import infer_rule


@dataclass(frozen=True)
class FieldRule:
    field_name: str
    field_key: str
    excel_column: str
    column_index: int
    sample_value: Any
    required: bool
    allow_special_empty: bool
    rule: dict[str, Any]


def parse_template(template_path: str | Path, rule_path: str | Path) -> TableMeta:
    rules = load_rules(rule_path)
    rows = load_sheet_values(template_path, rules.get("sheet_name"))
    columns = [
        column
        for column in parse_columns(rows, rules["template"]["header_rows"])
        if column.name
    ]
    return TableMeta(columns=columns)


def parse_template_rules(
    template_path: str | Path,
    sheet_name: str | None,
    header_rows: dict[str, int] | None = None,
    sample_row: int = 4,
) -> list[FieldRule]:
    rows = load_sheet_values(template_path, sheet_name)
    header_rows = header_rows or {"category": 1, "field": 2, "sub_field": 3}
    columns = [column for column in parse_columns(rows, header_rows) if column.name]

    field_rules: list[FieldRule] = []
    for column in columns:
        sample_value = _cell_value(rows, sample_row, column.index)
        rule = infer_rule(column.name, sample_value)
        field_rules.append(
            FieldRule(
                field_name=column.name,
                field_key=column.compare_key,
                excel_column=column.excel_column,
                column_index=column.index,
                sample_value=sample_value,
                required=False,
                allow_special_empty=rule.get("allow_special_empty", True),
                rule=rule,
            )
        )
    return field_rules


def _cell_value(rows: list[list[Any]], excel_row: int, zero_based_column: int) -> Any:
    row_index = excel_row - 1
    if row_index < 0 or row_index >= len(rows):
        return None
    row = rows[row_index]
    if zero_based_column < 0 or zero_based_column >= len(row):
        return None
    return row[zero_based_column]
