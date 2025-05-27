# tcm_kg_virtuoso_module/tests/core/test_graph_operations.py
import unittest
from unittest.mock import patch, MagicMock, ANY # ANY for some arguments if needed

# Function to be tested
from tcm_kg_virtuoso_module.core.graph_operations import add_entity
# For type hinting VirtuosoConnectionManager if needed by mocks, though not strictly necessary
from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager 

class TestGraphOperations(unittest.TestCase):

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_entity_sparql_insert')
    def test_add_entity_successful(self, mock_prepare_sparql, mock_SparqlExecutor_class):
        # 测试 add_entity 函数成功执行的情况
        
        # 1. 准备 mock 对象和输入数据
        # 1. Prepare mock objects and input data
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        
        dummy_sparql_query = "INSERT DATA { <http://s> <http://p> <http://o> . }"
        mock_prepare_sparql.return_value = dummy_sparql_query
        
        # 配置 SparqlExecutor 的 mock 实例
        # Configure the mock instance of SparqlExecutor
        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance

        entity_data_input = {
            'entity_type_name': "Herb",
            'entity_label': "测试草药",
            'entity_properties': {"tcm-onto:color": "绿色"},
            'source_details': {"citation": "Some Book", "original_text": "Text...", 
                               "document_identifier": "Book1", "source_type": "Book",
                               "source_section": "Ch1", "source_subsection": "Sec1"},
            'entity_id_args': ["arg1"]
        }

        # 2. 调用被测试的函数
        # 2. Call the function under test
        add_entity(entity_data_input, mock_conn_manager)

        # 3. 断言
        # 3. Assertions
        #    验证 prepare_entity_sparql_insert 是否被正确调用
        #    Verify prepare_entity_sparql_insert was called correctly
        mock_prepare_sparql.assert_called_once_with(
            entity_type_name="Herb",
            entity_label="测试草药",
            entity_properties={"tcm-onto:color": "绿色"},
            source_details=entity_data_input['source_details'],
            entity_id_args=["arg1"]
        )
        
        #    验证 SparqlExecutor 是否被正确实例化和使用
        #    Verify SparqlExecutor was instantiated and used correctly
        mock_SparqlExecutor_class.assert_called_once_with(mock_conn_manager)
        mock_executor_instance.begin_transaction.assert_called_once()
        mock_executor_instance.execute_update.assert_called_once_with(dummy_sparql_query)
        mock_executor_instance.commit_transaction.assert_called_once()
        mock_executor_instance.rollback_transaction.assert_not_called() # 不应调用回滚
                                                                        # Rollback should not be called

    def test_add_entity_missing_required_fields(self):
        # 测试当 entity_data 缺少必要字段时是否抛出 ValueError
        # Test if ValueError is raised when entity_data is missing required fields
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        
        required_keys = ['entity_type_name', 'entity_label', 'source_details']
        base_data = {
            'entity_type_name': "Herb", 'entity_label': "Label", 
            'source_details': {"citation": "Cited", "original_text": "Text...", 
                               "document_identifier": "Book1", "source_type": "Book",
                               "source_section": "Ch1", "source_subsection": "Sec1"} # 确保 source_details 完整
        }
        
        for key_to_remove in required_keys:
            faulty_data = base_data.copy()
            # 如果要移除的是 source_details，则整个键移除
            # If source_details is to be removed, remove the entire key
            if key_to_remove == 'source_details':
                del faulty_data[key_to_remove]
            else:
                # 否则，移除特定键
                # Otherwise, remove the specific key
                temp_data = base_data.copy()
                del temp_data[key_to_remove]
                faulty_data = temp_data # 更新 faulty_data

            # 修正后的正则表达式以匹配 graph_operations.py 中实际的中文错误消息格式
            # Corrected regex to match the actual Chinese error message format in graph_operations.py
            expected_error_message = f"错误：entity_data 字典中缺少必需的键 '{key_to_remove}'。"
            with self.assertRaisesRegex(ValueError, expected_error_message):
                add_entity(faulty_data, mock_conn_manager)

    @patch('tcm_kg_virtuoso_module.core.graph_operations.SparqlExecutor')
    @patch('tcm_kg_virtuoso_module.core.graph_operations.prepare_entity_sparql_insert')
    def test_add_entity_execution_fails_then_rolls_back(self, mock_prepare_sparql, mock_SparqlExecutor_class):
        # 测试当 SPARQL 执行失败时，是否调用回滚并重新抛出异常
        # Test if rollback is called and exception is re-raised when SPARQL execution fails
        
        mock_conn_manager = MagicMock(spec=VirtuosoConnectionManager)
        mock_prepare_sparql.return_value = "SOME SPARQL QUERY" # 内容不重要
                                                              # Content doesn't matter

        mock_executor_instance = MagicMock()
        mock_SparqlExecutor_class.return_value = mock_executor_instance
        
        # 配置 execute_update 抛出异常
        # Configure execute_update to raise an exception
        simulated_db_error = Exception("Simulated DB error during execute_update")
        mock_executor_instance.execute_update.side_effect = simulated_db_error
        
        entity_data_input = { # 提供完整的 entity_data 以通过初始校验
                            # Provide complete entity_data to pass initial checks
            'entity_type_name': "Herb", 'entity_label': "Failing Herb",
            'source_details': {"citation": "Source", "original_text": "...", 
                               "document_identifier": "DocFail", "source_type": "Test",
                               "source_section": "S", "source_subsection": "SS"}
        }

        # 断言原始异常被重新抛出
        # Assert that the original exception is re-raised
        with self.assertRaises(Exception) as context:
            add_entity(entity_data_input, mock_conn_manager)
        
        self.assertIs(context.exception, simulated_db_error, "应重新抛出数据库执行错误")
                                                              # "Should re-raise the database execution error"

        # 验证事务方法调用
        # Verify transaction method calls
        mock_executor_instance.begin_transaction.assert_called_once()
        mock_executor_instance.execute_update.assert_called_once() # 尝试执行
                                                                  # Attempted execution
        mock_executor_instance.commit_transaction.assert_not_called() # 不应提交
                                                                     # Should not commit
        mock_executor_instance.rollback_transaction.assert_called_once() # 应调用回滚
                                                                        # Should call rollback

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
