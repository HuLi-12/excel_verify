# 资产基本信息表校验工具

本项目是本地命令行版 Excel 校验 MVP：

- 解析模板表和汇总表的多行表头、合并单元格
- 对比模板字段和汇总表字段
- 检查缺字段、多字段、字段顺序、空表头列有数据
- 按 YAML 规则检查必填、数值、枚举、手机号
- 输出保留原汇总表格式的 `校验错误报告.xlsx`
- 对错误单元格标红，并添加批注说明错误类型
- 附加 `汇总概览`、`结构错误`、`数据错误` 三个 sheet

## 安装依赖

```bash
pip install -r requirements.txt
```

## 文件位置

默认输入路径：

```text
input/资产基本信息表(1).xlsx
input/汇总表截止20260416.xlsx
```

默认规则：

```text
config/asset_basic_info_rules.yaml
```

默认运行配置：

```text
config/app.yaml
```

示例：

```yaml
input_dir: input
template_path: input/资产基本信息表(1).xlsx
summary_path: input/汇总表截止20260416.xlsx
rule_path: config/asset_basic_info_rules.yaml
output_dir: output
```

默认输出会自动加时间戳：

```text
output/校验错误报告_YYYYMMDD_HHMMSS.xlsx
```

输出文件会复制待校验汇总表的原始工作表和格式，然后在错误单元格上标红。
因为默认输出带时间戳，通常不会被 Excel 或 WPS 的文件占用影响；如果通过 `--output` 指定固定文件名，请先关闭同名文件。

## 运行

```bash
python main.py
```

路径优先级：

```text
命令行参数 > config/app.yaml > 自动扫描 input/
```

临时换一个汇总表：

```bash
python main.py --summary "input/新的汇总表.xlsx"
```

显式指定全部路径：

```bash
python main.py --template "input/资产基本信息表(1).xlsx" --summary "input/汇总表截止20260416.xlsx" --rules "config/asset_basic_info_rules.yaml" --output "output/校验错误报告.xlsx"
```

如果 `config/app.yaml` 不存在或没有配置模板/汇总表路径，程序会自动扫描 `input/`：

- 文件名包含 `资产基本信息表` 或 `模板` 的 Excel 作为模板
- 文件名包含 `汇总表` 或 `汇总` 的 Excel 作为待校验数据
- 自动忽略 Excel/WPS 生成的 `~$` 锁文件

## 测试

```bash
python -m pytest -q
```
