# tcm_kg_virtuoso_module/tests/core/test_data_formatter.py
import unittest
from unittest.mock import patch, MagicMock # Removed ANY as it's not used now

# 导入需要测试的函数和常量
from tcm_kg_virtuoso_module.core.data_formatter import (
    format_uri,
    escape_literal_value,
    format_literal,
    create_rdf_triple,
    _expand_curie, 
    prepare_entity_sparql_insert,
    prepare_relationship_sparql_insert, # 导入 prepare_relationship_sparql_insert
    COMMON_DATATYPES,

prepare_sparql_for_attribute_supersede,
prepare_sparql_for_attribute_correction,
prepare_sparql_for_attribute_delete
)
from tcm_kg_virtuoso_module.config import settings # 用于访问真实的 DEFAULT_PREFIXES

# 使用真实的 settings.DEFAULT_PREFIXES 来构建测试中使用的 mock_DEFAULT_PREFIXES
# 这确保测试与实际配置的结构一致
mock_DEFAULT_PREFIXES_for_test = settings.DEFAULT_PREFIXES.copy()

# DEFAULT_PREFIXES 在 data_formatter 模块级别被引用
# 通过 patch data_formatter 模块内部使用的 DEFAULT_PREFIXES 确保测试隔离性
@patch('tcm_kg_virtuoso_module.core.data_formatter.DEFAULT_PREFIXES', mock_DEFAULT_PREFIXES_for_test)
class TestDataFormatter(unittest.TestCase):

    # ... (保留所有现有的 test_format_uri, test_escape_literal_value, test_format_literal_*, test_create_rdf_triple_*, test_expand_curie) ...
    # ... (Keep all existing test methods for format_uri, escape_literal_value, format_literal_*, create_rdf_triple_*, _expand_curie) ...
    # The following are existing tests, ensure they are present and correct:

    def test_format_uri(self):
        # 测试 URI 格式化
        self.assertEqual(format_uri("http://example.com/res"), "<http://example.com/res>")
        self.assertEqual(format_uri("<http://example.com/res2>"), "<http://example.com/res2>")
        self.assertEqual(format_uri("<123>"), "<123>") 
        self.assertEqual(format_uri(""), "<>")

    def test_escape_literal_value(self):
        # 测试字面量值的转义
        self.assertEqual(escape_literal_value("simple"), "simple")
        self.assertEqual(escape_literal_value('with "quotes"'), 'with \\"quotes\\"')
        self.assertEqual(escape_literal_value("with \\backslash"), "with \\\\backslash")
        self.assertEqual(escape_literal_value("new\nline"), "new\\nline")
        self.assertEqual(escape_literal_value("carriage\rreturn"), "carriage\\rreturn")
        self.assertEqual(escape_literal_value("tab\tchar"), "tab\\tchar")
        self.assertEqual(escape_literal_value('all: \\\"\n\r\t'), 'all: \\\\\\\"\\n\\r\\t')
        self.assertEqual(escape_literal_value("123"), "123")

    def test_format_literal_plain(self):
        # 测试普通字面量
        self.assertEqual(format_literal("hello"), '"hello"')
        self.assertEqual(format_literal(123.45), '"123.45"')
        self.assertEqual(format_literal(True), '"True"')

    def test_format_literal_with_known_datatype(self):
        # 测试带已知数据类型的字面量
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
        # 测试未知短格式数据类型
        self.assertEqual(format_literal("unknown type", datatype="nonExistentType"), '"unknown type"')
        mock_print.assert_any_call("警告：数据类型 'nonExistentType' 未被识别。将省略数据类型。")

    def test_format_literal_with_lang_tag(self):
        # 测试带语言标签的字面量
        self.assertEqual(format_literal("你好", lang="zh"), '"你好"@zh')
        self.assertEqual(format_literal("Hello", lang="en-US"), '"Hello"@en-US')

    @patch('builtins.print')
    def test_format_literal_invalid_lang_tag(self, mock_print):
        # 测试无效的语言标签
        self.assertEqual(format_literal("text", lang=""), '"text"') 
        mock_print.assert_any_call("警告：语言标签 '' 无效。将省略语言标签。")

    def test_format_literal_datatype_preferred_over_lang(self):
        # 测试数据类型优先于语言标签
        expected_str_dt = mock_DEFAULT_PREFIXES_for_test['xsd'] + "string"
        self.assertEqual(format_literal("text", datatype="string", lang="en"), f'"text"^^<{expected_str_dt}>')

    def test_format_literal_with_escaping(self):
        # 测试需要转义的字面量
        val_to_escape = 'text with "quotes" and \\ backslash, also \n newline.'
        escaped_val = 'text with \\"quotes\\" and \\\\ backslash, also \\n newline.'
        self.assertEqual(format_literal(val_to_escape), f'"{escaped_val}"')

    def test_create_rdf_triple_all_uris(self):
        # 测试所有部分都是 URI
        s, p, o = "http://example.com/s", "http://example.com/p", "http://example.com/o"
        self.assertEqual(create_rdf_triple(s, p, o), f"<{s}> <{p}> <{o}> .")

    def test_create_rdf_triple_with_literal_object(self):
        # 测试宾语是字面量
        s, p = "http://example.com/s", "http://example.com/p"
        obj_plain_literal_val = "A simple literal"
        formatted_obj_plain = format_literal(obj_plain_literal_val) 
        self.assertEqual(create_rdf_triple(s, p, formatted_obj_plain, is_object_literal=True),
                         f"<{s}> <{p}> {formatted_obj_plain} .")

    def test_expand_curie(self):
        # 测试 _expand_curie 辅助函数
        self.assertEqual(_expand_curie("tcm-onto:hasTaste", mock_DEFAULT_PREFIXES_for_test),
                         mock_DEFAULT_PREFIXES_for_test['tcm-onto'] + "hasTaste")
        full_uri = "http://example.org/fullURI"
        self.assertEqual(_expand_curie(full_uri, mock_DEFAULT_PREFIXES_for_test), full_uri)
        with patch('builtins.print') as mock_print:
            self.assertEqual(_expand_curie("unknown:property", mock_DEFAULT_PREFIXES_for_test), "unknown:property")
            mock_print.assert_any_call("警告：CURIE前缀 'unknown' 在提供的映射中未找到。CURIE: 'unknown:property'")
        with patch('builtins.print') as mock_print:
             self.assertEqual(_expand_curie("justAString", mock_DEFAULT_PREFIXES_for_test), "justAString")
             mock_print.assert_any_call("警告：输入值 'justAString' 不是有效的CURIE且不是可识别的完整URI。")


    # --- 更新后的 prepare_entity_sparql_insert 测试 ---
    # --- Updated tests for prepare_entity_sparql_insert ---
    @patch('tcm_kg_virtuoso_module.core.source_manager.create_source_metadata')
    @patch('tcm_kg_virtuoso_module.core.data_formatter.mint_entity_uri')
    def test_prepare_entity_sparql_insert_basic_and_multivalue_props(self, mock_mint_entity_uri, mock_create_source_metadata):
        # 测试基本的实体 SPARQL INSERT 查询生成，并包含多值属性
        # Test basic entity SPARQL INSERT query generation, including multi-valued properties

        # 1. 配置 Mocks 的返回值
        mock_entity_uri_val = "http://tcm.example.org/entity/GeneratedEntity/Herb_Ginseng_123"
        mock_mint_entity_uri.return_value = mock_entity_uri_val # mint_entity_uri 返回的是裸 URI
                                                              # mint_entity_uri returns a raw URI

        mock_source_graph_uri_val = "http://tcm.example.org/source_graph/SourceDoc_ShangHanLun_CH1_P1"
        # mock_source_triples_val = [
        #     "<http://tcm.example.org/source/SHL_CH1_P1> <dcterms:bibliographicCitation> \"ShangHanLun Chapter 1 Paragraph 1\" .",
        #     "<http://tcm.example.org/source/SHL_CH1_P1> <rdf:type> <tcm-onto:SourceContext> ."
        # ] # 确保这里的 CURIEs 和字面量与 data_formatter 内部生成的一致
          # Ensure CURIEs and literals here match what data_formatter would generate internally
        
        # 为了使 mock_source_triples_val 更真实，我们使用实际的前缀进行扩展
        # To make mock_source_triples_val more realistic, expand using actual prefixes
        real_dcterms_citation = _expand_curie("dcterms:bibliographicCitation", mock_DEFAULT_PREFIXES_for_test)
        real_rdf_type = _expand_curie("rdf:type", mock_DEFAULT_PREFIXES_for_test)
        real_tcm_SourceContext = _expand_curie("tcm-onto:SourceContext", mock_DEFAULT_PREFIXES_for_test)
        mock_source_triples_val = [
            f"<http://tcm.example.org/source/SHL_CH1_P1> <{real_dcterms_citation}> {format_literal('ShangHanLun Chapter 1 Paragraph 1', datatype='string')} .",
            f"<http://tcm.example.org/source/SHL_CH1_P1> <{real_rdf_type}> <{real_tcm_SourceContext}> ."
        ]
        mock_create_source_metadata.return_value = (mock_source_graph_uri_val, mock_source_triples_val)


        # 2. 准备输入参数
        entity_type_name_input = "Herb" 
        entity_label_input = "人参" 
        entity_properties_input = {
            "tcm-onto:hasTaste": ["甘", "微苦"], # 多值属性
                                            # Multi-valued property
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
        # prepare_entity_sparql_insert 现在返回 (sparql_query, entity_uri)
        # prepare_entity_sparql_insert now returns (sparql_query, entity_uri)
        sparql_query, returned_entity_uri = prepare_entity_sparql_insert(
            entity_type_name_input, entity_label_input, entity_properties_input,
            source_details_input, entity_id_args_input
        )
        
        # 4. 验证 SPARQL 查询字符串和返回的实体 URI
        # 4. Verify SPARQL query string and returned entity URI
        self.assertEqual(returned_entity_uri, mock_entity_uri_val, "返回的实体 URI 与 mock 不符。")
                                                                    # "Returned entity URI does not match mock."

        self.assertTrue(sparql_query.startswith("INSERT DATA {"), "查询应以 INSERT DATA { 开始")
        self.assertTrue(sparql_query.strip().endswith("}"), "查询应以 } 结束")
        self.assertIn(f"GRAPH <{mock_source_graph_uri_val}> {{", sparql_query, "缺少 GRAPH 子句")

        # 构造预期的实体三元组
        formatted_entity_uri = format_uri(mock_entity_uri_val) # format_uri 添加尖括号
                                                              # format_uri adds angle brackets
        
        rdf_type_predicate = format_uri(_expand_curie("rdf:type", mock_DEFAULT_PREFIXES_for_test))
        # entity_class_uri 是传递给 mint_entity_uri 的第一个参数
        # entity_class_uri is the first argument passed to mint_entity_uri
        expected_entity_class_uri_for_minting = _expand_curie(f"tcm-onto:{entity_type_name_input}", mock_DEFAULT_PREFIXES_for_test)
        formatted_entity_class_uri_for_triple = format_uri(expected_entity_class_uri_for_minting)
        expected_type_triple = f"{formatted_entity_uri} {rdf_type_predicate} {formatted_entity_class_uri_for_triple} ."
        
        rdfs_label_predicate = format_uri(_expand_curie("rdfs:label", mock_DEFAULT_PREFIXES_for_test))
        formatted_label_literal = format_literal(entity_label_input, datatype="string")
        expected_label_triple = f"{formatted_entity_uri} {rdfs_label_predicate} {formatted_label_literal} ."

        # 多值属性 tcm-onto:hasTaste
        # Multi-valued property tcm-onto:hasTaste
        taste_predicate_uri = format_uri(_expand_curie("tcm-onto:hasTaste", mock_DEFAULT_PREFIXES_for_test))
        expected_taste_triple_sweet = f"{formatted_entity_uri} {taste_predicate_uri} {format_literal('甘', datatype='string')} ."
        expected_taste_triple_bitter = f"{formatted_entity_uri} {taste_predicate_uri} {format_literal('微苦', datatype='string')} ."
        
        see_also_predicate = format_uri(_expand_curie("rdfs:seeAlso", mock_DEFAULT_PREFIXES_for_test))
        see_also_object_uri = format_uri("http://dbpedia.org/resource/Ginseng")
        expected_see_also_triple = f"{formatted_entity_uri} {see_also_predicate} {see_also_object_uri} ."

        desc_predicate = format_uri(_expand_curie("tcm-onto:hasDescription", mock_DEFAULT_PREFIXES_for_test))
        desc_literal = format_literal("一种珍贵的草药。", datatype="string")
        expected_desc_triple = f"{formatted_entity_uri} {desc_predicate} {desc_literal} ."
        
        # 提取 GRAPH 块内容
        # Extract GRAPH block content
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
        self.assertIn(expected_taste_triple_sweet.strip(), entity_graph_content, "多值属性 '甘' 未找到。")
                                                                                # "Multi-valued property '甘' not found."
        self.assertIn(expected_taste_triple_bitter.strip(), entity_graph_content, "多值属性 '微苦' 未找到。")
                                                                                  # "Multi-valued property '微苦' not found."
        self.assertIn(expected_see_also_triple.strip(), entity_graph_content)
        self.assertIn(expected_desc_triple.strip(), entity_graph_content)

        # 检查源数据三元组
        # Check source data triples
        source_triples_joined = "\n".join(mock_source_triples_val) # .strip() each?
        self.assertIn(source_triples_joined, sparql_query)
        for mock_src_triple in mock_source_triples_val:
             self.assertNotIn(mock_src_triple.strip(), entity_graph_content) # 确保不在实体 GRAPH 内
                                                                            # Ensure not inside entity GRAPH
            
        # 5. 确保 mock 被正确调用
        # 5. Ensure mocks were called correctly
        #   mint_entity_uri 的第一个参数应该是完整的类 URI
        #   The first argument to mint_entity_uri should be the full class URI
        mock_mint_entity_uri.assert_called_once_with(
            expected_entity_class_uri_for_minting, # 这是关键的改变
                                                   # This is the key change
            entity_label_input, 
            *entity_id_args_input
        )
        mock_create_source_metadata.assert_called_once_with(**source_details_input)

    # 可以添加更多测试用例，例如没有属性、没有 entity_id_args 等。
    # More test cases can be added, e.g., no properties, no entity_id_args, etc.
    # The test_prepare_entity_sparql_insert_no_properties_no_id_args from the previous version
    # can be adapted similarly.

    @patch('tcm_kg_virtuoso_module.core.data_formatter.create_source_metadata') # Patch where it's used
    def test_prepare_relationship_sparql_insert(self, mock_create_source_metadata):
        # 测试 prepare_relationship_sparql_insert 函数
        # Test the prepare_relationship_sparql_insert function

        # 1. 配置 Mocks 的返回值
        # 1. Configure mock return values
        mock_source_graph_uri = "http://example.com/graph/sourceRel123"
        # 使用实际的前缀和 format_literal 来创建更真实的元数据三元组
        # Use actual prefixes and format_literal to create more realistic metadata triples
        real_dcterms_citation = _expand_curie("dcterms:bibliographicCitation", mock_DEFAULT_PREFIXES_for_test)
        real_xsd_string = COMMON_DATATYPES["string"] # 从 COMMON_DATATYPES 获取
        mock_metadata_triples = [
            f"<http://example.com/sourceRel123/context> <{real_dcterms_citation}> {format_literal('TestSourceCitationForRel', datatype=real_xsd_string)} ."
            # 可以在这里添加更多模拟的元数据三元组
            # More mock metadata triples can be added here
        ]
        mock_create_source_metadata.return_value = (mock_source_graph_uri, mock_metadata_triples)

        # 2. 准备输入参数
        # 2. Prepare input parameters
        subject_uri_input = "http://example.com/subject/s1"
        predicate_curie_input = "tcm-onto:relatesTo" # 确保 tcm-onto 在 mock_DEFAULT_PREFIXES_for_test 中
                                                   # Ensure tcm-onto is in mock_DEFAULT_PREFIXES_for_test
        object_uri_input = "http://example.com/object/o1"
        source_details_input = {
            "citation": "Test Relationship Citation",
            "document_identifier": "TestDocRel",
            "source_type": "TestType",
            # 提供足够的细节以满足 create_source_metadata 的参数需求（即使它被mock了）
            # Provide enough details to satisfy create_source_metadata's parameter needs (even if mocked)
            "source_id_components": ["TestDocRel", "RelContext1"] 
        }

        # 3. 调用被测试的函数
        # 3. Call the function under test
        sparql_query = prepare_relationship_sparql_insert(
            subject_uri_input, predicate_curie_input, object_uri_input, source_details_input
        )

        # 4. 验证 SPARQL 查询字符串
        # 4. Verify the SPARQL query string
        self.assertTrue(sparql_query.startswith("INSERT DATA {"), "查询应以 INSERT DATA { 开始")
        self.assertTrue(sparql_query.strip().endswith("}"), "查询应以 } 结束")
        self.assertIn(f"GRAPH <{mock_source_graph_uri}> {{", sparql_query, "缺少关系图的 GRAPH 子句")

        # 验证关系三元组
        # Verify the relationship triple
        expected_predicate_expanded = _expand_curie(predicate_curie_input, mock_DEFAULT_PREFIXES_for_test)
        expected_relationship_triple = (
            f"{format_uri(subject_uri_input)} {format_uri(expected_predicate_expanded)} {format_uri(object_uri_input)} ."
        )
        
        # 提取关系图内容
        # Extract relationship graph content
        graph_block_start_idx = sparql_query.find(f"GRAPH <{mock_source_graph_uri}> {{") + len(f"GRAPH <{mock_source_graph_uri}> {{")
        balance = 1
        graph_block_end_idx = -1
        # 找到匹配的 '}'
        # Find the matching '}'
        temp_idx = graph_block_start_idx 
        while temp_idx < len(sparql_query):
            if sparql_query[temp_idx] == '{':
                balance +=1
            elif sparql_query[temp_idx] == '}':
                balance -=1
                if balance == 0:
                    graph_block_end_idx = temp_idx
                    break
            temp_idx += 1
        
        self.assertNotEqual(graph_block_end_idx, -1, "未能找到 GRAPH 块的结束符。") # "Failed to find the end of the GRAPH block."
        relationship_graph_content = sparql_query[graph_block_start_idx:graph_block_end_idx].strip()
        
        self.assertIn(expected_relationship_triple.strip(), relationship_graph_content, "关系三元组不正确或未在指定图中找到。")
                                                                                    # "Relationship triple is incorrect or not found in the specified graph."

        # 验证来源元数据三元组
        # Verify source metadata triples
        metadata_triples_joined = "\n".join(mock_metadata_triples)
        self.assertIn(metadata_triples_joined, sparql_query, "来源元数据三元组未找到。")
                                                            # "Source metadata triples not found."
        # 确保元数据三元组不在关系图中
        # Ensure metadata triples are not in the relationship graph
        for mock_meta_triple in mock_metadata_triples:
            self.assertNotIn(mock_meta_triple.strip(), relationship_graph_content, "来源元数据三元组不应在关系图中。")
                                                                                  # "Source metadata triple should not be in the relationship graph."


        # 5. 确保 mock 被正确调用
        # 5. Ensure mock was called correctly
        mock_create_source_metadata.assert_called_once_with(**source_details_input)

    # --- 新增的实体更新相关SPARQL生成函数的测试 ---
    # --- Tests for new entity update related SPARQL generation functions ---

    @patch('tcm_kg_virtuoso_module.core.data_formatter.create_source_metadata')
    def test_prepare_sparql_for_attribute_supersede(self, mock_create_source_metadata):
        """测试 prepare_sparql_for_attribute_supersede 函数 (测试属性替换的SPARQL准备)"""
        entity_uri_input = "http://example.com/entity/herb1"
        
        # 模拟 create_source_metadata
        mock_new_graph_uri = "http://example.com/graph/new_source_herb1_update1"
        mock_new_source_triples = [
            f"<{mock_new_graph_uri}/context> <{_expand_curie('dcterms:creator', mock_DEFAULT_PREFIXES_for_test)}> \"Test User\" ."
        ]
        mock_create_source_metadata.return_value = (mock_new_graph_uri, mock_new_source_triples)

        source_details_input = {"citation": "Supersede Source", "document_identifier": "doc_supersede_1"}

        attributes_to_add = [
            {"property": "tcm-onto:hasDescription", "value": "新的描述信息", "datatype": "xsd:string"},
            {"property": "rdfs:seeAlso", "value": "http://example.com/entity/relatedHerb"},
            {"property": "tcm-onto:maxDose", "value": 15} # 将测试无 datatype 的情况
        ]

        queries = prepare_sparql_for_attribute_supersede(entity_uri_input, attributes_to_add, source_details_input)

        self.assertEqual(len(queries), 2 * len(attributes_to_add) + 1) # 每个属性2条 (DELETE, INSERT) + 1条来源元数据 INSERT

        formatted_entity_uri = format_uri(entity_uri_input)

        # 验证第一个属性 (描述)
        prop1_uri = format_uri(_expand_curie(attributes_to_add[0]["property"], mock_DEFAULT_PREFIXES_for_test))
        expected_delete_q1 = f"DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {prop1_uri} ?old_value . }} }} WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {prop1_uri} ?old_value . }} }};"
        self.assertIn(expected_delete_q1.strip(), queries[0])
        
        formatted_val1 = format_literal(attributes_to_add[0]["value"], datatype=attributes_to_add[0]["datatype"])
        expected_insert_q1 = f"INSERT DATA {{ GRAPH <{mock_new_graph_uri}> {{ {formatted_entity_uri} {prop1_uri} {formatted_val1} . }} }};"
        self.assertIn(expected_insert_q1.strip(), queries[1])

        # 验证第二个属性 (seeAlso - URI value)
        prop2_uri = format_uri(_expand_curie(attributes_to_add[1]["property"], mock_DEFAULT_PREFIXES_for_test))
        formatted_val2 = format_uri(attributes_to_add[1]["value"]) # URI值
        expected_delete_q2 = f"DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {prop2_uri} ?old_value . }} }} WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {prop2_uri} ?old_value . }} }};"
        self.assertIn(expected_delete_q2.strip(), queries[2])
        expected_insert_q2 = f"INSERT DATA {{ GRAPH <{mock_new_graph_uri}> {{ {formatted_entity_uri} {prop2_uri} {formatted_val2} . }} }};"
        self.assertIn(expected_insert_q2.strip(), queries[3])
        
        # 验证第三个属性 (maxDose - 无 datatype)
        prop3_uri = format_uri(_expand_curie(attributes_to_add[2]["property"], mock_DEFAULT_PREFIXES_for_test))
        formatted_val3 = format_literal(attributes_to_add[2]["value"]) # 无 datatype，应为普通字面量
        expected_delete_q3 = f"DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {prop3_uri} ?old_value . }} }} WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {prop3_uri} ?old_value . }} }};"
        self.assertIn(expected_delete_q3.strip(), queries[4])
        expected_insert_q3 = f"INSERT DATA {{ GRAPH <{mock_new_graph_uri}> {{ {formatted_entity_uri} {prop3_uri} {formatted_val3} . }} }};"
        self.assertIn(expected_insert_q3.strip(), queries[5])

        # 验证来源元数据插入
        expected_source_insert = f"INSERT DATA {{\n{mock_new_source_triples[0]}\n}};" # 假设只有一个元数据三元组
        self.assertIn(expected_source_insert.strip(), queries[6])
        
        mock_create_source_metadata.assert_called_once_with(**source_details_input)

    @patch('tcm_kg_virtuoso_module.core.data_formatter.datetime')
    def test_prepare_sparql_for_attribute_correction(self, mock_datetime):
        """测试 prepare_sparql_for_attribute_correction 函数 (测试属性修正的SPARQL准备)"""
        # 模拟 datetime.now()
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2023-10-26T10:00:00"
        mock_datetime.now.return_value = mock_now

        entity_uri_input = "http://example.com/entity/herb2"
        property_to_correct_curie_input = "tcm-onto:hasDescription"
        new_value_input = "修正后的描述信息"
        new_value_datatype_input = "xsd:string"
        target_graph_uri_input = "http://example.com/graph/original_source_herb2"
        source_details_input = {
            "citation": "Correction Source Citation", 
            "original_text": "Correction original text",
            "document_identifier": "doc_correction_1"
        }

        queries = prepare_sparql_for_attribute_correction(
            entity_uri_input, property_to_correct_curie_input, new_value_input,
            new_value_datatype_input, target_graph_uri_input, source_details_input
        )
        
        self.assertEqual(len(queries), 3) # DELETE old, INSERT new, INSERT correction note

        formatted_entity_uri = format_uri(entity_uri_input)
        prop_uri = format_uri(_expand_curie(property_to_correct_curie_input, mock_DEFAULT_PREFIXES_for_test))

        # 验证删除旧值
        expected_delete_q = f"WITH <{target_graph_uri_input}> DELETE {{ {formatted_entity_uri} {prop_uri} ?old_value . }} WHERE {{ {formatted_entity_uri} {prop_uri} ?old_value . }};"
        self.assertIn(expected_delete_q.strip(), queries[0])

        # 验证插入新值
        formatted_new_val = format_literal(new_value_input, datatype=new_value_datatype_input)
        expected_insert_new_q = f"INSERT DATA {{ GRAPH <{target_graph_uri_input}> {{ {formatted_entity_uri} {prop_uri} {formatted_new_val} . }} }};"
        self.assertIn(expected_insert_new_q.strip(), queries[1])

        # 验证修正笔记
        correction_note_prop_uri = format_uri(_expand_curie("tcm-onto:correctionNote", mock_DEFAULT_PREFIXES_for_test))
        # 修正笔记的文本内容会比较复杂，这里只检查关键部分
        self.assertTrue(queries[2].startswith(f"INSERT DATA {{ <{target_graph_uri_input}> <{correction_note_prop_uri}> "))
        self.assertIn("修正后的描述信息", queries[2]) # 新值
        self.assertIn("2023-10-26T10:00:00", queries[2]) # 时间戳
        self.assertIn(source_details_input["citation"], queries[2]) # 来源引用
        self.assertTrue(queries[2].endswith(" . }};"))

    def test_prepare_sparql_for_attribute_delete(self):
        """测试 prepare_sparql_for_attribute_delete 函数 (测试属性删除的SPARQL准备)"""
        entity_uri_input = "http://example.com/entity/herb3"
        
        # 情况1: 删除特定属性（无值）
        attrs_to_delete_1 = [{"property": "tcm-onto:toBeRemovedProperty"}]
        queries1 = prepare_sparql_for_attribute_delete(entity_uri_input, attrs_to_delete_1)
        self.assertEqual(len(queries1), 1)
        formatted_entity_uri = format_uri(entity_uri_input)
        prop1_uri = format_uri(_expand_curie(attrs_to_delete_1[0]["property"], mock_DEFAULT_PREFIXES_for_test))
        expected_q1 = f"DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {prop1_uri} ?any_value . }} }} WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {prop1_uri} ?any_value . }} }};"
        self.assertIn(expected_q1.strip(), queries1[0])

        # 情况2: 删除特定属性-值对 (字面量)
        attrs_to_delete_2 = [{"property": "tcm-onto:oldName", "value": "旧名称", "datatype": "xsd:string"}]
        queries2 = prepare_sparql_for_attribute_delete(entity_uri_input, attrs_to_delete_2)
        self.assertEqual(len(queries2), 1)
        prop2_uri = format_uri(_expand_curie(attrs_to_delete_2[0]["property"], mock_DEFAULT_PREFIXES_for_test))
        val2_formatted = format_literal(attrs_to_delete_2[0]["value"], datatype=attrs_to_delete_2[0]["datatype"])
        expected_q2 = f"DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {prop2_uri} {val2_formatted} . }} }} WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {prop2_uri} {val2_formatted} . }} }};"
        self.assertIn(expected_q2.strip(), queries2[0])

        # 情况3: 删除特定属性-值对 (URI)
        attrs_to_delete_3 = [{"property": "rdfs:seeAlso", "value": "http://example.com/oldLink"}]
        queries3 = prepare_sparql_for_attribute_delete(entity_uri_input, attrs_to_delete_3)
        self.assertEqual(len(queries3), 1)
        prop3_uri = format_uri(_expand_curie(attrs_to_delete_3[0]["property"], mock_DEFAULT_PREFIXES_for_test))
        val3_formatted = format_uri(attrs_to_delete_3[0]["value"])
        expected_q3 = f"DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {prop3_uri} {val3_formatted} . }} }} WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {prop3_uri} {val3_formatted} . }} }};"
        self.assertIn(expected_q3.strip(), queries3[0])

        # 情况4: 混合删除
        attrs_to_delete_4 = [
            {"property": "tcm-onto:anotherProperty"},
            {"property": "tcm-onto:specificValue", "value": 123} # 无数据类型
        ]
        queries4 = prepare_sparql_for_attribute_delete(entity_uri_input, attrs_to_delete_4)
        self.assertEqual(len(queries4), 2)
        
        prop4a_uri = format_uri(_expand_curie(attrs_to_delete_4[0]["property"], mock_DEFAULT_PREFIXES_for_test))
        expected_q4a = f"DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {prop4a_uri} ?any_value . }} }} WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {prop4a_uri} ?any_value . }} }};"
        self.assertIn(expected_q4a.strip(), queries4[0])

        prop4b_uri = format_uri(_expand_curie(attrs_to_delete_4[1]["property"], mock_DEFAULT_PREFIXES_for_test))
        val4b_formatted = format_literal(attrs_to_delete_4[1]["value"]) # 无数据类型
        expected_q4b = f"DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {prop4b_uri} {val4b_formatted} . }} }} WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {prop4b_uri} {val4b_formatted} . }} }};"
        self.assertIn(expected_q4b.strip(), queries4[1])


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
