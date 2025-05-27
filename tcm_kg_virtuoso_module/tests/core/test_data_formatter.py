# tcm_kg_virtuoso_module/tests/core/test_data_formatter.py
import unittest
from unittest.mock import patch, MagicMock

# 导入需要测试的函数和常量
# Import functions and constants to be tested
from tcm_kg_virtuoso_module.core.data_formatter import (
    format_uri,
    escape_literal_value,
    format_literal,
    create_rdf_triple,
    COMMON_DATATYPES # 如果测试中直接使用或验证此常量，则导入
                     # Import if this constant is directly used or verified in tests
)
# from tcm_kg_virtuoso_module.config import settings # 真实 settings 不应在测试中直接导入，除非特殊情况
                                                  # Real settings should not be directly imported in tests, except for special cases

# 模拟 settings 模块，因为 data_formatter.py 中的 DEFAULT_PREFIXES 间接依赖于 settings
# Mock the settings module, as DEFAULT_PREFIXES in data_formatter.py indirectly depends on settings
# 尽管 COMMON_DATATYPES 主要使用 xsd 前缀（静态定义），但为了模块加载的完整性和未来可能的扩展，
# 最好 mock settings。
# Although COMMON_DATATYPES primarily uses the xsd prefix (statically defined), 
# it's best to mock settings for the completeness of module loading and future potential extensions.
mock_settings_for_formatter = MagicMock()
mock_settings_for_formatter.DEFAULT_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#", # 这是 COMMON_DATATYPES 主要依赖的
                                                # This is what COMMON_DATATYPES mainly relies on
    "dcterms": "http://purl.org/dc/terms/",
    "tcm-entity": "http://tcm.example.org/entity/", # 示例值
                                                    # Example value
    "tcm-onto": "http://tcm.example.org/ontology/",   # 示例值
                                                    # Example value
    "tcm-source": "http://tcm.example.org/source/", # 示例值
                                                  # Example value
}
# 我们还需要确保在 data_formatter 模块加载时，它能找到这个 mock 过的 DEFAULT_PREFIXES。
# We also need to ensure that when the data_formatter module loads, it can find this mocked DEFAULT_PREFIXES.
# 因此，patch 的目标应该是 'tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES'
# So, the patch target should be 'tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES'
# 或者，如果 DEFAULT_PREFIXES 是从 settings 导入的，那么 patch 'tcm_kg_virtuoso_module.config.settings.DEFAULT_PREFIXES'
# Or, if DEFAULT_PREFIXES is imported from settings, then patch 'tcm_kg_virtuoso_module.config.settings.DEFAULT_PREFIXES'
# 查阅 data_formatter.py，它直接从 config.settings 导入 DEFAULT_PREFIXES。
# Consulting data_formatter.py, it directly imports DEFAULT_PREFIXES from config.settings.
# 所以 patch 路径应为 'tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES'
# So the patch path should be 'tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES'
# 或者是 'tcm_kg_virtuoso_module.config.settings.DEFAULT_PREFIXES' 如果 COMMON_DATATYPES 在 data_formatter.py 中构建时直接使用了导入的 settings.DEFAULT_PREFIXES
# Or 'tcm_kg_virtuoso_module.config.settings.DEFAULT_PREFIXES' if COMMON_DATATYPES uses the imported settings.DEFAULT_PREFIXES directly when constructed in data_formatter.py
# 在 data_formatter.py 中: `from tcm_kg_virtuoso_module.config.settings import DEFAULT_PREFIXES`
# In data_formatter.py: `from tcm_kg_virtuoso_module.config.settings import DEFAULT_PREFIXES`
# 然后 `COMMON_DATATYPES = { "string": f"{DEFAULT_PREFIXES['xsd']}string", ... }`
# Then `COMMON_DATATYPES = { "string": f"{DEFAULT_PREFIXES['xsd']}string", ... }`
# 这意味着我们需要 patch `tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES` 这个被导入的名称。
# This means we need to patch `tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES` which is the imported name.

@patch('tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES', mock_settings_for_formatter.DEFAULT_PREFIXES)
class TestDataFormatter(unittest.TestCase):

    def test_format_uri(self):
        # 测试 URI 格式化
        self.assertEqual(format_uri("http://example.com/res"), "<http://example.com/res>")
        self.assertEqual(format_uri("<http://example.com/res2>"), "<http://example.com/res2>") # 已有括号
        self.assertEqual(format_uri(123), "<123>") # 数字输入，应转换为字符串并加括号
                                                 # Numeric input, should be converted to string and bracketed
        self.assertEqual(format_uri(""), "<>") # 空字符串
                                           # Empty string

    def test_escape_literal_value(self):
        # 测试字面量值的转义
        self.assertEqual(escape_literal_value("simple"), "simple")
        self.assertEqual(escape_literal_value('with "quotes"'), 'with \\"quotes\\"')
        self.assertEqual(escape_literal_value("with \\backslash"), "with \\\\backslash")
        self.assertEqual(escape_literal_value("new\nline"), "new\\nline")
        self.assertEqual(escape_literal_value("carriage\rreturn"), "carriage\\rreturn")
        self.assertEqual(escape_literal_value("tab\tchar"), "tab\\tchar")
        self.assertEqual(escape_literal_value('all: \\"\n\r\t'), 'all: \\\\\\\"\\n\\r\\t') # 混合
                                                                                        # Mixed
        self.assertEqual(escape_literal_value(123), "123") # 数字也应字符串化
                                                          # Numbers should also be stringified

    def test_format_literal_plain(self):
        # 测试普通字面量 (无数据类型，无语言标签)
        self.assertEqual(format_literal("hello"), '"hello"')
        self.assertEqual(format_literal(123.45), '"123.45"') # 数字输入
                                                            # Numeric input
        self.assertEqual(format_literal(True), '"True"')     # 布尔输入
                                                            # Boolean input

    def test_format_literal_with_known_datatype(self):
        # 测试带已知数据类型的字面量 (从 COMMON_DATATYPES)
        # COMMON_DATATYPES 在测试开始时应该已经被 mock 的 DEFAULT_PREFIXES['xsd'] 正确构建
        # COMMON_DATATYPES should be correctly constructed with the mocked DEFAULT_PREFIXES['xsd'] at the start of the test
        expected_int_dt = mock_settings_for_formatter.DEFAULT_PREFIXES['xsd'] + "integer"
        self.assertEqual(format_literal(42, datatype="integer"), f'"42"^^<{expected_int_dt}>')
        
        expected_bool_dt = mock_settings_for_formatter.DEFAULT_PREFIXES['xsd'] + "boolean"
        self.assertEqual(format_literal(True, datatype="boolean"), f'"True"^^<{expected_bool_dt}>')

        expected_str_dt = mock_settings_for_formatter.DEFAULT_PREFIXES['xsd'] + "string"
        self.assertEqual(format_literal("text", datatype="string"), f'"text"^^<{expected_str_dt}>')

    def test_format_literal_with_full_uri_datatype(self):
        # 测试带完整 URI 作为数据类型的字面量
        dt_uri = "http://mycustom.com/datatype#specialString"
        self.assertEqual(format_literal("special", datatype=dt_uri), f'"special"^^<{dt_uri}>')

    @patch('builtins.print') # 用于捕获 format_literal 中的警告打印
                             # Used to capture warning prints in format_literal
    def test_format_literal_with_unknown_short_datatype(self, mock_print):
        # 测试使用未在 COMMON_DATATYPES 中定义的短格式数据类型
        # (应回退到普通字面量，并打印警告)
        # (Should fall back to plain literal and print a warning)
        self.assertEqual(format_literal("unknown type", datatype="nonExistentType"), '"unknown type"')
        # 检查是否打印了预期的警告信息
        # Check if the expected warning message was printed
        mock_print.assert_any_call("警告：数据类型 'nonExistentType' 未被识别。将省略数据类型。")

    def test_format_literal_with_lang_tag(self):
        # 测试带语言标签的字面量
        self.assertEqual(format_literal("你好", lang="zh"), '"你好"@zh')
        self.assertEqual(format_literal("Hello", lang="en-US"), '"Hello"@en-US')
        self.assertEqual(format_literal(123, lang="num"), '"123"@num') # 数字作为值，带语言标签
                                                                    # Number as value, with language tag

    @patch('builtins.print')
    def test_format_literal_invalid_lang_tag(self, mock_print):
        # 测试无效的语言标签 (例如，非字符串或空字符串)
        # Test invalid language tags (e.g., non-string or empty string)
        self.assertEqual(format_literal("text", lang=""), '"text"') # 空语言标签
        mock_print.assert_any_call("警告：语言标签 '' 无效。将省略语言标签。")
        mock_print.reset_mock()
        self.assertEqual(format_literal("text", lang=None), '"text"') # None 语言标签
        # 根据当前实现，None lang 不会触发警告，直接跳过 lang 处理
        # According to the current implementation, None lang does not trigger a warning, it skips lang processing
        mock_print.assert_not_called() 

    def test_format_literal_datatype_preferred_over_lang(self):
        # 测试同时提供数据类型和语言标签时，数据类型优先
        expected_str_dt = mock_settings_for_formatter.DEFAULT_PREFIXES['xsd'] + "string"
        self.assertEqual(format_literal("text", datatype="string", lang="en"), f'"text"^^<{expected_str_dt}>')
        # 此时不应打印关于 lang 的警告，因为它被 datatype 覆盖了
        # No warning about lang should be printed at this time, as it is overridden by datatype

    def test_format_literal_with_escaping(self):
        # 测试值中包含需要转义的字符的字面量格式化
        val_to_escape = 'text with "quotes" and \\ backslash, also \n newline.'
        escaped_val = 'text with \\"quotes\\" and \\\\ backslash, also \\n newline.'
        self.assertEqual(format_literal(val_to_escape), f'"{escaped_val}"')

        # 带数据类型
        expected_str_dt = mock_settings_for_formatter.DEFAULT_PREFIXES['xsd'] + "string"
        self.assertEqual(format_literal(val_to_escape, datatype="string"), f'"{escaped_val}"^^<{expected_str_dt}>')

        # 带语言标签
        self.assertEqual(format_literal(val_to_escape, lang="en"), f'"{escaped_val}"@en')

    def test_create_rdf_triple_all_uris(self):
        # 测试所有部分都是 URI 的RDF三元组创建
        s, p, o = "http://example.com/s", "http://example.com/p", "http://example.com/o"
        self.assertEqual(create_rdf_triple(s, p, o), f"<{s}> <{p}> <{o}> .")
        
        # 测试包含已加括号的URI
        # Test with already bracketed URIs
        s_br = "<http://example.com/s_br>"
        p_br = "http://example.com/p_br" # 未加括号
                                         # Not bracketed
        o_br = "<http://example.com/o_br>"
        self.assertEqual(create_rdf_triple(s_br, p_br, o_br), f"{s_br} <{p_br}> {o_br} .")

    def test_create_rdf_triple_with_literal_object(self):
        # 测试宾语是字面量的RDF三元组创建
        s, p = "http://example.com/s", "http://example.com/p"
        
        # 宾语是一个普通字面量
        # Object is a plain literal
        obj_plain_literal_val = "A simple literal"
        formatted_obj_plain = format_literal(obj_plain_literal_val) # 预先格式化
                                                                    # Pre-format
        self.assertEqual(create_rdf_triple(s, p, formatted_obj_plain, is_object_literal=True),
                         f"<{s}> <{p}> {formatted_obj_plain} .")

        # 宾语是一个带数据类型的字面量
        # Object is a literal with a datatype
        obj_typed_literal_val = 100
        expected_int_dt = mock_settings_for_formatter.DEFAULT_PREFIXES['xsd'] + "integer"
        formatted_obj_typed = format_literal(obj_typed_literal_val, datatype="integer")
        self.assertEqual(formatted_obj_typed, f'"100"^^<{expected_int_dt}>') # 确认字面量格式
                                                                          # Confirm literal format
        self.assertEqual(create_rdf_triple(s, p, formatted_obj_typed, is_object_literal=True),
                         f"<{s}> <{p}> {formatted_obj_typed} .")

        # 宾语是一个带语言标签的字面量
        # Object is a literal with a language tag
        obj_lang_literal_val = "你好"
        formatted_obj_lang = format_literal(obj_lang_literal_val, lang="zh-CN")
        self.assertEqual(formatted_obj_lang, '"你好"@zh-CN') # 确认字面量格式
                                                          # Confirm literal format
        self.assertEqual(create_rdf_triple(s, p, formatted_obj_lang, is_object_literal=True),
                         f"<{s}> <{p}> {formatted_obj_lang} .")

    def test_create_rdf_triple_object_is_uri_mistakenly_not_literal(self):
        # 测试当对象是URI，但错误地未将 is_object_literal 设置为 False (或省略，默认为False)
        # Test when the object is a URI, but is_object_literal is mistakenly not set to False (or omitted, defaulting to False)
        s, p, o_uri = "http://s.com", "http://p.com", "http://o.com/uri"
        # 默认 is_object_literal=False，所以 o_uri 会被 format_uri 处理
        # Default is_object_literal=False, so o_uri will be processed by format_uri
        self.assertEqual(create_rdf_triple(s, p, o_uri), f"<{s}> <{p}> <{o_uri}> .")
        # 如果 o_uri 已经是 <...> 格式
        # If o_uri is already in <...> format
        self.assertEqual(create_rdf_triple(s, p, f"<{o_uri}>"), f"<{s}> <{p}> <{o_uri}> .")

if __name__ == '__main__':
    # 这使得测试可以直接从命令行运行
    # This allows tests to be run directly from the command line
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
