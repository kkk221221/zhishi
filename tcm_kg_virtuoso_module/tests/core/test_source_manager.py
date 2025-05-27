# tcm_kg_virtuoso_module/tests/core/test_source_manager.py
import unittest

# 导入需要测试的函数
# Import the function to be tested
from tcm_kg_virtuoso_module.core.source_manager import create_source_metadata

# 导入 source_manager 使用的辅助函数 (真实版本)
# Import helper functions used by source_manager (real versions)
from tcm_kg_virtuoso_module.core.uri_minter import mint_source_uri
from tcm_kg_virtuoso_module.core.data_formatter import format_uri, format_literal
# COMMON_DATATYPES 不是直接在 source_manager 中使用，而是通过 format_literal 间接使用
# COMMON_DATATYPES is not directly used in source_manager, but indirectly through format_literal
from tcm_kg_virtuoso_module.config import settings # 用于访问 DEFAULT_PREFIXES 以获取预期值
                                                 # Used to access DEFAULT_PREFIXES for expected values

class TestSourceManager(unittest.TestCase):

    def _get_expected_predicate_uri(self, prefix_key: str, term: str) -> str:
        """
        辅助函数: 根据 settings 中的 DEFAULT_PREFIXES 构建完整的谓词或类型 URI。
        Helper function: Construct full predicate or type URI from DEFAULT_PREFIXES in settings.
        """
        # 从 settings.DEFAULT_PREFIXES 获取基础URI
        # Get base URI from settings.DEFAULT_PREFIXES
        # settings.py 中 DEFAULT_PREFIXES 的值已经是完整的 URI 前缀
        # The values in DEFAULT_PREFIXES in settings.py are already complete URI prefixes
        # 例如 "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        # For example, "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        # 所以我们直接拼接 term
        # So we directly concatenate the term
        base_uri = settings.DEFAULT_PREFIXES.get(prefix_key)
        if base_uri is None:
            raise ValueError(f"前缀 '{prefix_key}' 在 settings.DEFAULT_PREFIXES 中未定义。")
            # Raise ValueError if prefix_key is not defined in settings.DEFAULT_PREFIXES
        
        # 根据 source_manager.py 中的逻辑，它是直接拼接的：
        # According to the logic in source_manager.py, it's a direct concatenation:
        # rdf_type_uri = settings.DEFAULT_PREFIXES.get('rdf', ...) + 'type'
        return base_uri + term

    def test_create_source_metadata_basic(self):
        # 测试基本的源元数据创建
        # Test basic source metadata creation
        citation_val = "来源文献：《黄帝内经》"
        original_text_val = "原文内容：阴平阳秘，精神乃治。"
        doc_id_val = "HDNJ-001"
        source_type_val = "古籍" # 古代书籍 (Ancient Book)
        section_val = "素问"   # 素问 (Su Wen)
        subsection_val = "生气通天论" # 生气通天论 (Sheng Qi Tong Tian Lun)
        extra_uri_arg = "段落1" # 段落1 (Paragraph 1)

        # 1. 使用实际的 uri_minter 生成预期的 source_uri
        # 1. Generate expected source_uri using the actual uri_minter
        expected_source_uri = mint_source_uri(
            source_type_val, doc_id_val, section_val, subsection_val, extra_uri_arg
        )
        
        # 执行被测试函数
        # Execute the function under test
        actual_source_uri, actual_triples = create_source_metadata(
            citation_val, original_text_val, doc_id_val, 
            source_type_val, section_val, subsection_val, extra_uri_arg
        )

        # 2. 验证返回的 source_uri
        # 2. Verify the returned source_uri
        self.assertEqual(actual_source_uri, expected_source_uri)

        # 3. 验证生成的三元组数量
        # 3. Verify the number of generated triples
        self.assertEqual(len(actual_triples), 3, "应生成3条三元组。") # "Should generate 3 triples."

        # 4. 定义预期的 URI 和字面量 (基于实际的 settings 和 data_formatter)
        # 4. Define expected URIs and literals (based on actual settings and data_formatter)
        
        # 格式化的主语 URI
        # Formatted subject URI
        expected_subject_formatted = format_uri(expected_source_uri)
        
        # 预期的谓词 URI
        # Expected predicate URIs
        rdf_type_uri_formatted = format_uri(self._get_expected_predicate_uri('rdf', 'type'))
        # 根据 source_manager.py, tcm-onto:SourceContext 的构建方式：
        # According to source_manager.py, the construction of tcm-onto:SourceContext:
        # tcm_onto_source_context_uri = settings.DEFAULT_PREFIXES.get('tcm-onto', ...) + 'SourceContext'
        tcm_SourceContext_uri_formatted = format_uri(self._get_expected_predicate_uri('tcm-onto', 'SourceContext'))
        dcterms_citation_uri_formatted = format_uri(self._get_expected_predicate_uri('dcterms', 'bibliographicCitation'))
        tcm_hasOriginalText_uri_formatted = format_uri(self._get_expected_predicate_uri('tcm-onto', 'hasOriginalText'))
        
        # 预期的字面量 (使用 data_formatter.format_literal 以确保一致性)
        # Expected literals (use data_formatter.format_literal for consistency)
        # source_manager.py 中硬编码了 datatype="string"
        # datatype="string" is hardcoded in source_manager.py
        expected_citation_literal = format_literal(citation_val, datatype="string")
        expected_original_text_literal = format_literal(original_text_val, datatype="string")

        # 5. 检查每个三元组的内容
        # 5. Check the content of each triple
        
        # 三元组 1: rdf:type
        # Triple 1: rdf:type
        # <source_uri> <rdf:type> <tcm-onto:SourceContext> .
        # is_object_literal=False for rdf:type triple's object
        expected_triple1_str = f"{expected_subject_formatted} {rdf_type_uri_formatted} {tcm_SourceContext_uri_formatted} ."
        self.assertIn(expected_triple1_str, actual_triples, "RDF type三元组不匹配或缺失。")
                      # "RDF type triple mismatch or missing."

        # 三元组 2: dcterms:bibliographicCitation
        # Triple 2: dcterms:bibliographicCitation
        # <source_uri> <dcterms:bibliographicCitation> "citation"^^<xsd:string> .
        # is_object_literal=True for citation
        expected_triple2_str = f"{expected_subject_formatted} {dcterms_citation_uri_formatted} {expected_citation_literal} ."
        self.assertIn(expected_triple2_str, actual_triples, "文献引用三元组不匹配或缺失。")
                      # "Bibliographic citation triple mismatch or missing."

        # 三元组 3: tcm-onto:hasOriginalText
        # Triple 3: tcm-onto:hasOriginalText
        # <source_uri> <tcm-onto:hasOriginalText> "original_text"^^<xsd:string> .
        # is_object_literal=True for original text
        expected_triple3_str = f"{expected_subject_formatted} {tcm_hasOriginalText_uri_formatted} {expected_original_text_literal} ."
        self.assertIn(expected_triple3_str, actual_triples, "原始文本三元组不匹配或缺失。")
                      # "Original text triple mismatch or missing."

    def test_create_source_metadata_special_chars_in_literals(self):
        # 测试字面量中包含特殊字符的情况
        # Test scenario with special characters in literals
        citation_val = '文献 "引言" 部分, 第 5 页'
        original_text_val = '记录曰：\n"道生一，一生二，二生三，三生万物。"\t(老子)'
        doc_id_val = "LZ-道德经-CH42"
        source_type_val = "哲学著作" # Philosophical Work
        section_val = "第四十二章" # Chapter 42
        subsection_val = "论道"   # On Tao
        
        expected_source_uri = mint_source_uri(
            source_type_val, doc_id_val, section_val, subsection_val
        )
        
        actual_source_uri, actual_triples = create_source_metadata(
            citation_val, original_text_val, doc_id_val, 
            source_type_val, section_val, subsection_val
        )

        self.assertEqual(actual_source_uri, expected_source_uri)
        self.assertEqual(len(actual_triples), 3)

        expected_subject_formatted = format_uri(expected_source_uri)
        dcterms_citation_uri_formatted = format_uri(self._get_expected_predicate_uri('dcterms', 'bibliographicCitation'))
        tcm_hasOriginalText_uri_formatted = format_uri(self._get_expected_predicate_uri('tcm-onto', 'hasOriginalText'))

        # format_literal 会处理转义
        # format_literal will handle escaping
        expected_citation_literal = format_literal(citation_val, datatype="string")
        expected_original_text_literal = format_literal(original_text_val, datatype="string")
        
        # 检查包含转义字符的字面量的三元组
        # Check triples with literals containing escaped characters
        expected_triple_citation_escaped = f"{expected_subject_formatted} {dcterms_citation_uri_formatted} {expected_citation_literal} ."
        self.assertIn(expected_triple_citation_escaped, actual_triples, "带转义的引文字典三元组错误。")
                       # "Escaped citation literal triple error."
        
        expected_triple_text_escaped = f"{expected_subject_formatted} {tcm_hasOriginalText_uri_formatted} {expected_original_text_literal} ."
        self.assertIn(expected_triple_text_escaped, actual_triples, "带转义的原始文本三元组错误。")
                       # "Escaped original text triple error."


if __name__ == '__main__':
    # 这使得测试可以直接从命令行运行
    # This allows tests to be run directly from the command line
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
