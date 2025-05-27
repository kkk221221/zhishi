# tcm_kg_virtuoso_module/tests/core/test_graph_operations.py
import unittest
from unittest.mock import patch, MagicMock, ANY # ANY can be useful for complex dicts

# Functions to be tested
from tcm_kg_virtuoso_module.core.graph_operations import add_entity, add_relationship
# For type hinting VirtuosoConnectionManager if needed
from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager
# To help construct expected dictionaries for assertion
from typing import Dict, List, Union 

class TestGraphOperations(unittest.TestCase):

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_entity_sparql_insert') # Keep for add_entity tests
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_relationship_sparql_insert') # Add for add_relationship tests
    def test_add_entity_successful_and_transforms_attributes(self, mock_prepare_relationship_sparql, mock_prepare_entity_sparql, mock_SparqlExecutor_class): # Add new mock to signature
        # 测试 add_entity 函数成功执行，并验证属性列表的正确转换
        # Test successful execution of add_entity and verify correct transformation of attribute list
        
        # 1. 准备 mock 对象和输入数据
        # 1. Prepare mock objects and input data
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        
        dummy_sparql_query = "INSERT DATA { <http://s> <http://p> <http://o> . }"
        mock_entity_uri_from_formatter = "http://example.com/entity/TestEntity_From_Formatter_1"
        # prepare_entity_sparql_insert 现在返回 (query, entity_uri)
        # prepare_entity_sparql_insert now returns (query, entity_uri)
        mock_prepare_entity_sparql.return_value = (dummy_sparql_query, mock_entity_uri_from_formatter)
        
        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance

        # entity_data 现在包含 'attributes_list'
        # entity_data now contains 'attributes_list'
        entity_data_input = {
            'entity_type_name': "Herb",
            'entity_label': "测试草药",
            'attributes_list': [ # 列表形式的属性
                               # List form for attributes
                {'property': 'tcm-onto:hasTaste', 'value': '甘'},
                {'property': 'tcm-onto:hasTaste', 'value': '微苦'}, # 同一属性，不同值
                                                                # Same property, different value
                {'property': 'rdfs:seeAlso', 'value': 'http://example.com/anotherHerb'}
            ],
            'source_details': {"citation": "Some Book", "original_text": "Text...", 
                               "document_identifier": "Book1", "source_type": "Book",
                               "source_section": "Ch1", "source_subsection": "Sec1"},
            'entity_id_args': ["arg1"]
        }

        # 2. 调用被测试的函数，现在它返回 entity_uri
        # 2. Call the function under test, it now returns entity_uri
        returned_entity_uri = add_entity(entity_data_input, mock_conn_manager)

        # 3. 断言
        # 3. Assertions
        
        # 验证 add_entity 返回的 URI
        # Verify the URI returned by add_entity
        self.assertEqual(returned_entity_uri, mock_entity_uri_from_formatter, "add_entity 应返回从 formatter 获取的 URI。")
                                                                                # "add_entity should return the URI obtained from the formatter."

        # 构造 prepare_entity_sparql_insert 期望接收的 entity_properties 参数
        # Construct the expected entity_properties argument for prepare_entity_sparql_insert
        expected_properties_for_formatter: Dict[str, Union[str, List[str]]] = {
            'tcm-onto:hasTaste': ['甘', '微苦'], # 值被收集到列表中
                                            # Values are collected into a list
            'rdfs:seeAlso': 'http://example.com/anotherHerb'
        }
        
        # 验证 prepare_entity_sparql_insert 是否被正确调用
        # Verify prepare_entity_sparql_insert was called correctly
        mock_prepare_entity_sparql.assert_called_once_with(
            entity_type_name="Herb",
            entity_label="测试草药",
            entity_properties=expected_properties_for_formatter, # 验证转换后的属性
                                                                # Verify transformed properties
            source_details=entity_data_input['source_details'],
            entity_id_args=["arg1"]
        )
        
        # 验证 SparqlExecutor 是否被正确实例化和使用 (与之前相同)
        # Verify SparqlExecutor was instantiated and used correctly (same as before)
        mock_SparqlExecutor_class.assert_called_once_with(mock_conn_manager)
        mock_executor_instance.begin_transaction.assert_called_once()
        mock_executor_instance.execute_update.assert_called_once_with(dummy_sparql_query)
        mock_executor_instance.commit_transaction.assert_called_once()
        mock_executor_instance.rollback_transaction.assert_not_called()

    def test_add_entity_missing_required_fields(self):
        # 测试当 entity_data 缺少必要字段时是否抛出 ValueError (与之前相同)
        # Test if ValueError is raised when entity_data is missing required fields (same as before)
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        
        required_keys = ['entity_type_name', 'entity_label', 'source_details']
        # attributes_list 是可选的，在 add_entity 中有 .get(..., []) 处理
        # attributes_list is optional, handled by .get(..., []) in add_entity
        base_data = { 
            'entity_type_name': "Herb", 'entity_label': "Label", 
            'source_details': {"citation": "Cited"},
            'attributes_list': [] 
        }
        
        for key_to_remove in required_keys:
            faulty_data = base_data.copy()
            del faulty_data[key_to_remove]
            # 假设 add_entity 内部的错误信息与键名匹配
            # Assume error message inside add_entity matches the key name
            # 修正后的正则表达式以匹配 graph_operations.py 中实际的中文错误消息格式
            # Corrected regex to match the actual Chinese error message format in graph_operations.py
            expected_error_message = f"错误：entity_data 字典中缺少必需的键 '{key_to_remove}'。" # Updated to match actual error
            with self.assertRaisesRegex(ValueError, expected_error_message): # Using actual error message
                add_entity(faulty_data, mock_conn_manager)

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_entity_sparql_insert') # Keep for add_entity
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_relationship_sparql_insert') # Add for add_relationship
    def test_add_entity_execution_fails_then_rolls_back(self, mock_prepare_relationship_sparql, mock_prepare_entity_sparql, mock_SparqlExecutor_class): # Add new mock
        # 测试当 SPARQL 执行失败时，是否调用回滚并重新抛出异常 (与之前相同)
        # Test if rollback is called and exception is re-raised when SPARQL execution fails (same as before)
        
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        # prepare_entity_sparql_insert 现在返回 (query, entity_uri)
        # prepare_entity_sparql_insert now returns (query, entity_uri)
        mock_prepare_entity_sparql.return_value = ("SOME SPARQL QUERY", "http://example.com/entity/dummy") # For add_entity call

        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance
        
        simulated_db_error = Exception("Simulated DB error during execute_update")
        mock_executor_instance.execute_update.side_effect = simulated_db_error
        
        entity_data_input = { 
            'entity_type_name': "Herb", 'entity_label': "Failing Herb",
            'attributes_list': [], # 提供 attributes_list 以免因此出错
                                 # Provide attributes_list to avoid error from that
            'source_details': {"citation": "Source", "original_text": "...", 
                               "document_identifier": "DocFail", "source_type": "Test",
                               "source_section": "S", "source_subsection": "SS"}
        }

        with self.assertRaises(Exception) as context:
            add_entity(entity_data_input, mock_conn_manager)
        
        self.assertIs(context.exception, simulated_db_error)

        mock_executor_instance.begin_transaction.assert_called_once()
        mock_executor_instance.execute_update.assert_called_once() 
        mock_executor_instance.commit_transaction.assert_not_called() 
        mock_executor_instance.rollback_transaction.assert_called_once()

    # --- Tests for add_relationship ---

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_relationship_sparql_insert')
    def test_add_relationship_successful(self, mock_prepare_relationship_sparql, mock_SparqlExecutor_class):
        # Test successful execution of add_relationship
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        
        dummy_sparql_query = "INSERT DATA { <http://s1> <http://p1> <http://o1> . }"
        mock_prepare_relationship_sparql.return_value = dummy_sparql_query
        
        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance

        relationship_data_input = {
            'subject_uri': "http://example.com/subject/ent1",
            'predicate': "tcm-onto:hasSymptom",
            'object_uri': "http://example.com/object/sym1",
            'source_details': {"citation": "Rel Book", "original_text": "Rel Text...", 
                               "document_identifier": "BookRel1", "source_type": "Book",
                               "source_section": "ChRel1", "source_subsection": "SecRel1"}
        }

        add_relationship(relationship_data_input, mock_conn_manager)

        mock_prepare_relationship_sparql.assert_called_once_with(
            subject_uri=relationship_data_input['subject_uri'],
            predicate_curie=relationship_data_input['predicate'],
            object_uri=relationship_data_input['object_uri'],
            source_details=relationship_data_input['source_details']
        )
        
        mock_SparqlExecutor_class.assert_called_once_with(mock_conn_manager)
        mock_executor_instance.begin_transaction.assert_called_once()
        mock_executor_instance.execute_update.assert_called_once_with(dummy_sparql_query)
        mock_executor_instance.commit_transaction.assert_called_once()
        mock_executor_instance.rollback_transaction.assert_not_called()

    def test_add_relationship_missing_required_fields(self):
        # Test ValueError for missing required fields in relationship_data
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        required_keys = ['subject_uri', 'predicate', 'object_uri', 'source_details']
        base_data = {
            'subject_uri': "http://example.com/s",
            'predicate': "pred",
            'object_uri': "http://example.com/o",
            'source_details': {"citation": "CitedRel"}
        }
        
        for key_to_remove in required_keys:
            faulty_data = base_data.copy()
            del faulty_data[key_to_remove]
            expected_error_message = f"Error: Missing required key '{key_to_remove}' in relationship_data dictionary."
            with self.assertRaisesRegex(ValueError, expected_error_message):
                add_relationship(faulty_data, mock_conn_manager)

    def test_add_relationship_incorrect_data_types(self):
        # Test ValueError for incorrect data types in relationship_data
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        base_data = {
            'subject_uri': "http://example.com/s",
            'predicate': "pred",
            'object_uri': "http://example.com/o",
            'source_details': {"citation": "CitedRel"}
        }

        test_cases = [
            ('subject_uri', 123, "Error: 'subject_uri' should be a string, but got <class 'int'>."),
            ('predicate', True, "Error: 'predicate' should be a string (CURIE), but got <class 'bool'>."),
            ('object_uri', [], "Error: 'object_uri' should be a string, but got <class 'list'>."),
            ('source_details', "not a dict", "Error: 'source_details' should be a dictionary, but got <class 'str'>."),
        ]

        for key, wrong_value, error_msg in test_cases:
            faulty_data = base_data.copy()
            faulty_data[key] = wrong_value
            with self.assertRaisesRegex(ValueError, error_msg):
                add_relationship(faulty_data, mock_conn_manager)

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_relationship_sparql_insert')
    def test_add_relationship_prepare_sparql_fails(self, mock_prepare_relationship_sparql, mock_SparqlExecutor_class):
        # Test rollback and re-raise if prepare_relationship_sparql_insert fails
        # Note: In the current design, prepare_relationship_sparql_insert is less likely to cause
        # an exception that SparqlExecutor would need to roll back, as it mainly does string formatting.
        # However, this test ensures that if it *did* raise an error before transaction began,
        # the core function would propagate it. For errors *during* transaction, see next test.
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        
        simulated_prepare_error = ValueError("Simulated error during SPARQL preparation")
        mock_prepare_relationship_sparql.side_effect = simulated_prepare_error

        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance
        
        relationship_data_input = {
            'subject_uri': "http://example.com/s_fail_prepare",
            'predicate': "pred_fail_prepare",
            'object_uri': "http://example.com/o_fail_prepare",
            'source_details': {"citation": "CitedRelFailPrepare"}
        }

        with self.assertRaises(ValueError) as context:
            add_relationship(relationship_data_input, mock_conn_manager)
        
        self.assertIs(context.exception, simulated_prepare_error)
        # Transaction should not have started if preparation fails
        mock_executor_instance.begin_transaction.assert_not_called()
        mock_executor_instance.rollback_transaction.assert_not_called() # No transaction to roll back

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_relationship_sparql_insert')
    def test_add_relationship_execution_fails_then_rolls_back(self, mock_prepare_relationship_sparql, mock_SparqlExecutor_class):
        # Test rollback and re-raise if executor.execute_update fails
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        mock_prepare_relationship_sparql.return_value = "SOME RELATIONSHIP SPARQL QUERY"

        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance
        
        simulated_db_error = Exception("Simulated DB error during relationship execute_update")
        mock_executor_instance.execute_update.side_effect = simulated_db_error
        
        relationship_data_input = {
            'subject_uri': "http://example.com/s_fail_exec",
            'predicate': "pred_fail_exec",
            'object_uri': "http://example.com/o_fail_exec",
            'source_details': {"citation": "CitedRelFailExec"}
        }

        with self.assertRaises(Exception) as context:
            add_relationship(relationship_data_input, mock_conn_manager)
        
        self.assertIs(context.exception, simulated_db_error)

        mock_executor_instance.begin_transaction.assert_called_once()
        mock_executor_instance.execute_update.assert_called_once() 
        mock_executor_instance.commit_transaction.assert_not_called() 
        mock_executor_instance.rollback_transaction.assert_called_once()


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
