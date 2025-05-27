import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import quote

# 模拟 settings 对象
# Mock the settings object
mock_settings_uri = MagicMock()
mock_settings_uri.ENTITY_BASE_URI = "http://test.com/entity/"
mock_settings_uri.SOURCE_BASE_URI = "http://test.com/source/"

# 使用 patch 来替换真实的 settings 模块
# Use patch to replace the actual settings module
@patch('tcm_kg_virtuoso_module.core.uri_minter.settings', mock_settings_uri)
class TestUriMinter(unittest.TestCase):

    def setUp(self):
        # 动态导入被测试的函数，确保 mock 生效
        # Dynamically import the functions under test to ensure mocks are in effect
        from tcm_kg_virtuoso_module.core.uri_minter import mint_entity_uri, mint_source_uri
        self.mint_entity_uri = mint_entity_uri
        self.mint_source_uri = mint_source_uri
        mock_settings_uri.reset_mock() # 重置 mock 调用，如果需要
                                     # Reset mock calls if needed

    def test_mint_entity_uri_simple(self):
        # 测试简单的实体 URI 生成
        # Test simple entity URI generation
        uri = self.mint_entity_uri("Herb", "Ginseng")
        expected_uri = f"{mock_settings_uri.ENTITY_BASE_URI}{quote('Herb', safe='')}/{quote('Ginseng', safe='')}"
        self.assertEqual(uri, expected_uri)

    def test_mint_entity_uri_special_chars(self):
        # 测试包含特殊字符的实体 URI 生成
        # Test entity URI generation with special characters
        uri = self.mint_entity_uri("中药材", "当归/ Angelica")
        # "当归/ Angelica" 中的 / 会被编码
        # The / in "当归/ Angelica" will be encoded
        expected_uri = f"{mock_settings_uri.ENTITY_BASE_URI}{quote('中药材', safe='')}/{quote('当归/ Angelica', safe='')}"
        self.assertEqual(uri, expected_uri)
        self.assertIn(quote("/", safe=''), uri) # 检查斜杠是否被编码
                                  # Check if the slash is encoded

    def test_mint_entity_uri_with_args(self):
        # 测试带附加参数的实体 URI 生成
        # Test entity URI generation with additional arguments
        uri = self.mint_entity_uri("Formula", "XiaoYaoSan", "Variant1", "AnotherArg")
        expected_uri = f"{mock_settings_uri.ENTITY_BASE_URI}{quote('Formula', safe='')}/{quote('XiaoYaoSan', safe='')}/{quote('Variant1', safe='')}/{quote('AnotherArg', safe='')}"
        self.assertEqual(uri, expected_uri)

    def test_mint_source_uri_simple(self):
        # 测试简单的来源 URI 生成
        # Test simple source URI generation
        uri = self.mint_source_uri("Book", "ShangHanLun", "Chapter1", "Verse2")
        expected_uri = f"{mock_settings_uri.SOURCE_BASE_URI}{quote('Book', safe='')}/{quote('ShangHanLun', safe='')}/{quote('Chapter1', safe='')}/{quote('Verse2', safe='')}"
        self.assertEqual(uri, expected_uri)

    def test_mint_source_uri_special_chars(self):
        # 测试包含特殊字符的来源 URI 生成
        # Test source URI generation with special characters
        uri = self.mint_source_uri("古籍", "本草纲目 (Compendium)", "卷一", "序 例/Section A")
        # "本草纲目 (Compendium)" 和 "序 例" 中的空格和括号会被编码
        # Spaces and parentheses in "本草纲目 (Compendium)" and "序 例" will be encoded
        # "序 例/Section A" 中的 / 也会被编码
        # The / in "序 例/Section A" will also be encoded
        expected_uri = f"{mock_settings_uri.SOURCE_BASE_URI}{quote('古籍', safe='')}/{quote('本草纲目 (Compendium)', safe='')}/{quote('卷一', safe='')}/{quote('序 例/Section A', safe='')}"
        self.assertEqual(uri, expected_uri)
        self.assertIn(quote(" ", safe=''), uri) # 检查空格是否被编码
                                  # Check if space is encoded
        self.assertIn(quote("(", safe=''), uri) # 检查左括号是否被编码
                                   # Check if left parenthesis is encoded
        self.assertIn(quote(")", safe=''), uri) # 检查右括号是否被编码
                                   # Check if right parenthesis is encoded
        self.assertIn(quote("/", safe=''), uri) # 检查斜杠是否被编码
                                   # Check if the slash is encoded


    def test_mint_source_uri_with_args(self):
        # 测试带附加参数的来源 URI 生成
        # Test source URI generation with additional arguments
        uri = self.mint_source_uri("Journal", "TCMResearch", "Vol10", "Article5", "Page100", "Fig2")
        expected_uri = f"{mock_settings_uri.SOURCE_BASE_URI}{quote('Journal', safe='')}/{quote('TCMResearch', safe='')}/{quote('Vol10', safe='')}/{quote('Article5', safe='')}/{quote('Page100', safe='')}/{quote('Fig2', safe='')}"
        self.assertEqual(uri, expected_uri)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
