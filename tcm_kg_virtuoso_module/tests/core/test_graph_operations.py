# tcm_kg_virtuoso_module/tests/core/test_graph_operations.py
import unittest
from unittest.mock import patch, MagicMock, ANY # ANY can be useful for complex dicts

# Functions to be tested
from tcm_kg_virtuoso_module.core.graph_operations import add_entity, add_relationship, update_entity # update_entity 新增导入
# For type hinting VirtuosoConnectionManager if needed
from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager
# To help construct expected dictionaries for assertion / Optional for update_entity
from typing import Dict, List, Union, Optional, Any 

class TestGraphOperations(unittest.TestCase):

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_entity_sparql_insert') # Keep for add_entity tests
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_relationship_sparql_insert') # Add for add_relationship tests
    # Patches for update_entity tests will be added specifically to its test methods
    def test_add_entity_successful_and_transforms_attributes(self, mock_prepare_relationship_sparql_unused, mock_prepare_entity_sparql, mock_SparqlExecutor_class): # Renamed unused mock
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
    def test_add_entity_execution_fails_then_rolls_back(self, mock_prepare_relationship_sparql_unused, mock_prepare_entity_sparql, mock_SparqlExecutor_class): # Renamed unused mock
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

    # --- 测试 update_entity 函数 ---
    # --- Tests for update_entity function ---
    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_delete')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_correction')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_supersede')
    def test_update_entity_only_delete(self, mock_prepare_supersede, mock_prepare_correction, mock_prepare_delete, mock_SparqlExecutor_class):
        """测试 update_entity：仅执行删除属性操作 (Test update_entity: only delete attributes)"""
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance
        
        entity_uri = "http://example.com/entity/ent1"
        attrs_to_delete = [{"property": "tcm-onto:oldProp", "value": "old_value"}]
        
        # 模拟 prepare_sparql_for_attribute_delete 返回的查询
        # Mock queries returned by prepare_sparql_for_attribute_delete
        mock_delete_queries = ["DELETE_QUERY_1;"]
        mock_prepare_delete.return_value = mock_delete_queries

        update_entity(
            entity_uri=entity_uri,
            attributes_to_delete=attrs_to_delete,
            conn_manager=mock_conn_manager
        )

        mock_prepare_delete.assert_called_once_with(entity_uri, attrs_to_delete)
        mock_prepare_supersede.assert_not_called()
        mock_prepare_correction.assert_not_called()
        
        mock_executor_instance.begin_transaction.assert_called_once()
        mock_executor_instance.execute_update.assert_called_once_with(mock_delete_queries[0])
        mock_executor_instance.commit_transaction.assert_called_once()
        mock_executor_instance.rollback_transaction.assert_not_called()

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_delete')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_correction')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_supersede')
    def test_update_entity_scenario1_only_supersede(self, mock_prepare_supersede, mock_prepare_correction, mock_prepare_delete, mock_SparqlExecutor_class):
        """测试 update_entity：仅执行Scenario 1（替换/添加属性） (Test update_entity: only Scenario 1 - supersede/add attributes)"""
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance

        entity_uri = "http://example.com/entity/ent2"
        attrs_to_add_update = [{"property": "tcm-onto:newProp", "value": "new_value"}]
        source_info_input = {"citation": "Source for newProp"}

        mock_supersede_queries = ["SUPERSEDE_QUERY_1;", "SUPERSEDE_QUERY_2;"]
        mock_prepare_supersede.return_value = mock_supersede_queries

        update_entity(
            entity_uri=entity_uri,
            attributes_to_add_or_update=attrs_to_add_update,
            source_info=source_info_input,
            conn_manager=mock_conn_manager
        )

        mock_prepare_supersede.assert_called_once_with(entity_uri, attrs_to_add_update, source_info_input)
        mock_prepare_delete.assert_not_called()
        mock_prepare_correction.assert_not_called()

        mock_executor_instance.begin_transaction.assert_called_once()
        self.assertEqual(mock_executor_instance.execute_update.call_count, 2)
        mock_executor_instance.execute_update.assert_any_call(mock_supersede_queries[0])
        mock_executor_instance.execute_update.assert_any_call(mock_supersede_queries[1])
        mock_executor_instance.commit_transaction.assert_called_once()

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_delete')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_correction')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_supersede')
    def test_update_entity_scenario2_only_correction(self, mock_prepare_supersede, mock_prepare_correction, mock_prepare_delete, mock_SparqlExecutor_class):
        """测试 update_entity：仅执行Scenario 2（修正属性） (Test update_entity: only Scenario 2 - correct attribute)"""
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance

        entity_uri = "http://example.com/entity/ent3"
        prop_to_correct = "tcm-onto:description"
        attrs_to_add_update = [{"property": prop_to_correct, "value": "corrected_description", "datatype": "xsd:string"}]
        source_info_input = {"citation": "Source for correction"}
        correction_details_input = {"property_to_correct": prop_to_correct, "targetNamedGraphUri": "http://example.com/graph/original_graph"}

        mock_correction_queries = ["CORRECTION_QUERY_1;", "CORRECTION_QUERY_2;"]
        mock_prepare_correction.return_value = mock_correction_queries

        update_entity(
            entity_uri=entity_uri,
            attributes_to_add_or_update=attrs_to_add_update,
            source_info=source_info_input,
            correction_details_info=correction_details_input,
            conn_manager=mock_conn_manager
        )

        mock_prepare_correction.assert_called_once_with(
            entity_uri=entity_uri,
            property_to_correct_curie=prop_to_correct,
            new_value="corrected_description",
            new_value_datatype="xsd:string",
            target_graph_uri="http://example.com/graph/original_graph",
            source_details=source_info_input
        )
        mock_prepare_supersede.assert_not_called()
        mock_prepare_delete.assert_not_called()
        
        self.assertEqual(mock_executor_instance.execute_update.call_count, 2)

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_delete')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_correction')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_supersede')
    def test_update_entity_mixed_scenario(self, mock_prepare_supersede, mock_prepare_correction, mock_prepare_delete, mock_SparqlExecutor_class):
        """测试 update_entity：混合场景（修正、替换和删除） (Test update_entity: mixed scenario - correction, supersede, delete)"""
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance

        entity_uri = "http://example.com/entity/ent_mixed"
        prop_for_correction = "tcm-onto:note"
        attrs_to_add_update = [
            {"property": prop_for_correction, "value": "corrected note"}, # 用于修正
            {"property": "tcm-onto:newFeature", "value": "feature_value"}  # 用于替换/添加
        ]
        attrs_to_delete = [{"property": "tcm-onto:toBeDeleted"}]
        source_info_input = {"citation": "Mixed op source"}
        correction_details_input = {"property_to_correct": prop_for_correction, "targetNamedGraphUri": "http://example.com/graph/g_mixed"}

        mock_delete_q = ["DELETE_MIXED;"]
        mock_correction_q = ["CORRECT_MIXED;"]
        mock_supersede_q = ["SUPERSEDE_MIXED;"]
        mock_prepare_delete.return_value = mock_delete_q
        mock_prepare_correction.return_value = mock_correction_q
        mock_prepare_supersede.return_value = mock_supersede_q

        update_entity(
            entity_uri=entity_uri,
            attributes_to_add_or_update=attrs_to_add_update,
            attributes_to_delete=attrs_to_delete,
            source_info=source_info_input,
            correction_details_info=correction_details_input,
            conn_manager=mock_conn_manager
        )
        
        mock_prepare_delete.assert_called_once_with(entity_uri, attrs_to_delete)
        mock_prepare_correction.assert_called_once_with(
            entity_uri=entity_uri,
            property_to_correct_curie=prop_for_correction,
            new_value="corrected note", new_value_datatype=None, # 从 attrs_to_add_update[0] 获取
            target_graph_uri="http://example.com/graph/g_mixed",
            source_details=source_info_input
        )
        # 验证传递给 supersede 的列表只包含未被修正的属性
        # Verify the list passed to supersede only contains the non-corrected attribute
        mock_prepare_supersede.assert_called_once_with(
            entity_uri, 
            [{"property": "tcm-onto:newFeature", "value": "feature_value"}], # 仅包含第二个属性
            source_info_input
        )

        expected_query_order = mock_delete_q + mock_correction_q + mock_supersede_q
        self.assertEqual(mock_executor_instance.execute_update.call_count, len(expected_query_order))
        for i, query in enumerate(expected_query_order):
            self.assertEqual(mock_executor_instance.execute_update.call_args_list[i][0][0], query)
        
        mock_executor_instance.commit_transaction.assert_called_once()

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    def test_update_entity_transaction_rollback(self, mock_SparqlExecutor_class):
        """测试 update_entity：当 execute_update 失败时事务回滚 (Test update_entity: transaction rollback on execute_update failure)"""
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance
        
        # 模拟 execute_update 抛出异常
        # Mock execute_update to raise an exception
        db_error = Exception("数据库更新失败")
        mock_executor_instance.execute_update.side_effect = db_error

        # 使用一个简单的删除操作来触发执行
        # Use a simple delete operation to trigger execution
        with patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_sparql_for_attribute_delete') as mock_prepare_delete:
            mock_prepare_delete.return_value = ["SOME_DELETE_QUERY;"]
            
            with self.assertRaises(Exception) as context:
                update_entity(
                    entity_uri="http://example.com/entity/fail_ent",
                    attributes_to_delete=[{"property": "p"}],
                    conn_manager=mock_conn_manager
                )
            self.assertIs(context.exception, db_error) # 确保原始异常被重新抛出
                                                       # Ensure original exception is re-raised

        mock_executor_instance.begin_transaction.assert_called_once()
        mock_executor_instance.execute_update.assert_called_once() # 因为它在第一个查询就失败了
                                                                   # Because it failed on the first query
        mock_executor_instance.commit_transaction.assert_not_called()
        mock_executor_instance.rollback_transaction.assert_called_once()

    def test_update_entity_value_errors(self):
        """测试 update_entity：特定 ValueError 条件 (Test update_entity: specific ValueError conditions)"""
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        entity_uri = "http://example.com/entity/verr"

        # Scenario 1 缺少 source_info
        # Scenario 1 missing source_info
        with self.assertRaisesRegex(ValueError, "错误：属性添加/更新操作 \(Scenario 1\) 需要 'source_info' 来创建新的命名图。"):
            update_entity(
                entity_uri=entity_uri,
                attributes_to_add_or_update=[{"property": "p1", "value": "v1"}],
                conn_manager=mock_conn_manager
                # source_info is missing
            )

        # Scenario 2 缺少 source_info
        # Scenario 2 missing source_info
        with self.assertRaisesRegex(ValueError, "错误：修正操作 \(Scenario 2\) 需要提供 'source_info' 以记录修正的来源。"):
            update_entity(
                entity_uri=entity_uri,
                attributes_to_add_or_update=[{"property": "p_correct", "value": "v_correct"}],
                correction_details_info={"property_to_correct": "p_correct", "targetNamedGraphUri": "http://g"},
                conn_manager=mock_conn_manager
                # source_info is missing
            )
        
        # Scenario 2, correction_details 中指定的属性在 attributes_to_add_or_update 中未找到
        # Scenario 2, property specified in correction_details not found in attributes_to_add_or_update
        prop_to_correct_missing = "p_correct_not_found"
        expected_msg_regex = (
            f"错误：修正操作指定了属性 '{prop_to_correct_missing}'，"
            f"但在 'attributes_to_add_or_update' 列表中未找到该属性的新值。"
        )
        with self.assertRaisesRegex(ValueError, expected_msg_regex):
            update_entity(
                entity_uri=entity_uri,
                attributes_to_add_or_update=[{"property": "p_other", "value": "v_other"}], # 不包含 p_correct_not_found
                source_info={"citation": "s"},
                correction_details_info={"property_to_correct": prop_to_correct_missing, "targetNamedGraphUri": "http://g"},
                conn_manager=mock_conn_manager
            )
            
    def test_update_entity_no_operations(self):
        """测试 update_entity：当没有提供任何操作时，函数应直接返回 (Test update_entity: no operations provided, should return early)"""
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        mock_executor_instance = MagicMock()
        
        # 模拟 SparqlExecutor 类，使其返回我们自定义的 mock_executor_instance
        # Mock SparqlExecutor class to return our custom mock_executor_instance
        with patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor', return_value=mock_executor_instance):
            update_entity(
                entity_uri="http://example.com/entity/no_ops",
                conn_manager=mock_conn_manager
                # attributes_to_add_or_update, attributes_to_delete, source_info, correction_details_info 均未提供
                # All optional parameters are None
            )
        
        mock_executor_instance.begin_transaction.assert_not_called()
        mock_executor_instance.execute_update.assert_not_called()
        mock_executor_instance.commit_transaction.assert_not_called()
        # 验证是否打印了相应的日志信息 (需要 patch print)
        # Verify if corresponding log message was printed (requires patching print)
        with patch('builtins.print') as mock_print:
            update_entity(
                entity_uri="http://example.com/entity/no_ops2",
                conn_manager=mock_conn_manager
            )
            mock_print.assert_any_call("信息：实体 <http://example.com/entity/no_ops2> 无更新操作需要执行。")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
