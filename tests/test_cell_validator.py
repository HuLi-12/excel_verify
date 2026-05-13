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


def test_number_rule_accepts_positive_decimal():
    assert validate_cell("23500.5", {"type": "number", "min": 0}) is None
