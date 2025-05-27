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
    _expand_curie, 
    prepare_entity_sparql_insert,
    COMMON_DATATYPES 
)
from tcm_kg_virtuoso_module.config import settings


# 使用真实的 settings.DEFAULT_PREFIXES 来构建测试中使用的 mock_DEFAULT_PREFIXES
# Use real settings.DEFAULT_PREFIXES to build mock_DEFAULT_PREFIXES used in tests
# 这样可以确保测试与实际配置的结构一致，同时允许在测试中覆盖（如果需要）
# This ensures test consistency with actual config structure, while allowing overrides if needed.
mock_DEFAULT_PREFIXES_for_test = settings.DEFAULT_PREFIXES.copy()


@patch('tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES', mock_DEFAULT_PREFIXES_for_test)
class TestDataFormatter(unittest.TestCase):

    def test_format_uri(self):
        # 测试 URI 格式化
        self.assertEqual(format_uri("http://example.com/res"), "<http://example.com/res>")
        self.assertEqual(format_uri("<http://example.com/res2>"), "<http://example.com/res2>") # 已有括号
        self.assertEqual(format_uri(123), "<123>") # 数字输入，应转换为字符串并加括号
        self.assertEqual(format_uri(""), "<>") # 空字符串

    def test_escape_literal_value(self):
        # 测试字面量值的转义
        self.assertEqual(escape_literal_value("simple"), "simple")
        self.assertEqual(escape_literal_value('with "quotes"'), 'with \\"quotes\\"') # 双引号转义
        self.assertEqual(escape_literal_value("with \\backslash"), "with \\\\backslash") # 反斜杠转义
        self.assertEqual(escape_literal_value("new\nline"), "new\\nline") # 换行符转义
        self.assertEqual(escape_literal_value("carriage\rreturn"), "carriage\\rreturn") # 回车符转义
        self.assertEqual(escape_literal_value("tab\tchar"), "tab\\tchar") # 制表符转义
        self.assertEqual(escape_literal_value('all: \\\"\n\r\t'), 'all: \\\\\\\"\\n\\r\\t') # 混合转义
        self.assertEqual(escape_literal_value(123), "123") # 数字也应字符串化

    def test_format_literal_plain(self):
        # 测试普通字面量 (无数据类型，无语言标签)
        self.assertEqual(format_literal("hello"), '"hello"')
        self.assertEqual(format_literal(123.45), '"123.45"') # 数字输入
        self.assertEqual(format_literal(True), '"True"')     # 布尔输入

    def test_format_literal_with_known_datatype(self):
        # 测试带已知数据类型的字面量 (从 COMMON_DATATYPES)
        # COMMON_DATATYPES 自身在 data_formatter.py 中定义时会使用其模块内的 DEFAULT_PREFIXES
        # 因此这里的测试会隐式使用上面 @patch 的 mock_DEFAULT_PREFIXES_for_test
        expected_int_dt = mock_DEFAULT_PREFIXES_for_test['xsd'] + "integer"
        self.assertEqual(format_literal(42, datatype="integer"), f'"42"^^<{expected_int_dt}>')
        
        expected_bool_dt = mock_DEFAULT_PREFIXES_for_test['xsd'] + "boolean"
        self.assertEqual(format_literal(True, datatype="boolean"), f'"True"^^<{expected_bool_dt}>')

        expected_str_dt = mock_DEFAULT_PREFIXES_for_test['xsd'] + "string"
        self.assertEqual(format_literal("text", datatype="string"), f'"text"^^<{expected_str_dt}>')

    def test_format_literal_with_full_uri_datatype(self):
        # 测试带完整 URI 作为数据类型的字面量
        dt_uri = "http://mycustom.com/datatype#specialString"
        self.assertEqual(format_literal("special", datatype=dt_uri), f'"special"^^<{dt_uri}>')

    @patch('builtins.print') 
    def test_format_literal_with_unknown_short_datatype(self, mock_print):
        # 测试使用未在 COMMON_DATATYPES 中定义的短格式数据类型
        self.assertEqual(format_literal("unknown type", datatype="nonExistentType"), '"unknown type"')
        mock_print.assert_any_call("警告：数据类型 'nonExistentType' 未被识别。将省略数据类型。") # 假设这是 data_formatter.py 中的实际警告

    def test_format_literal_with_lang_tag(self):
        # 测试带语言标签的字面量
        self.assertEqual(format_literal("你好", lang="zh"), '"你好"@zh')
        self.assertEqual(format_literal("Hello", lang="en-US"), '"Hello"@en-US')

    @patch('builtins.print')
    def test_format_literal_invalid_lang_tag(self, mock_print):
        # 测试无效的语言标签 (例如空字符串)
        # 假设 data_formatter.py 中的 format_literal 会对无效 lang 标签进行处理或警告
        self.assertEqual(format_literal("text", lang=""), '"text"') # 假设空 lang 标签被忽略
        mock_print.assert_any_call("警告：语言标签 '' 无效。将省略语言标签。") # 假设的警告信息

    def test_format_literal_datatype_preferred_over_lang(self):
        # 测试同时提供数据类型和语言标签时，数据类型优先
        expected_str_dt = mock_DEFAULT_PREFIXES_for_test['xsd'] + "string"
        self.assertEqual(format_literal("text", datatype="string", lang="en"), f'"text"^^<{expected_str_dt}>')

    def test_format_literal_with_escaping(self):
        # 测试值中包含需要转义的字符的字面量格式化
        val_to_escape = 'text with "quotes" and \\ backslash, also \n newline.' # 注意原始字符串中反斜杠的表示
        escaped_val = 'text with \\"quotes\\" and \\\\ backslash, also \\n newline.'
        self.assertEqual(format_literal(val_to_escape), f'"{escaped_val}"')

    def test_create_rdf_triple_all_uris(self):
        # 测试所有部分都是 URI 的RDF三元组创建
        s, p, o = "http://example.com/s", "http://example.com/p", "http://example.com/o"
        self.assertEqual(create_rdf_triple(s, p, o), f"<{s}> <{p}> <{o}> .")

    def test_create_rdf_triple_with_literal_object(self):
        # 测试宾语是字面量的RDF三元组创建
        s, p = "http://example.com/s", "http://example.com/p"
        obj_plain_literal_val = "A simple literal"
        formatted_obj_plain = format_literal(obj_plain_literal_val) 
        self.assertEqual(create_rdf_triple(s, p, formatted_obj_plain, is_object_literal=True),
                         f"<{s}> <{p}> {formatted_obj_plain} .")

    def test_expand_curie(self):
        # 测试 _expand_curie 辅助函数
        self.assertEqual(_expand_curie("tcm-onto:hasTaste", mock_DEFAULT_PREFIXES_for_test),
                         mock_DEFAULT_PREFIXES_for_test['tcm-onto'] + "hasTaste")
        self.assertEqual(_expand_curie("rdf:type", mock_DEFAULT_PREFIXES_for_test),
                         mock_DEFAULT_PREFIXES_for_test['rdf'] + "type")
        full_uri = "http://example.org/fullURI"
        self.assertEqual(_expand_curie(full_uri, mock_DEFAULT_PREFIXES_for_test), full_uri)
        with patch('builtins.print') as mock_print: # _expand_curie 内部有 print 警告
            self.assertEqual(_expand_curie("unknown:property", mock_DEFAULT_PREFIXES_for_test), "unknown:property")
            mock_print.assert_any_call("警告：CURIE前缀 'unknown' 在提供的映射中未找到。CURIE: 'unknown:property'")
        with patch('builtins.print') as mock_print:
             self.assertEqual(_expand_curie("justAString", mock_DEFAULT_PREFIXES_for_test), "justAString")
             mock_print.assert_any_call("警告：输入值 'justAString' 不是有效的CURIE且不是可识别的完整URI。")


    # --- 新增的 prepare_entity_sparql_insert 测试 ---
    @patch('tcm_kg_virtuoso_module.core.data_formatter.create_source_metadata')
    @patch('tcm_kg_virtuoso_module.core.data_formatter.mint_entity_uri')
    def test_prepare_entity_sparql_insert_basic(self, mock_mint_entity_uri, mock_create_source_metadata):
        # 测试基本的实体 SPARQL INSERT 查询生成

        # 1. 配置 Mocks 的返回值
        mock_entity_uri_val = "http://tcm.example.org/entity/GeneratedEntity/Herb_Ginseng_123"
        mock_mint_entity_uri.return_value = mock_entity_uri_val

        mock_source_graph_uri_val = "http://tcm.example.org/source_graph/SourceDoc_ShangHanLun_CH1_P1"
        mock_source_triples_val = [
            "<http://tcm.example.org/source/SHL_CH1_P1> <http://purl.org/dc/terms/bibliographicCitation> \"ShangHanLun Chapter 1 Paragraph 1\" .",
            "<http://tcm.example.org/source/SHL_CH1_P1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://tcm.example.org/ontology/SourceContext> ."
        ]
        mock_create_source_metadata.return_value = (mock_source_graph_uri_val, mock_source_triples_val)

        # 2. 准备输入参数
        entity_type_name_input = "Herb" 
        entity_label_input = "人参" 
        entity_properties_input = {
            "tcm-onto:hasTaste": "甘", 
            "rdfs:seeAlso": "http://dbpedia.org/resource/Ginseng", 
            "tcm-onto:hasDescription": "一种珍贵的草药。"
        }
        source_details_input = { 
            "citation": "《伤寒论》第一章第一段", "original_text": "太阳之为病，脉浮，头项强痛而恶寒。",
            "document_identifier": "ShangHanLun", "source_type": "经典著作",
            "source_section": "第一章", "source_subsection": "第一段"
        }
        entity_id_args_input = ["Ginseng", "123"] 

        # 3. 调用被测试的函数
        sparql_query = prepare_entity_sparql_insert(
            entity_type_name_input, entity_label_input, entity_properties_input,
            source_details_input, entity_id_args_input
        )
        
        # 4. 验证 SPARQL 查询字符串
        self.assertTrue(sparql_query.startswith("INSERT DATA {"), "查询应以 INSERT DATA { 开始")
        self.assertTrue(sparql_query.strip().endswith("}"), "查询应以 } 结束") # strip() to handle potential trailing newlines by worker
        self.assertIn(f"GRAPH <{mock_source_graph_uri_val}> {{", sparql_query, "缺少 GRAPH 子句")

        # 构造预期的实体三元组 (使用 _expand_curie, format_uri, format_literal 确保与实现一致)
        formatted_entity_uri = format_uri(mock_entity_uri_val)
        
        rdf_type_predicate = format_uri(_expand_curie("rdf:type", mock_DEFAULT_PREFIXES_for_test))
        expected_entity_class_uri = _expand_curie(f"tcm-onto:{entity_type_name_input}", mock_DEFAULT_PREFIXES_for_test)
        formatted_entity_class_uri = format_uri(expected_entity_class_uri)
        expected_type_triple = f"{formatted_entity_uri} {rdf_type_predicate} {formatted_entity_class_uri} ."
        
        rdfs_label_predicate = format_uri(_expand_curie("rdfs:label", mock_DEFAULT_PREFIXES_for_test))
        formatted_label_literal = format_literal(entity_label_input, datatype="string")
        expected_label_triple = f"{formatted_entity_uri} {rdfs_label_predicate} {formatted_label_literal} ."

        taste_predicate = format_uri(_expand_curie("tcm-onto:hasTaste", mock_DEFAULT_PREFIXES_for_test))
        taste_literal = format_literal("甘", datatype="string")
        expected_taste_triple = f"{formatted_entity_uri} {taste_predicate} {taste_literal} ."
        
        see_also_predicate = format_uri(_expand_curie("rdfs:seeAlso", mock_DEFAULT_PREFIXES_for_test))
        see_also_object_uri = format_uri("http://dbpedia.org/resource/Ginseng")
        expected_see_also_triple = f"{formatted_entity_uri} {see_also_predicate} {see_also_object_uri} ."

        desc_predicate = format_uri(_expand_curie("tcm-onto:hasDescription", mock_DEFAULT_PREFIXES_for_test))
        desc_literal = format_literal("一种珍贵的草药。", datatype="string")
        expected_desc_triple = f"{formatted_entity_uri} {desc_predicate} {desc_literal} ."

        # 提取 GRAPH 块内容进行断言
        graph_block_start_idx = sparql_query.find(f"GRAPH <{mock_source_graph_uri_val}> {{") + len(f"GRAPH <{mock_source_graph_uri_val}> {{")
        # 假设实体图是第一个 GRAPH 块，其后紧跟源数据三元组
        # This assumes source triples are outside and after the first GRAPH block.
        # A more robust way might be needed if query structure is more complex.
        # For now, find the closing '}' of this specific graph block.
        # Find the balanced '}' for this graph block.
        balance = 1
        graph_block_end_idx = -1
        for i in range(graph_block_start_idx, len(sparql_query)):
            if sparql_query[i] == '{':
                balance += 1
            elif sparql_query[i] == '}':
                balance -= 1
                if balance == 0:
                    graph_block_end_idx = i
                    break
        
        self.assertTrue(graph_block_end_idx != -1, "Could not find closing '}' for entity GRAPH block")
        entity_graph_content = sparql_query[graph_block_start_idx:graph_block_end_idx].strip()

        self.assertIn(expected_type_triple.strip(), entity_graph_content)
        self.assertIn(expected_label_triple.strip(), entity_graph_content)
        self.assertIn(expected_taste_triple.strip(), entity_graph_content)
        self.assertIn(expected_see_also_triple.strip(), entity_graph_content)
        self.assertIn(expected_desc_triple.strip(), entity_graph_content)

        # 检查源数据三元组是否在默认图中
        source_triples_joined = "\n".join(mock_source_triples_val)
        self.assertIn(source_triples_joined, sparql_query)
        # 确保源三元组不在实体 GRAPH 块内
        for mock_src_triple in mock_source_triples_val:
             self.assertNotIn(mock_src_triple.strip(), entity_graph_content)
            
        # 5. 确保 mock 被正确调用
        # mint_entity_uri is called with (class_uri, label, *args)
        # class_uri itself is expanded from "tcm-onto:" + entity_type_name_input
        mock_mint_entity_uri.assert_called_once_with(
            expected_entity_class_uri, # First arg to mint_entity_uri is class_uri
            entity_label_input, 
            *entity_id_args_input
        )
        mock_create_source_metadata.assert_called_once_with(**source_details_input)

    @patch('tcm_kg_virtuoso_module.core.data_formatter.create_source_metadata')
    @patch('tcm_kg_virtuoso_module.core.data_formatter.mint_entity_uri')
    def test_prepare_entity_sparql_insert_no_properties_no_id_args(self, mock_mint_entity_uri, mock_create_source_metadata):
        # 测试无实体属性、无附加ID参数的情况

        mock_entity_uri_val = "http://tcm.example.org/entity/GeneratedEntity/Syndrome_Cold"
        mock_mint_entity_uri.return_value = mock_entity_uri_val

        mock_source_graph_uri_val = "http://tcm.example.org/source_graph/Source_ClinicalGuideline_V1"
        mock_source_triples_val = ["<http://example.com/source/s1> <http://example.com/p1> <http://example.com/o1> ."]
        mock_create_source_metadata.return_value = (mock_source_graph_uri_val, mock_source_triples_val)

        entity_type_name_input = "Syndrome" 
        entity_label_input = "风寒束表证"  
        entity_properties_input = {} 
        source_details_input = {"citation": "CG V1", "original_text": "text", "document_identifier": "CGV1", 
                                "source_type": "Guideline", "source_section": "S2", "source_subsection": "I3"}
        
        sparql_query = prepare_entity_sparql_insert(
            entity_type_name_input, entity_label_input, entity_properties_input,
            source_details_input # entity_id_args is None (default)
        )

        self.assertTrue(sparql_query.startswith("INSERT DATA {"))
        self.assertIn(f"GRAPH <{mock_source_graph_uri_val}> {{", sparql_query)

        formatted_entity_uri = format_uri(mock_entity_uri_val)
        rdf_type_predicate = format_uri(_expand_curie("rdf:type", mock_DEFAULT_PREFIXES_for_test))
        expected_entity_class_uri = _expand_curie(f"tcm-onto:{entity_type_name_input}", mock_DEFAULT_PREFIXES_for_test)
        formatted_entity_class_uri = format_uri(expected_entity_class_uri)
        expected_type_triple = f"{formatted_entity_uri} {rdf_type_predicate} {formatted_entity_class_uri} ."
        
        rdfs_label_predicate = format_uri(_expand_curie("rdfs:label", mock_DEFAULT_PREFIXES_for_test))
        formatted_label_literal = format_literal(entity_label_input, datatype="string")
        expected_label_triple = f"{formatted_entity_uri} {rdfs_label_predicate} {formatted_label_literal} ."
        
        graph_block_start_idx = sparql_query.find(f"GRAPH <{mock_source_graph_uri_val}> {{") + len(f"GRAPH <{mock_source_graph_uri_val}> {{")
        balance = 1
        graph_block_end_idx = -1
        for i in range(graph_block_start_idx, len(sparql_query)):
            if sparql_query[i] == '{': balance += 1
            elif sparql_query[i] == '}':
                balance -= 1
                if balance == 0: graph_block_end_idx = i; break
        entity_graph_content = sparql_query[graph_block_start_idx:graph_block_end_idx].strip()

        self.assertIn(expected_type_triple.strip(), entity_graph_content)
        self.assertIn(expected_label_triple.strip(), entity_graph_content)
        
        self.assertEqual(entity_graph_content.count(" ."), 2, "实体图中应恰好有两条三元组。")

        source_triples_joined = "\n".join(mock_source_triples_val)
        self.assertIn(source_triples_joined, sparql_query)
        for mock_src_triple in mock_source_triples_val:
             self.assertNotIn(mock_src_triple.strip(), entity_graph_content)
            
        mock_mint_entity_uri.assert_called_once_with(
            expected_entity_class_uri, 
            entity_label_input
            # No *entity_id_args passed as it's None/empty
        )
        mock_create_source_metadata.assert_called_once_with(**source_details_input)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
