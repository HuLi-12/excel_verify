from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.excel_loader import (
    TableMeta,
    load_rules,
    load_sheet_values,
    normalize_cell,
    parse_columns,
)


def parse_summary(summary_path: str | Path, rule_path: str | Path) -> tuple[pd.DataFrame, TableMeta]:
    rules = load_rules(rule_path)
    rows = load_sheet_values(summary_path, rules.get("sheet_name"))
    summary_rules = rules["summary"]
    columns = parse_columns(rows, summary_rules["header_rows"])
    data_start_row = int(summary_rules["data_start_row"])
    data_rows = rows[data_start_row - 1 :]

    records = []
    for excel_row_number, row in enumerate(data_rows, start=data_start_row):
        record = {"__excel_row__": excel_row_number}
        has_value = False
        has_named_value = False
        for column in columns:
            value = row[column.index] if column.index < len(row) else None
            if normalize_cell(value):
                has_value = True
                if column.name:
                    has_named_value = True
            record[column.data_key] = value
        if has_value:
            record["__has_named_value__"] = has_named_value
            records.append(record)

    return pd.DataFrame.from_records(records), TableMeta(columns=columns, data_start_row=data_start_row)
