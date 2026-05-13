from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.excel_loader import TableMeta
from src.validators import validate_data


def validate_business_rules(
    summary_df: pd.DataFrame,
    summary_meta: TableMeta,
    rule_path: str | Path,
) -> list[dict[str, Any]]:
    return validate_data(summary_df, summary_meta, rule_path)
