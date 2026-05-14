from src.cell_validator import validate_cell


def test_validate_enum_rejects_unknown_value():
    error = validate_cell("新建", {"type": "enum", "allowed_values": ["划转", "购入", "自建"]})
    assert error["错误类型"] == "枚举错误"


def test_validate_list_normalizes_english_semicolon():
    error = validate_cell("500;1200", {"type": "list", "separator": "；", "item_type": "positive_integer"})
    assert error["status"] == "NORMALIZED"
    assert error["输出值"] == "500；1200"


def test_validate_number_with_unit_requires_exact_unit():
    assert validate_cell("500平方米", {"type": "number_with_unit", "unit": "平方米"}) is None
    error = validate_cell("500㎡", {"type": "number_with_unit", "unit": "平方米"})
    assert error["错误类型"] == "单位数值错误"


def test_required_field_rejects_special_empty():
    error = validate_cell("/", {"type": "string"}, required=True, allow_special_empty=False)
    assert error["错误类型"] == "必填项为空"


def test_number_rule_accepts_positive_decimal():
    assert validate_cell("23500.5", {"type": "number", "min": 0}) is None


def test_list_with_english_semicolon_is_normalized():
    result = validate_cell("500;1200;1350", {"type": "list", "separator": "；", "item_type": "positive_integer"})
    assert result["status"] == "NORMALIZED"
    assert result["原始值"] == "500;1200;1350"
    assert result["输出值"] == "500；1200；1350"


def test_list_with_comma_separator_is_warning():
    result = validate_cell("500,1200,1350", {"type": "list", "separator": "；", "item_type": "positive_integer"})
    assert result["status"] == "WARNING"
    assert result["输出值"] == "500,1200,1350"


def test_structured_field_with_none_text_is_warning():
    result = validate_cell("无", {"type": "number", "min": 0})
    assert result["status"] == "WARNING"
    assert result["警告类型"] == "结构化字段填写无"


def test_list_containing_none_text_is_error():
    result = validate_cell("500；无；1350", {"type": "list", "separator": "；", "item_type": "positive_integer"})
    assert result["status"] == "ERROR"
    assert result["错误类型"] == "列表格式错误"


def test_date_rule_normalizes_supported_formats_and_rejects_invalid_dates():
    rule = {"type": "date", "format": "yyyy.MM.dd"}
    normalized = validate_cell("2026-5-6", rule)
    assert normalized["status"] == "NORMALIZED"
    assert normalized["输出值"] == "2026.05.06"

    invalid = validate_cell("2026-13-01", rule)
    assert invalid["status"] == "ERROR"
    assert invalid["错误类型"] == "日期错误"


def test_preprocessing_removes_spaces_and_trailing_period_before_enum_validation():
    result = validate_cell("划 转。", {"type": "enum", "allowed_values": ["划转", "购入", "自建"]})
    assert result["status"] == "NORMALIZED"
    assert result["原始值"] == "划 转。"
    assert result["输出值"] == "划转"
    assert "删除空白字符" in result["修正说明"]
    assert "删除末尾句号" in result["修正说明"]


def test_preprocessing_removes_spaces_before_unit_and_date_validation():
    unit_result = validate_cell("500 平方米。", {"type": "number_with_unit", "unit": "平方米"})
    assert unit_result["status"] == "NORMALIZED"
    assert unit_result["输出值"] == "500平方米"

    date_result = validate_cell("2026 - 05 - 06", {"type": "date", "format": "yyyy.MM.dd"})
    assert date_result["status"] == "NORMALIZED"
    assert date_result["输出值"] == "2026.05.06"


def test_phone_rule_validates_and_normalizes_spaces():
    normalized = validate_cell("138 0000 0000", {"type": "phone"})
    assert normalized["status"] == "NORMALIZED"
    assert normalized["输出值"] == "13800000000"

    invalid = validate_cell("123456", {"type": "phone"})
    assert invalid["status"] == "ERROR"
    assert invalid["错误类型"] == "手机号错误"


def test_id_card_rule_validates_and_uppercases_x():
    normalized = validate_cell("11010519491231002x", {"type": "id_card"})
    assert normalized["status"] == "NORMALIZED"
    assert normalized["输出值"] == "11010519491231002X"

    invalid = validate_cell("11010519491231002A", {"type": "id_card"})
    assert invalid["status"] == "ERROR"
    assert invalid["错误类型"] == "身份证号错误"
