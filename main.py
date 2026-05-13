from __future__ import annotations

from src.app_config import resolve_run_config
from src.output_writer import write_validated_workbook
from src.template_driven_validator import validate_workbook


def main() -> None:
    config = resolve_run_config()

    result = validate_workbook(config.template, config.summary, sheet_name="资产基本信息调研表")
    write_validated_workbook(config.summary, config.output, result.errors)

    print(f"校验完成，数据错误 {len(result.errors)} 个")
    print(f"报告路径：{config.output}")


if __name__ == "__main__":
    main()
