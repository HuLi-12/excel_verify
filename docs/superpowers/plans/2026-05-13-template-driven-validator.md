# Excel Template Driven Validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current asset-table validator into a template-driven Excel validator that infers rules from template examples, starts validation at the first `序号=1` row, replaces invalid cells with `/`, highlights them red, and writes an error-detail sheet.

**Architecture:** Keep `main.py` and `src/app_config.py` as the run-entry layer, but replace the current data-validation path with openpyxl-first modules. `template_parser.py` will produce field metadata plus inferred rules, `data_region.py` will locate the real data start row, `validator.py` will validate workbook cells directly, and `output_writer.py` will modify a copy of the source workbook.

**Tech Stack:** Python 3.11, openpyxl, PyYAML, pytest, standard-library `re`, optional pandas only for existing compatibility while migrating.

---

## File Structure

- Modify: `src/excel_loader.py`
  - Keep shared Excel utilities and `ColumnMeta`, but add richer field-rule structures or move them to `src/rule_infer.py`.
- Modify: `src/template_parser.py`
  - Parse template header rows plus sample row and return inferred rules per column.
- Create: `src/rule_infer.py`
  - Infer `string`, `positive_integer`, `number`, `enum`, `list`, `number_with_unit`, `list_with_unit`, and `any`.
- Create: `src/data_region.py`
  - Find the first real data row by scanning the `序号` column for value `1`.
- Create: `src/cell_validator.py`
  - Validate one cell against one inferred field rule and return structured errors.
- Create or replace: `src/output_writer.py`
  - Copy source workbook, replace invalid cell values with `/`, red-fill cells, add comments, and write `错误明细`.
- Modify: `src/report_writer.py`
  - Either delegate to `output_writer.py` or keep as a compatibility wrapper.
- Modify: `main.py`
  - Use the new openpyxl-first pipeline.
- Modify: `config/asset_basic_info_rules.yaml`
  - Change from primary rules to override rules only.
- Test: `tests/test_rule_infer.py`
- Test: `tests/test_data_region.py`
- Test: `tests/test_cell_validator.py`
- Test: `tests/test_template_driven_pipeline.py`

---

### Task 1: Rule Inference Module

**Files:**
- Create: `src/rule_infer.py`
- Test: `tests/test_rule_infer.py`

- [ ] **Step 1: Write failing tests for enum, list, unit, number, integer, any**

```python
from src.rule_infer import infer_rule


def test_infer_enum_from_slash_separated_sample():
    rule = infer_rule("资产来源", "划转/购入/自建")
    assert rule["type"] == "enum"
    assert rule["allowed_values"] == ["划转", "购入", "自建"]


def test_single_slash_is_any_special_empty_not_enum():
    rule = infer_rule("备注", "/")
    assert rule["type"] == "any"
    assert rule["allow_special_empty"] is True


def test_infer_list_of_positive_integers_from_chinese_semicolon():
    rule = infer_rule("车位编号", "500；1200；1350")
    assert rule == {
        "type": "list",
        "separator": "；",
        "item_type": "positive_integer",
    }


def test_infer_number_with_required_unit():
    rule = infer_rule("建筑面积", "30平方米")
    assert rule == {
        "type": "number_with_unit",
        "number_type": "positive_number",
        "unit": "平方米",
        "unit_required": True,
    }


def test_infer_list_with_unit():
    rule = infer_rule("分项面积", "500平方米；1200平方米")
    assert rule["type"] == "list"
    assert rule["separator"] == "；"
    assert rule["item_type"] == "number_with_unit"
    assert rule["unit"] == "平方米"


def test_infer_positive_integer_and_number():
    assert infer_rule("序号", "1")["type"] == "positive_integer"
    assert infer_rule("容积率", "0.8")["type"] == "number"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_rule_infer.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.rule_infer'`.

- [ ] **Step 3: Implement minimal inference**

Create `src/rule_infer.py`:

```python
from __future__ import annotations

import re
from typing import Any

SPECIAL_EMPTY = {"/", "", "无", "暂无", "未提供", "不涉及"}
UNIT_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)([\u4e00-\u9fa5a-zA-Z㎡]+)$")


def infer_rule(field_name: str, sample_value: Any) -> dict[str, Any]:
    text = _normalize(sample_value)
    if text in SPECIAL_EMPTY:
        return {"type": "any", "allow_special_empty": True}
    if "；" in text:
        return _infer_list(text)
    if _looks_like_enum(text):
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
        return {"type": "positive_integer"}
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return {"type": "number", "min": 0}
    return {"type": "string"}


def _infer_list(text: str) -> dict[str, Any]:
    parts = text.split("；")
    item_rules = [infer_rule("", part) for part in parts]
    first = item_rules[0]
    if all(rule.get("type") == "number_with_unit" and rule.get("unit") == first.get("unit") for rule in item_rules):
        return {
            "type": "list",
            "separator": "；",
            "item_type": "number_with_unit",
            "unit": first["unit"],
            "unit_required": True,
        }
    if all(rule.get("type") == "positive_integer" for rule in item_rules):
        return {"type": "list", "separator": "；", "item_type": "positive_integer"}
    return {"type": "list", "separator": "；", "item_type": "string"}


def _looks_like_enum(text: str) -> bool:
    return "/" in text and len([part for part in text.split("/") if part]) >= 2


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_rule_infer.py -q
```

Expected: PASS.

---

### Task 2: Template Parser Produces Field Rules

**Files:**
- Modify: `src/template_parser.py`
- Test: `tests/test_template_parser_rules.py`

- [ ] **Step 1: Write failing test for extracting sample-row rules**

```python
import openpyxl

from src.template_parser import parse_template_rules


def test_parse_template_rules_uses_sample_row_for_rule_inference(tmp_path):
    path = tmp_path / "template.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "资产基本信息调研表"
    ws["A1"] = "一、资产基础法律属性"
    ws["A2"] = "资产来源"
    ws["A3"] = "划转/购入/自建"
    ws["A4"] = "划转/购入/自建"
    wb.save(path)

    rules = parse_template_rules(path, "资产基本信息调研表")

    assert rules[0].field_name == "一、资产基础法律属性_资产来源_划转/购入/自建"
    assert rules[0].excel_column == "A"
    assert rules[0].sample_value == "划转/购入/自建"
    assert rules[0].rule["type"] == "enum"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_template_parser_rules.py -q
```

Expected: FAIL because `parse_template_rules` does not exist.

- [ ] **Step 3: Add `FieldRule` and `parse_template_rules`**

Implement a dataclass in `src/template_parser.py`:

```python
from dataclasses import dataclass
from typing import Any

from src.excel_loader import load_sheet_values, parse_columns
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
```

Add `parse_template_rules(template_path, sheet_name, header_rows)` that:

- Uses template header rows: category row 1, field row 2, sub-field row 3.
- Uses sample row 4 by default.
- Calls `parse_columns`.
- Calls `infer_rule(column.name, sample_value)`.
- Sets `required=False` for every inferred field in this task; YAML overrides for `required` are implemented only if they are added in a separate task.

- [ ] **Step 4: Run parser tests**

Run:

```bash
python -m pytest tests/test_template_parser_rules.py tests/test_rule_infer.py -q
```

Expected: PASS.

---

### Task 3: Data Region Detection by `序号=1`

**Files:**
- Create: `src/data_region.py`
- Test: `tests/test_data_region.py`

- [ ] **Step 1: Write failing test**

```python
import openpyxl

from src.data_region import find_data_start_row
from src.excel_loader import load_sheet_values, parse_columns


def test_find_data_start_row_from_first_sequence_one(tmp_path):
    path = tmp_path / "data.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "资产基本信息调研表"
    ws["A1"] = "汇总表"
    ws["A2"] = "一、资产基础法律属性"
    ws["A3"] = "序号"
    ws["A4"] = "序号"
    ws["A5"] = "示例"
    ws["A6"] = 1
    ws["A7"] = 2
    wb.save(path)

    rows = load_sheet_values(path, "资产基本信息调研表")
    columns = parse_columns(rows, {"category": 2, "field": 3, "sub_field": 4})

    assert find_data_start_row(rows, columns) == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_data_region.py -q
```

Expected: FAIL because `src.data_region` does not exist.

- [ ] **Step 3: Implement `find_data_start_row`**

```python
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
```

- [ ] **Step 4: Run data-region tests**

Run:

```bash
python -m pytest tests/test_data_region.py -q
```

Expected: PASS.

---

### Task 4: Cell Validator

**Files:**
- Create: `src/cell_validator.py`
- Test: `tests/test_cell_validator.py`

- [ ] **Step 1: Write failing tests for core cell types**

```python
from src.cell_validator import validate_cell


def test_validate_enum_rejects_unknown_value():
    error = validate_cell("新建", {"type": "enum", "allowed_values": ["划转", "购入", "自建"]})
    assert error["错误类型"] == "枚举错误"


def test_validate_list_requires_chinese_semicolon():
    error = validate_cell("500;1200", {"type": "list", "separator": "；", "item_type": "positive_integer"})
    assert error["错误类型"] == "列表格式错误"


def test_validate_number_with_unit_requires_exact_unit():
    assert validate_cell("500平方米", {"type": "number_with_unit", "unit": "平方米"}) is None
    error = validate_cell("500㎡", {"type": "number_with_unit", "unit": "平方米"})
    assert error["错误类型"] == "单位数值错误"


def test_required_field_rejects_special_empty():
    error = validate_cell("/", {"type": "string"}, required=True, allow_special_empty=False)
    assert error["错误类型"] == "必填项为空"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_cell_validator.py -q
```

Expected: FAIL because `src.cell_validator` does not exist.

- [ ] **Step 3: Implement validation**

Implement:

```python
def validate_cell(value, rule, required=False, allow_special_empty=True) -> dict | None:
    text = normalize_cell(value)
    if text in {"/", "", "无", "暂无", "未提供", "不涉及"}:
        if required and not allow_special_empty:
            return {"错误类型": "必填项为空", "错误说明": "必填字段不能为空或特殊空值"}
        return None
    rule_type = rule.get("type", "string")
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
    return None
```

Rules:

- Special empty values pass only when `required=False` or `allow_special_empty=True`.
- `positive_integer`: regex `^[1-9]\d*$`.
- `number`: parse `float`, require `>= 0`.
- `enum`: exact match against allowed values.
- `list`: split by exact separator and validate each item recursively.
- `number_with_unit`: regex `^\d+(\.\d+)?<unit>$`.
- `string`: any non-empty value passes.
- `any`: always passes unless required and empty.

- [ ] **Step 4: Run cell-validator tests**

Run:

```bash
python -m pytest tests/test_cell_validator.py -q
```

Expected: PASS.

---

### Task 5: Template-Driven Pipeline

**Files:**
- Create: `src/template_driven_validator.py`
- Modify: `main.py`
- Test: `tests/test_template_driven_pipeline.py`

- [ ] **Step 1: Write failing integration test**

```python
import openpyxl

from src.template_driven_validator import validate_workbook


def test_template_driven_pipeline_starts_at_sequence_one_and_returns_cell_errors(tmp_path):
    template = tmp_path / "template.xlsx"
    data = tmp_path / "data.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "资产基本信息调研表"
    ws["A1"] = "一、资产基础法律属性"
    ws["A2"] = "序号"
    ws["A3"] = "序号"
    ws["A4"] = "1"
    ws["B1"] = "一、资产基础法律属性"
    ws["B2"] = "资产来源"
    ws["B3"] = "划转/购入/自建"
    ws["B4"] = "划转/购入/自建"
    wb.save(template)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "资产基本信息调研表"
    ws["A1"] = "汇总"
    ws["A2"] = "一、资产基础法律属性"
    ws["A3"] = "序号"
    ws["A4"] = "序号"
    ws["A5"] = "说明行"
    ws["A6"] = 1
    ws["B2"] = "一、资产基础法律属性"
    ws["B3"] = "资产来源"
    ws["B4"] = "划转/购入/自建"
    ws["B6"] = "新建"
    wb.save(data)

    result = validate_workbook(template, data, "资产基本信息调研表")

    assert result.data_start_row == 6
    assert len(result.errors) == 1
    assert result.errors[0]["Excel行号"] == 6
    assert result.errors[0]["Excel列号"] == "B"
    assert result.errors[0]["原始值"] == "新建"
```

- [ ] **Step 2: Run integration test to verify it fails**

Run:

```bash
python -m pytest tests/test_template_driven_pipeline.py -q
```

Expected: FAIL because `src.template_driven_validator` does not exist.

- [ ] **Step 3: Implement pipeline**

`validate_workbook` should:

1. Parse template field rules.
2. Parse data workbook header columns.
3. Match columns by normalized field key.
4. Find `序号=1` start row.
5. Iterate each non-empty data row from the start row.
6. Validate each matched cell.
7. Return `ValidationResult(data_start_row, errors)`.

- [ ] **Step 4: Run integration test**

Run:

```bash
python -m pytest tests/test_template_driven_pipeline.py -q
```

Expected: PASS.

---

### Task 6: Output Writer Replaces Invalid Values with `/`

**Files:**
- Create: `src/output_writer.py`
- Test: `tests/test_output_writer.py`

- [ ] **Step 1: Write failing test**

```python
import openpyxl

from src.output_writer import write_validated_workbook


def test_output_writer_replaces_error_cell_with_slash_and_keeps_original_in_detail(tmp_path):
    source = tmp_path / "data.xlsx"
    output = tmp_path / "output.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "资产基本信息调研表"
    ws["B6"] = "新建"
    wb.save(source)

    write_validated_workbook(
        source,
        output,
        [
            {
                "Excel行号": 6,
                "Excel列号": "B",
                "字段名": "资产来源",
                "原始值": "新建",
                "错误类型": "枚举错误",
                "错误说明": "允许值：划转/购入/自建",
            }
        ],
    )

    result = openpyxl.load_workbook(output)
    sheet = result["资产基本信息调研表"]
    assert sheet["B6"].value == "/"
    assert sheet["B6"].fill.fgColor.rgb == "FFFFC7CE"
    detail = result["错误明细"]
    assert detail["D2"].value == "新建"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_output_writer.py -q
```

Expected: FAIL because `src.output_writer` does not exist.

- [ ] **Step 3: Implement writer**

Use `openpyxl.load_workbook(source)`, mutate the first/data sheet, create or replace `错误明细`, save output.

- [ ] **Step 4: Run writer test**

Run:

```bash
python -m pytest tests/test_output_writer.py -q
```

Expected: PASS.

---

### Task 7: Wire `main.py` to the New Pipeline

**Files:**
- Modify: `main.py`
- Keep: `src/app_config.py`
- Test: existing full suite plus `python main.py`

- [ ] **Step 1: Replace old parser/validator calls**

`main.py` should call:

```python
from src.output_writer import write_validated_workbook
from src.template_driven_validator import validate_workbook


def main() -> None:
    config = resolve_run_config()
    result = validate_workbook(config.template, config.summary, sheet_name="资产基本信息调研表")
    write_validated_workbook(config.summary, config.output, result.errors)
    print(f"校验完成，数据错误 {len(result.errors)} 个")
    print(f"报告路径：{config.output}")
```

- [ ] **Step 2: Run all tests**

Run:

```bash
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run compile check**

Run:

```bash
python -m compileall -q .
```

Expected: exit code 0.

- [ ] **Step 4: Run real command**

Run:

```bash
python main.py
```

Expected: generates an `output/校验错误报告_YYYYMMDD_HHMMSS.xlsx` file. In the output workbook, invalid source cells are replaced with `/`, red-filled, and `错误明细` contains original values.

---

## Migration Notes

- Keep existing `src/validators.py`, `src/summary_parser.py`, and `src/report_writer.py` during the first pass to avoid breaking tests abruptly.
- Once the new pipeline is green, either delete old modules in a separate cleanup task or leave them as compatibility code.
- YAML should become overrides only. The first implementation can keep existing `config/asset_basic_info_rules.yaml`, but the validator should prefer template-inferred rules for enum/list/unit detection.
- Existing output sheets `汇总概览`, `结构错误`, `数据错误` can be replaced by a single `错误明细` sheet for this new flow unless backward compatibility is required.

## Verification Checklist

- `python -m pytest -q` passes.
- `python -m compileall -q .` passes.
- `python main.py` runs against the real input files.
- Output workbook preserves original workbook styles outside error cells.
- Error cells contain `/`.
- Error cells are red-filled.
- `错误明细` records the original invalid value.
- Rows before the first `序号=1` are not validated.
