from __future__ import annotations

from pathlib import Path
from typing import Any

from src.excel_loader import TableMeta, load_rules


def build_rule_context(table_meta: TableMeta, rule_path: str | Path) -> dict[str, Any]:
    rules = load_rules(rule_path)
    return {
        "columns": table_meta.field_names,
        "required_keywords": rules.get("required_keywords", []),
        "numeric_keywords": rules.get("numeric_keywords", []),
        "enum_rules": rules.get("enum_rules", {}),
        "phone_rules": rules.get("phone_rules", []),
    }
