from __future__ import annotations

from src.app_config import resolve_run_config
from src.output_writer import write_validated_workbook
from src.template_driven_validator import validate_workbook


def main() -> None:
    config = resolve_run_config()

    result = validate_workbook(config.template, config.summary, sheet_name="资产基本信息调研表")
    write_validated_workbook(
        config.summary,
        config.output,
        result.errors,
        replace_error_values=config.replace_error_values,
        generate_error_detail_sheet=config.generate_error_detail_sheet,
    )

    error_count = sum(1 for item in result.errors if item.get("status", "ERROR") == "ERROR")
    warning_count = sum(1 for item in result.errors if item.get("status") == "WARNING")
    normalized_count = sum(1 for item in result.errors if item.get("status") == "NORMALIZED")
    print(f"校验完成，错误 {error_count} 个，警告 {warning_count} 个，自动修正 {normalized_count} 个")
    print(f"报告路径：{config.output}")


if __name__ == "__main__":
    main()
