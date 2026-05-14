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


def test_infer_enum_from_field_path_when_sample_is_one_allowed_value():
    rule = infer_rule("一、资产基础法律属性_资产来源_划转/购入/自建", "购入")
    assert rule["type"] == "enum"
    assert rule["allowed_values"] == ["划转", "购入", "自建"]


def test_slash_in_company_placeholder_is_string_not_enum():
    rule = infer_rule("一、资产基础法律属性_管理责任单位_明确的一级/二级企业名称", "南昌市X投集团/XX公司")
    assert rule["type"] == "string"


def test_infer_ignores_template_sample_prefix():
    assert infer_rule("序号", "填报示例：1")["type"] == "positive_integer"


def test_phone_placeholder_with_x_is_string_not_unit_number():
    assert infer_rule("联系电话_手机", "139XXXXXXXX")["type"] == "phone"


def test_infer_id_card_rule_from_field_name():
    assert infer_rule("联系人_身份证号", "510xxxxxxxxxxxxxxx")["type"] == "id_card"


def test_list_inference_ignores_newlines_and_trailing_chinese_period():
    rule = infer_rule("附近地铁站距离（m）", "500；\n1200；\n1350。")
    assert rule == {
        "type": "list",
        "separator": "；",
        "item_type": "positive_integer",
    }


def test_area_field_with_integer_sample_allows_decimal_number():
    rule = infer_rule("二、空间与物理指标_有产权面积_建筑面积（平方米）", 23500)
    assert rule["type"] == "number"
    assert rule["min"] == 0


def test_area_list_with_integer_samples_allows_decimal_items():
    rule = infer_rule("分项面积", "500；1200；1350")
    assert rule == {
        "type": "list",
        "separator": "；",
        "item_type": "number",
    }


def test_infer_date_rule_from_template_sample_format():
    assert infer_rule("合同签订日期", "2026.05.06") == {"type": "date", "format": "yyyy.MM.dd"}
    assert infer_rule("合同签订日期", "2026-05-06") == {"type": "date", "format": "yyyy-MM-dd"}
    assert infer_rule("合同签订日期", "20260506") == {"type": "date", "format": "yyyyMMdd"}
