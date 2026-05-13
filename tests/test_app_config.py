from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from src.app_config import resolve_run_config


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"placeholder")
    return path


def test_resolve_run_config_reads_app_yaml_defaults(tmp_path):
    _touch(tmp_path / "input" / "模板.xlsx")
    _touch(tmp_path / "input" / "汇总.xlsx")
    _touch(tmp_path / "config" / "rules.yaml")
    app_config = tmp_path / "config" / "app.yaml"
    app_config.write_text(
        """
template_path: input/模板.xlsx
summary_path: input/汇总.xlsx
rule_path: config/rules.yaml
output_dir: reports
""",
        encoding="utf-8",
    )

    config = resolve_run_config(
        [],
        project_root=tmp_path,
        now=datetime(2026, 5, 13, 14, 30, 5),
    )

    assert config.template == tmp_path / "input" / "模板.xlsx"
    assert config.summary == tmp_path / "input" / "汇总.xlsx"
    assert config.rules == tmp_path / "config" / "rules.yaml"
    assert config.output == tmp_path / "reports" / "校验错误报告_20260513_143005.xlsx"


def test_resolve_run_config_cli_args_override_app_yaml(tmp_path):
    _touch(tmp_path / "input" / "配置模板.xlsx")
    _touch(tmp_path / "input" / "配置汇总.xlsx")
    cli_summary = _touch(tmp_path / "input" / "临时汇总.xlsx")
    cli_output = tmp_path / "output" / "临时报告.xlsx"
    _touch(tmp_path / "config" / "asset_basic_info_rules.yaml")
    (tmp_path / "config" / "app.yaml").write_text(
        """
template_path: input/配置模板.xlsx
summary_path: input/配置汇总.xlsx
output_dir: output
""",
        encoding="utf-8",
    )

    config = resolve_run_config(
        ["--summary", str(cli_summary), "--output", str(cli_output)],
        project_root=tmp_path,
        now=datetime(2026, 5, 13, 14, 30, 5),
    )

    assert config.template == tmp_path / "input" / "配置模板.xlsx"
    assert config.summary == cli_summary
    assert config.output == cli_output


def test_resolve_run_config_auto_discovers_input_files_when_app_yaml_missing(tmp_path):
    template = _touch(tmp_path / "input" / "资产基本信息表(1).xlsx")
    summary = _touch(tmp_path / "input" / "汇总表截止20260416.xlsx")
    rules = _touch(tmp_path / "config" / "asset_basic_info_rules.yaml")

    config = resolve_run_config(
        [],
        project_root=tmp_path,
        now=datetime(2026, 5, 13, 14, 30, 5),
    )

    assert config.template == template
    assert config.summary == summary
    assert config.rules == rules
    assert config.output == tmp_path / "output" / "校验错误报告_20260513_143005.xlsx"


def test_resolve_run_config_ignores_excel_lock_files(tmp_path):
    _touch(tmp_path / "input" / "~$资产基本信息表(1).xlsx")
    _touch(tmp_path / "input" / "~$汇总表截止20260416.xlsx")
    _touch(tmp_path / "config" / "asset_basic_info_rules.yaml")

    with pytest.raises(FileNotFoundError, match="未找到模板 Excel"):
        resolve_run_config([], project_root=tmp_path, now=datetime(2026, 5, 13, 14, 30, 5))
