from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from src.excel_loader import load_rules


DEFAULT_CONFIG_PATH = Path("config/app.yaml")
DEFAULT_RULE_PATH = Path("config/asset_basic_info_rules.yaml")
DEFAULT_INPUT_DIR = Path("input")
DEFAULT_OUTPUT_DIR = Path("output")
TEMPLATE_KEYWORDS = ["资产基本信息表", "模板"]
SUMMARY_KEYWORDS = ["汇总表", "汇总"]


@dataclass(frozen=True)
class RunConfig:
    template: Path
    summary: Path
    rules: Path
    output: Path


def resolve_run_config(
    argv: Sequence[str] | None = None,
    project_root: Path | None = None,
    now: datetime | None = None,
) -> RunConfig:
    root = (project_root or Path.cwd()).resolve()
    current_time = now or datetime.now()
    args = _parse_args(argv)
    app_config = _load_app_config(_resolve_path(root, args.config))

    template = _configured_or_discovered_path(
        root=root,
        cli_value=args.template,
        config_value=app_config.get("template_path"),
        input_dir=app_config.get("input_dir"),
        keywords=TEMPLATE_KEYWORDS,
        missing_message="未找到模板 Excel，请在 config/app.yaml 配置 template_path，或使用 --template 指定。",
    )
    summary = _configured_or_discovered_path(
        root=root,
        cli_value=args.summary,
        config_value=app_config.get("summary_path"),
        input_dir=app_config.get("input_dir"),
        keywords=SUMMARY_KEYWORDS,
        missing_message="未找到汇总 Excel，请在 config/app.yaml 配置 summary_path，或使用 --summary 指定。",
    )
    rules = _resolve_existing_path(
        root,
        args.rules or app_config.get("rule_path") or DEFAULT_RULE_PATH,
        "未找到规则 YAML，请在 config/app.yaml 配置 rule_path，或使用 --rules 指定。",
    )
    output = _resolve_output_path(root, args.output, app_config, current_time)

    return RunConfig(template=template, summary=summary, rules=rules, output=output)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="资产基本信息表 Excel 校验工具")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="运行配置 YAML 路径")
    parser.add_argument("--template", type=Path, help="模板 Excel 路径")
    parser.add_argument("--summary", type=Path, help="待校验汇总 Excel 路径")
    parser.add_argument("--rules", type=Path, help="YAML 规则配置路径")
    parser.add_argument("--output", type=Path, help="错误报告输出路径")
    return parser.parse_args(argv)


def _load_app_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    return load_rules(config_path)


def _configured_or_discovered_path(
    root: Path,
    cli_value: Path | None,
    config_value: str | Path | None,
    input_dir: str | Path | None,
    keywords: list[str],
    missing_message: str,
) -> Path:
    if cli_value or config_value:
        return _resolve_existing_path(root, cli_value or config_value, missing_message)

    discovered = _discover_excel(root / (input_dir or DEFAULT_INPUT_DIR), keywords)
    if not discovered:
        raise FileNotFoundError(missing_message)
    return discovered


def _resolve_existing_path(root: Path, value: str | Path, missing_message: str) -> Path:
    path = _resolve_path(root, value)
    if not path.exists():
        raise FileNotFoundError(f"{missing_message} 当前路径不存在：{path}")
    return path


def _resolve_output_path(
    root: Path,
    cli_output: Path | None,
    app_config: dict[str, Any],
    now: datetime,
) -> Path:
    if cli_output:
        return _resolve_path(root, cli_output)
    if app_config.get("output_path"):
        return _resolve_path(root, app_config["output_path"])

    output_dir = _resolve_path(root, app_config.get("output_dir") or DEFAULT_OUTPUT_DIR)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    return output_dir / f"校验错误报告_{timestamp}.xlsx"


def _discover_excel(input_dir: Path, keywords: list[str]) -> Path | None:
    if not input_dir.exists():
        return None

    candidates = [
        path
        for path in input_dir.glob("*.xlsx")
        if not path.name.startswith("~$") and any(keyword in path.name for keyword in keywords)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: (path.stat().st_mtime, path.name), reverse=True)[0]


def _resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path
