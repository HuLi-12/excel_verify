from __future__ import annotations

from typing import Any

from src.excel_loader import ColumnMeta, normalize_cell


def find_data_start_row(rows: list[list[Any]], columns: list[ColumnMeta]) -> int:
    sequence_column = next((column for column in columns if "序号" in column.name), None)
    if sequence_column is None:
        raise ValueError("未找到序号列，无法识别真实数据起始行")

    for row_index, row in enumerate(rows, start=1):
        value = row[sequence_column.index] if sequence_column.index < len(row) else None
        if normalize_cell(value) in {"1", "1.0"}:
            return row_index

    raise ValueError("未找到序号=1的真实数据起始行")
