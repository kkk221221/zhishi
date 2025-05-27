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
    _expand_curie, # _expand_curie 也是在 data_formatter.py 中定义的，测试它有助于验证内部逻辑
                   # _expand_curie is also defined in data_formatter.py, testing it helps validate internal logic
    prepare_entity_sparql_insert, # 要测试的主要函数
                                  # Main function to test
    COMMON_DATATYPES 
)
from tcm_kg_virtuoso_module.config import settings # 用于访问 DEFAULT_PREFIXES 以获取预期值
                                                 # Used to access DEFAULT_PREFIXES for expected values

# 模拟 settings 模块，因为 data_formatter.py 中的 DEFAULT_PREFIXES 间接依赖于 settings
# Mock the settings module, as DEFAULT_PREFIXES in data_formatter.py indirectly depends on settings
mock_settings_for_formatter = MagicMock()
mock_settings_for_formatter.DEFAULT_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#", 
    "dcterms": "http://purl.org/dc/terms/",
    "tcm-entity": settings.ENTITY_BASE_URI, # 使用真实的 settings 值来确保一致性
                                          # Use real settings values to ensure consistency
    "tcm-onto": settings.ONTOLOGY_BASE_URI,   
    "tcm-source": settings.SOURCE_BASE_URI, 
}


# DEFAULT_PREFIXES 是在 tcm_kg_virtuoso_module.core.data_formatter 模块的顶层定义的，
# 并且是从 tcm_kg_virtuoso_module.config.settings 导入的。
# 因此，当测试 data_formatter.py 中的函数时，如果这些函数使用了 DEFAULT_PREFIXES，
# 我们需要确保它们使用的是我们测试中可控的 DEFAULT_PREFIXES 版本。
# @patch 的目标应该是 'tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES'
# The target for @patch should be 'tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES'
@patch('tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES', mock_settings_for_formatter.DEFAULT_PREFIXES)
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
        self.assertEqual(escape_literal_value('with "quotes"'), 'with \\"quotes\\"')
        self.assertEqual(escape_literal_value("with \\backslash"), "with \\\\backslash")
        self.assertEqual(escape_literal_value("new\nline"), "new\\nline")
        self.assertEqual(escape_literal_value("carriage\rreturn"), "carriage\\rreturn")
        self.assertEqual(escape_literal_value("tab\tchar"), "tab\\tchar")
        self.assertEqual(escape_literal_value('all: \\"\n\r\t'), 'all: \\\\\\\"\\n\\r\\t') # 混合
        self.assertEqual(escape_literal_value(123), "123") # 数字也应字符串化

    def test_format_literal_plain(self):
        # 测试普通字面量 (无数据类型，无语言标签)
        self.assertEqual(format_literal("hello"), '"hello"')
        self.assertEqual(format_literal(123.45), '"123.45"') # 数字输入
        self.assertEqual(format_literal(True), '"True"')     # 布尔输入

    def test_format_literal_with_known_datatype(self):
        # 测试带已知数据类型的字面量 (从 COMMON_DATATYPES)
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

    @patch('builtins.print') 
    def test_format_literal_with_unknown_short_datatype(self, mock_print):
        # 测试使用未在 COMMON_DATATYPES 中定义的短格式数据类型
        self.assertEqual(format_literal("unknown type", datatype="nonExistentType"), '"unknown type"')
        mock_print.assert_any_call("警告：数据类型 'nonExistentType' 未被识别。将省略数据类型。")

    def test_format_literal_with_lang_tag(self):
        # 测试带语言标签的字面量
        self.assertEqual(format_literal("你好", lang="zh"), '"你好"@zh')
        self.assertEqual(format_literal("Hello", lang="en-US"), '"Hello"@en-US')
        self.assertEqual(format_literal(123, lang="num"), '"123"@num') 

    @patch('builtins.print')
    def test_format_literal_invalid_lang_tag(self, mock_print):
        # 测试无效的语言标签
        self.assertEqual(format_literal("text", lang=""), '"text"') 
        mock_print.assert_any_call("警告：语言标签 '' 无效。将省略语言标签。")
        mock_print.reset_mock()
        self.assertEqual(format_literal("text", lang=None), '"text"') 
        mock_print.assert_not_called() 

    def test_format_literal_datatype_preferred_over_lang(self):
        # 测试同时提供数据类型和语言标签时，数据类型优先
        expected_str_dt = mock_settings_for_formatter.DEFAULT_PREFIXES['xsd'] + "string"
        self.assertEqual(format_literal("text", datatype="string", lang="en"), f'"text"^^<{expected_str_dt}>')

    def test_format_literal_with_escaping(self):
        # 测试值中包含需要转义的字符的字面量格式化
        val_to_escape = 'text with "quotes" and \ backslash, also \n newline.'
        escaped_val = 'text with \\"quotes\\" and \\\\ backslash, also \\n newline.'
        self.assertEqual(format_literal(val_to_escape), f'"{escaped_val}"')
        expected_str_dt = mock_settings_for_formatter.DEFAULT_PREFIXES['xsd'] + "string"
        self.assertEqual(format_literal(val_to_escape, datatype="string"), f'"{escaped_val}"^^<{expected_str_dt}>')
        self.assertEqual(format_literal(val_to_escape, lang="en"), f'"{escaped_val}"@en')

    def test_create_rdf_triple_all_uris(self):
        # 测试所有部分都是 URI 的RDF三元组创建
        s, p, o = "http://example.com/s", "http://example.com/p", "http://example.com/o"
        self.assertEqual(create_rdf_triple(s, p, o), f"<{s}> <{p}> <{o}> .")
        s_br = "<http://example.com/s_br>"
        p_br = "http://example.com/p_br" 
        o_br = "<http://example.com/o_br>"
        self.assertEqual(create_rdf_triple(s_br, p_br, o_br), f"{s_br} <{p_br}> {o_br} .")

    def test_create_rdf_triple_with_literal_object(self):
        # 测试宾语是字面量的RDF三元组创建
        s, p = "http://example.com/s", "http://example.com/p"
        obj_plain_literal_val = "A simple literal"
        formatted_obj_plain = format_literal(obj_plain_literal_val) 
        self.assertEqual(create_rdf_triple(s, p, formatted_obj_plain, is_object_literal=True),
                         f"<{s}> <{p}> {formatted_obj_plain} .")
        obj_typed_literal_val = 100
        expected_int_dt = mock_settings_for_formatter.DEFAULT_PREFIXES['xsd'] + "integer"
        formatted_obj_typed = format_literal(obj_typed_literal_val, datatype="integer")
        self.assertEqual(create_rdf_triple(s, p, formatted_obj_typed, is_object_literal=True),
                         f"<{s}> <{p}> {formatted_obj_typed} .")
        obj_lang_literal_val = "你好"
        formatted_obj_lang = format_literal(obj_lang_literal_val, lang="zh-CN")
        self.assertEqual(create_rdf_triple(s, p, formatted_obj_lang, is_object_literal=True),
                         f"<{s}> <{p}> {formatted_obj_lang} .")

    def test_create_rdf_triple_object_is_uri_mistakenly_not_literal(self):
        # 测试当对象是URI，但错误地未将 is_object_literal 设置为 False
        s, p, o_uri = "http://s.com", "http://p.com", "http://o.com/uri"
        self.assertEqual(create_rdf_triple(s, p, o_uri), f"<{s}> <{p}> <{o_uri}> .")
        self.assertEqual(create_rdf_triple(s, p, f"<{o_uri}>"), f"<{s}> <{p}> <{o_uri}> .")

    def test_expand_curie(self):
        # 测试 _expand_curie 辅助函数
        # Test the _expand_curie helper function
        self.assertEqual(_expand_curie("tcm-onto:hasTaste", mock_settings_for_formatter.DEFAULT_PREFIXES),
                         mock_settings_for_formatter.DEFAULT_PREFIXES['tcm-onto'] + "hasTaste")
        self.assertEqual(_expand_curie("rdf:type", mock_settings_for_formatter.DEFAULT_PREFIXES),
                         mock_settings_for_formatter.DEFAULT_PREFIXES['rdf'] + "type")
        # 测试完整 URI (应原样返回)
        # Test full URI (should return as is)
        full_uri = "http://example.org/fullURI"
        self.assertEqual(_expand_curie(full_uri, mock_settings_for_formatter.DEFAULT_PREFIXES), full_uri)
        # 测试未知前缀 (应原样返回并打印警告 - 需要 mock print 来验证警告)
        # Test unknown prefix (should return as is and print a warning - requires mock print to verify warning)
        with patch('builtins.print') as mock_print:
            self.assertEqual(_expand_curie("unknown:property", mock_settings_for_formatter.DEFAULT_PREFIXES), "unknown:property")
            mock_print.assert_called_with("警告：CURIE前缀 'unknown' 在提供的映射中未找到。CURIE: 'unknown:property'")
        # 测试非CURIE非完整URI (应原样返回并打印警告)
        # Test non-CURIE non-full URI (should return as is and print a warning)
        with patch('builtins.print') as mock_print:
             self.assertEqual(_expand_curie("justAString", mock_settings_for_formatter.DEFAULT_PREFIXES), "justAString")
             mock_print.assert_called_with("警告：输入值 'justAString' 不是有效的CURIE且不是可识别的完整URI。")


    # --- 新增的 prepare_entity_sparql_insert 测试 ---
    # --- New tests for prepare_entity_sparql_insert ---
    @patch('tcm_kg_virtuoso_module.core.data_formatter.create_source_metadata')
    @patch('tcm_kg_virtuoso_module.core.data_formatter.mint_entity_uri')
    def test_prepare_entity_sparql_insert_basic(self, mock_mint_entity_uri, mock_create_source_metadata):
        # 测试基本的实体 SPARQL INSERT 查询生成
        # Test basic entity SPARQL INSERT query generation

        # 1. 配置 Mocks 的返回值
        # 1. Configure mock return values
        mock_entity_uri_val = "http://tcm.example.org/entity/GeneratedEntity/Herb_Ginseng_123"
        mock_mint_entity_uri.return_value = mock_entity_uri_val

        mock_source_graph_uri_val = "http://tcm.example.org/source_graph/SourceDoc_ShangHanLun_CH1_P1"
        mock_source_triples_val = [
            "<http://tcm.example.org/source/SHL_CH1_P1> <http://purl.org/dc/terms/bibliographicCitation> \"ShangHanLun Chapter 1 Paragraph 1\" .",
            "<http://tcm.example.org/source/SHL_CH1_P1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://tcm.example.org/ontology/SourceContext> ."
        ]
        mock_create_source_metadata.return_value = (mock_source_graph_uri_val, mock_source_triples_val)

        # 2. 准备输入参数
        # 2. Prepare input parameters
        entity_type_name_input = "Herb" 
        entity_label_input = "人参" # Ginseng
        entity_properties_input = {
            "tcm-onto:hasTaste": "甘", # Sweet, Literal property
            "rdfs:seeAlso": "http://dbpedia.org/resource/Ginseng", # URI property
            "tcm-onto:hasDescription": "一种珍贵的草药。" # A precious herb. Literal property
        }
        source_details_input = { 
            "citation": "《伤寒论》第一章第一段", "original_text": "太阳之为病，脉浮，头项强痛而恶寒。",
            "document_identifier": "ShangHanLun", "source_type": "经典著作",
            "source_section": "第一章", "source_subsection": "第一段"
        }
        entity_id_args_input = ["Ginseng", "123"] # 对应 mock_entity_uri_val 中的部分
                                                # Corresponds to parts of mock_entity_uri_val

        # 3. 调用被测试的函数
        # 3. Call the function under test
        sparql_query = prepare_entity_sparql_insert(
            entity_type_name_input, entity_label_input, entity_properties_input,
            source_details_input, entity_id_args_input
        )
        
        # 4. 验证 SPARQL 查询字符串
        # 4. Verify the SPARQL query string

        # 检查整体结构
        # Check overall structure
        self.assertTrue(sparql_query.startswith("INSERT DATA {"), "查询应以 INSERT DATA { 开始")
        self.assertTrue(sparql_query.endswith("}"), "查询应以 } 结束")
        self.assertIn(f"GRAPH <{mock_source_graph_uri_val}> {{", sparql_query, "缺少 GRAPH 子句")

        # 构造预期的实体三元组
        # Construct expected entity triples
        #   实体URI (已 mock)
        #   Entity URI (mocked)
        formatted_entity_uri = format_uri(mock_entity_uri_val)
        
        #   类型三元组: <entity_uri> rdf:type <tcm-onto:Herb> .
        #   Type triple: <entity_uri> rdf:type <tcm-onto:Herb> .
        rdf_type_predicate = format_uri(_expand_curie("rdf:type", mock_settings_for_formatter.DEFAULT_PREFIXES))
        expected_entity_class_uri = _expand_curie(f"tcm-onto:{entity_type_name_input}", mock_settings_for_formatter.DEFAULT_PREFIXES)
        formatted_entity_class_uri = format_uri(expected_entity_class_uri)
        expected_type_triple = f"{formatted_entity_uri} {rdf_type_predicate} {formatted_entity_class_uri} ."
        
        #   标签三元组: <entity_uri> rdfs:label "人参"^^xsd:string .
        #   Label triple: <entity_uri> rdfs:label "人参"^^xsd:string .
        rdfs_label_predicate = format_uri(_expand_curie("rdfs:label", mock_settings_for_formatter.DEFAULT_PREFIXES))
        formatted_label_literal = format_literal(entity_label_input, datatype="string")
        expected_label_triple = f"{formatted_entity_uri} {rdfs_label_predicate} {formatted_label_literal} ."

        #   属性三元组
        #   Property triples
        #   tcm-onto:hasTaste "甘"
        taste_predicate = format_uri(_expand_curie("tcm-onto:hasTaste", mock_settings_for_formatter.DEFAULT_PREFIXES))
        taste_literal = format_literal("甘", datatype="string")
        expected_taste_triple = f"{formatted_entity_uri} {taste_predicate} {taste_literal} ."
        
        #   rdfs:seeAlso <http://dbpedia.org/resource/Ginseng>
        see_also_predicate = format_uri(_expand_curie("rdfs:seeAlso", mock_settings_for_formatter.DEFAULT_PREFIXES))
        see_also_object_uri = format_uri("http://dbpedia.org/resource/Ginseng") # 对象是URI
                                                                               # Object is URI
        expected_see_also_triple = f"{formatted_entity_uri} {see_also_predicate} {see_also_object_uri} ."

        # tcm-onto:hasDescription "一种珍贵的草药。"
        desc_predicate = format_uri(_expand_curie("tcm-onto:hasDescription", mock_settings_for_formatter.DEFAULT_PREFIXES))
        desc_literal = format_literal("一种珍贵的草药。", datatype="string")
        expected_desc_triple = f"{formatted_entity_uri} {desc_predicate} {desc_literal} ."

        # 验证实体三元组是否在 GRAPH 块内
        # Verify entity triples are inside the GRAPH block
        # 通过查找 GRAPH { ... triples ... } 的方式来粗略判断
        # Roughly check by looking for GRAPH { ... triples ... }
        graph_block_start = sparql_query.find(f"GRAPH <{mock_source_graph_uri_val}> {{")
        graph_block_end = sparql_query.rfind("}}") # 假设实体图是最后一个图
                                                  # Assume entity graph is the last graph
        self.assertTrue(graph_block_start != -1 and graph_block_end != -1 and graph_block_start < graph_block_end,
                        "未能正确定位实体 GRAPH 块。")
                        # "Failed to correctly locate the entity GRAPH block."
        
        entity_graph_content = sparql_query[graph_block_start + len(f"GRAPH <{mock_source_graph_uri_val}> {{") : graph_block_end]

        self.assertIn(expected_type_triple, entity_graph_content, "类型三元组错误或不在实体图中。")
        self.assertIn(expected_label_triple, entity_graph_content, "标签三元组错误或不在实体图中。")
        self.assertIn(expected_taste_triple, entity_graph_content, "味道属性三元组错误或不在实体图中。")
        self.assertIn(expected_see_also_triple, entity_graph_content, "seeAlso属性三元组错误或不在实体图中。")
        self.assertIn(expected_desc_triple, entity_graph_content, "描述属性三元组错误或不在实体图中。")


        # 检查源数据三元组是否在默认图中 (即不在实体 GRAPH 块内，但在总查询内)
        # Check if source data triples are in the default graph (i.e., not inside the entity GRAPH block, but in the overall query)
        for triple in mock_source_triples_val:
            self.assertIn(triple, sparql_query, f"源数据三元组 '{triple}' 缺失。")
                                             # f"Source data triple '{triple}' is missing."
            self.assertNotIn(triple, entity_graph_content, f"源数据三元组 '{triple}' 不应在实体 GRAPH 块内。")
                                                       # f"Source data triple '{triple}' should not be inside the entity GRAPH block."
            
        # 5. 确保 mock 被正确调用
        # 5. Ensure mocks were called correctly
        #   验证 mint_entity_uri 调用
        #   Verify mint_entity_uri call
        #   prepare_entity_sparql_insert 内部调用 mint_entity_uri(entity_type_name, entity_label, *entity_id_args)
        #   prepare_entity_sparql_insert internally calls mint_entity_uri(entity_type_name, entity_label, *entity_id_args)
        mock_mint_entity_uri.assert_called_once_with(
            entity_type_name_input, 
            entity_label_input, 
            *entity_id_args_input
        )
        
        #   验证 create_source_metadata 调用
        #   Verify create_source_metadata call
        mock_create_source_metadata.assert_called_once_with(**source_details_input)

    @patch('tcm_kg_virtuoso_module.core.data_formatter.create_source_metadata')
    @patch('tcm_kg_virtuoso_module.core.data_formatter.mint_entity_uri')
    def test_prepare_entity_sparql_insert_no_properties_no_id_args(self, mock_mint_entity_uri, mock_create_source_metadata):
        # 测试无实体属性、无附加ID参数的情况
        # Test case with no entity properties and no additional ID arguments

        mock_entity_uri_val = "http://tcm.example.org/entity/GeneratedEntity/Syndrome_Cold"
        mock_mint_entity_uri.return_value = mock_entity_uri_val

        mock_source_graph_uri_val = "http://tcm.example.org/source_graph/Source_ClinicalGuideline_V1"
        mock_source_triples_val = [
            "<http://tcm.example.org/source/CG_V1> <dcterms:title> \"Clinical Guideline V1\" ."
        ]
        mock_create_source_metadata.return_value = (mock_source_graph_uri_val, mock_source_triples_val)

        entity_type_name_input = "Syndrome" # 证候
        entity_label_input = "风寒束表证"   # Wind-Cold Affecting the Exterior Syndrome
        entity_properties_input = {} # 空属性字典
                                   # Empty properties dictionary
        source_details_input = {
            "citation": "Clinical Guideline V1", "original_text": "Patient exhibits aversion to cold, fever, etc.",
            "document_identifier": "CG_V1", "source_type": "Guideline",
            "source_section": "Section 2", "source_subsection": "Item 3"
        }
        # entity_id_args 为 None (默认)
        # entity_id_args is None (default)

        sparql_query = prepare_entity_sparql_insert(
            entity_type_name_input, entity_label_input, entity_properties_input,
            source_details_input # entity_id_args 省略
                               # entity_id_args omitted
        )

        self.assertTrue(sparql_query.startswith("INSERT DATA {"))
        self.assertIn(f"GRAPH <{mock_source_graph_uri_val}> {{", sparql_query)

        formatted_entity_uri = format_uri(mock_entity_uri_val)
        rdf_type_predicate = format_uri(_expand_curie("rdf:type", mock_settings_for_formatter.DEFAULT_PREFIXES))
        expected_entity_class_uri = _expand_curie(f"tcm-onto:{entity_type_name_input}", mock_settings_for_formatter.DEFAULT_PREFIXES)
        formatted_entity_class_uri = format_uri(expected_entity_class_uri)
        expected_type_triple = f"{formatted_entity_uri} {rdf_type_predicate} {formatted_entity_class_uri} ."
        
        rdfs_label_predicate = format_uri(_expand_curie("rdfs:label", mock_settings_for_formatter.DEFAULT_PREFIXES))
        formatted_label_literal = format_literal(entity_label_input, datatype="string")
        expected_label_triple = f"{formatted_entity_uri} {rdfs_label_predicate} {formatted_label_literal} ."

        graph_block_start = sparql_query.find(f"GRAPH <{mock_source_graph_uri_val}> {{")
        graph_block_end = sparql_query.rfind("}}") 
        entity_graph_content = sparql_query[graph_block_start + len(f"GRAPH <{mock_source_graph_uri_val}> {{") : graph_block_end]

        self.assertIn(expected_type_triple, entity_graph_content)
        self.assertIn(expected_label_triple, entity_graph_content)
        
        # 确认没有其他属性三元组被错误添加
        # Confirm no other property triples were mistakenly added
        # (通过检查行数或更复杂的解析，这里简单假设类型和标签是仅有的)
        # (By checking line count or more complex parsing, here simply assume type and label are the only ones)
        lines_in_entity_graph = entity_graph_content.strip().count('\n')
        self.assertEqual(lines_in_entity_graph, 1, "实体图中应只有类型和标签两条三元组（不包括可能的空行）。") 
                                                # "Entity graph should only contain type and label triples (excluding possible empty lines)."
                                                # (Note: .count('\n') gives N-1 lines for N triples. If each triple is on one line, it should be 1 for 2 triples)
                                                # Corrected: each triple ends with ' .', so count ' .'
        self.assertEqual(entity_graph_content.strip().count(" ."), 2, "实体图中应恰好有两条三元组。")
                                                                    # "Entity graph should have exactly two triples."


        for triple in mock_source_triples_val:
            self.assertIn(triple, sparql_query)
            self.assertNotIn(triple, entity_graph_content)
            
        mock_mint_entity_uri.assert_called_once_with(
            entity_type_name_input, 
            entity_label_input # *entity_id_args 为空
                               # *entity_id_args is empty
        )
        mock_create_source_metadata.assert_called_once_with(**source_details_input)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
