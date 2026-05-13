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
