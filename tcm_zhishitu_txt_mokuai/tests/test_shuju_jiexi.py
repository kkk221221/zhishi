import unittest
import sys
import os
import json

# 为确保能正确导入模块，将项目根目录添加到sys.path
# 这通常在运行测试脚本时需要，特别是当测试位于子目录时
# 获取当前测试文件所在的目录 (tcm_zhishitu_txt_mokuai/tests)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (tcm_zhishitu_txt_mokuai)
project_root = os.path.dirname(current_dir)
# 将项目根目录的父目录 (即包含 tcm_zhishitu_txt_mokuai 的目录) 添加到 sys.path
# 这样就可以使用 from tcm_zhishitu_txt_mokuai.hexin... 来导入
sys.path.insert(0, os.path.dirname(project_root))

from tcm_zhishitu_txt_mokuai.hexin.shuju_jiexi import parse_entity_line, format_entity_for_txt

class TestDataParsing(unittest.TestCase):
    """测试数据解析模块 (shuju_jiexi.py) 中的函数"""

    # --- 测试 parse_entity_line ---
    def test_parse_valid_json_line(self):
        """测试解析有效的JSONL字符串"""
        line = '{"id": "YC001", "name": "人参", "功效": ["补气", "健脾"]}'
        expected = {"id": "YC001", "name": "人参", "功效": ["补气", "健脾"]}
        self.assertEqual(parse_entity_line(line), expected)

    def test_parse_invalid_json_line(self):
        """测试解析无效的JSONL字符串 (例如，属性名没有引号)"""
        line = '{id: "YC002", "name": "枸杞"}' # 'id' 应该被引号包围
        self.assertIsNone(parse_entity_line(line), "无效的JSON字符串应返回None")

    def test_parse_empty_line(self):
        """测试解析空字符串"""
        line = ""
        self.assertIsNone(parse_entity_line(line), "空字符串应返回None")

    def test_parse_whitespace_line(self):
        """测试解析只包含空白字符的字符串"""
        line = "   \t  \n  "
        self.assertIsNone(parse_entity_line(line), "只包含空白字符的字符串应返回None")

    def test_parse_line_with_chinese_chars(self):
        """测试解析包含中文字符的有效JSONL字符串"""
        line = '{"id": "ZZ001", "名称": "头痛", "描述": "头部疼痛的感觉"}'
        expected = {"id": "ZZ001", "名称": "头痛", "描述": "头部疼痛的感觉"}
        self.assertEqual(parse_entity_line(line), expected)

    def test_parse_line_with_various_data_types(self):
        """测试解析包含不同数据类型的有效JSONL字符串"""
        line = '{"id": "FJ001", "name": "方剂一号", "herb_ids": ["YC001", "YC002"], "dosage_grams": 15.5, "is_common": true, "notes": null}'
        expected = {"id": "FJ001", "name": "方剂一号", "herb_ids": ["YC001", "YC002"], "dosage_grams": 15.5, "is_common": True, "notes": None}
        self.assertEqual(parse_entity_line(line), expected)

    # --- 测试 format_entity_for_txt ---
    def test_format_valid_dict(self):
        """测试格式化有效的Python字典"""
        obj = {"id": "YC001", "name": "人参", "功效": ["补气", "健脾"]}
        # 注意: json.dumps 默认会在逗号和冒号后添加空格。
        # 如果原始函数实现不添加空格，则此预期结果需要调整。
        # 假设原始函数 format_entity_for_txt 使用 json.dumps(obj, ensure_ascii=False)
        # 并且没有指定 separators，那么默认会有空格。
        # 若指定 separators=(',', ':') 则无空格。
        # 此处假设默认行为，即有空格。
        # 更新：根据 format_entity_for_txt 的实现 (json.dumps(obj, ensure_ascii=False))，
        # 默认情况下，键值对之间的逗号后会有空格，冒号后也会有空格。
        # 然而，为了与parse_entity_line的输出（通常无额外空格）和文件存储的简洁性保持一致，
        # 更常见的做法是生成无不必要空格的JSON。
        # 如果 format_entity_for_txt 的目标是生成最紧凑的JSON，则expected应无空格。
        # 但如果 format_entity_for_txt 使用默认的 json.dumps，则应有空格。
        # 假设目标是标准的、可读性较好的JSON输出（带空格）。
        # 经过对json.dumps的测试, ensure_ascii=False时, 默认的separators是(', ', ': ')
        expected = '{"id": "YC001", "name": "人参", "功效": ["补气", "健脾"]}'
        # 为了使测试更健壮，我们先解析预期的字符串，再解析实际生成的字符串，然后比较字典。
        # 这样可以忽略由于json库版本或默认格式化选项导致的微小空格差异。
        self.assertEqual(json.loads(format_entity_for_txt(obj)), json.loads(expected))


    def test_format_dict_with_chinese_chars(self):
        """测试格式化包含中文字符的Python字典"""
        obj = {"id": "ZZ001", "名称": "头痛", "描述": "头部疼痛的感觉"}
        expected_json_str = '{"id": "ZZ001", "名称": "头痛", "描述": "头部疼痛的感觉"}'
        
        formatted_str = format_entity_for_txt(obj)
        self.assertIsNotNone(formatted_str)
        # 检查中文字符是否原样保留 (没有被转义成 \uXXXX)
        self.assertNotIn("\\u", formatted_str)
        self.assertEqual(json.loads(formatted_str), json.loads(expected_json_str))


    def test_format_empty_dict(self):
        """测试格式化空字典"""
        obj = {}
        expected = "{}"
        self.assertEqual(format_entity_for_txt(obj), expected)

    def test_format_dict_with_various_data_types(self):
        """测试格式化包含不同数据类型的Python字典"""
        obj = {"id": "FJ001", "name": "方剂一号", "herb_ids": ["YC001", "YC002"], "dosage_grams": 15.5, "is_common": True, "notes": None}
        # Python的True/False会转为json的true/false, None会转为null
        expected_str = '{"id": "FJ001", "name": "方剂一号", "herb_ids": ["YC001", "YC002"], "dosage_grams": 15.5, "is_common": true, "notes": null}'
        self.assertEqual(json.loads(format_entity_for_txt(obj)), json.loads(expected_str))


if __name__ == '__main__':
    unittest.main()
