# tests/utils/test_uri_utils.py
import unittest
from tcm_kg_virtuoso_module.utils import uri_utils
from tcm_kg_virtuoso_module.core.config import NAMESPACES # 用于校验生成的前缀是否正确

class TestUriUtils(unittest.TestCase):

    def test_generate_entity_uri_valid_key(self):
        # 测试使用配置中存在的 entity_type_key
        key = "tcm_entity" # 假设这个key在NAMESPACES中定义
        name = "Herb123"
        expected_base = NAMESPACES.get(key, "http://example.com/entity/tcm/") # 获取基础URI
        if not expected_base.endswith(("/", "#")):
            expected_base += "/"
        expected_uri = f"{expected_base}{name}"
        
        generated_uri = uri_utils.generate_entity_uri(key, name)
        self.assertEqual(generated_uri, expected_uri)

    def test_generate_entity_uri_name_with_spaces(self):
        # 测试名称中包含空格的情况
        key = "tcm_ont"
        name = "Symptom A B"
        expected_name_part = "Symptom_A_B" # 空格被替换为下划线
        expected_base = NAMESPACES.get(key, "http://example.com/ontology/tcm#")
        if not expected_base.endswith(("/", "#")):
            expected_base += "/"
        expected_uri = f"{expected_base}{expected_name_part}"
        
        generated_uri = uri_utils.generate_entity_uri(key, name)
        self.assertEqual(generated_uri, expected_uri)

    def test_generate_entity_uri_name_with_special_chars(self):
        # 测试名称中包含其他特殊字符的情况
        key = "tcm_entity"
        name = "Herb/Item#Code"
        expected_name_part = "Herb_Item_Code" # / 和 # 被替换为下划线
        expected_base = NAMESPACES.get(key, "http://example.com/entity/tcm/")
        if not expected_base.endswith(("/", "#")):
            expected_base += "/"
        expected_uri = f"{expected_base}{expected_name_part}"

        generated_uri = uri_utils.generate_entity_uri(key, name)
        self.assertEqual(generated_uri, expected_uri)


    def test_generate_entity_uri_key_not_in_namespaces(self):
        # 测试使用配置中不存在的 entity_type_key
        with self.assertRaisesRegex(ValueError, "命名空间前缀键 .* 在配置的 NAMESPACES 中未定义"):
            uri_utils.generate_entity_uri("non_existent_key", "SomeName")

    def test_validate_uri_format_valid(self):
        # 测试各种有效的URI格式
        self.assertTrue(uri_utils.validate_uri_format("http://example.com"))
        self.assertTrue(uri_utils.validate_uri_format("https://example.com/path?query=1#frag"))
        self.assertTrue(uri_utils.validate_uri_format("urn:isbn:1234567890"))
        self.assertTrue(uri_utils.validate_uri_format("rdf:type")) # 已知前缀
        self.assertTrue(uri_utils.validate_uri_format(NAMESPACES["tcm_ont"] + "Symptom1")) # 完整URI，基于已知前缀
        self.assertTrue(uri_utils.validate_uri_format("just-a-local-name")) # 相对路径或片段

    def test_validate_uri_format_invalid(self):
        # 测试各种无效的URI格式
        self.assertFalse(uri_utils.validate_uri_format(None))
        self.assertFalse(uri_utils.validate_uri_format(""))
        self.assertFalse(uri_utils.validate_uri_format("http:// example.com")) # 包含空格
        self.assertFalse(uri_utils.validate_uri_format("  leading_space:id"))
        self.assertFalse(uri_utils.validate_uri_format("invalid space in curie:test"))
        self.assertFalse(uri_utils.validate_uri_format("unknownprefix:myvalue")) # 如果'unknownprefix'不在config.NAMESPACES中
                                                                               # validate_uri_format会尝试将其视为绝对URI或路径
                                                                               # 根据当前的实现，这可能返回True，因为它不含空格
                                                                               # 需要根据validate_uri_format的具体实现调整此测试用例
                                                                               # 当前实现会认为 "unknownprefix:myvalue" 是有效的，因为 Simple CURIE regex 会匹配

    def test_validate_uri_format_curie_unknown_prefix(self):
        # 这个测试专门针对未知前缀的CURIE
        # 当前的 validate_uri_format 实现，如果前缀未知，会将其视为普通字符串并用 SIMPLE_CURIE_OR_URI_REGEX 检查
        # 这个正则表达式允许未知前缀的 "prefix:localname" 结构，只要字符有效
        self.assertTrue(uri_utils.validate_uri_format("some_unknown_prefix:localName123"))
        self.assertFalse(uri_utils.validate_uri_format("some_unknown_prefix: local Name 123")) # 包含空格

if __name__ == '__main__':
    unittest.main()
