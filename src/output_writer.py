from __future__ import annotations

from copy import copy
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill


ERROR_FILL = PatternFill(fill_type="solid", fgColor="FFFFC7CE")
ERROR_FONT_COLOR = "FF9C0006"
DETAIL_SHEET_NAME = "错误明细"
DETAIL_HEADERS = ["Excel行号", "Excel列号", "字段名", "原始值", "错误类型", "错误说明"]


def write_validated_workbook(
    source_workbook_path: str | Path,
    output_path: str | Path,
    errors: list[dict[str, Any]],
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    workbook = openpyxl.load_workbook(source_workbook_path)
    data_sheet = workbook.worksheets[0]

    for error in errors:
        row = error.get("Excel行号")
        column = error.get("Excel列号")
        if not isinstance(row, int) or not isinstance(column, str) or not column:
            continue
        cell = data_sheet[f"{column}{row}"]
        cell.value = "/"
        cell.fill = ERROR_FILL
        font = copy(cell.font)
        font.color = ERROR_FONT_COLOR
        cell.font = font
        cell.comment = Comment(_comment_text(error), "asset-validator")

    _write_detail_sheet(workbook, errors)
    workbook.save(output)


def _write_detail_sheet(workbook: openpyxl.Workbook, errors: list[dict[str, Any]]) -> None:
    if DETAIL_SHEET_NAME in workbook.sheetnames:
        del workbook[DETAIL_SHEET_NAME]
    sheet = workbook.create_sheet(DETAIL_SHEET_NAME)
    sheet.append(DETAIL_HEADERS)
    header_font = Font(bold=True)
    for cell in sheet[1]:
        cell.font = header_font

    for error in errors:
        sheet.append([error.get(header, "") for header in DETAIL_HEADERS])


def _comment_text(error: dict[str, Any]) -> str:
    return f"{error.get('错误类型', '')}：{error.get('错误说明', '')}"
