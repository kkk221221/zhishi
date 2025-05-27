import unittest
from unittest.mock import MagicMock, patch

# 动态导入被测试的类
# Dynamically import the class under test
from tcm_kg_virtuoso_module.core.sparql_executor import SparqlExecutor
# VirtuosoConnectionManager 也会被 mock，所以这里可以不用真的导入
# VirtuosoConnectionManager will also be mocked, so no need to actually import it here

class TestSparqlExecutor(unittest.TestCase):

    def setUp(self):
        # 创建 VirtuosoConnectionManager 的 mock 实例
        # Create a mock instance of VirtuosoConnectionManager
        self.mock_connection_manager = MagicMock()
        
        # 配置 get_connection 方法返回一个 mock 连接对象
        # Configure the get_connection method to return a mock connection object
        self.mock_db_connection = MagicMock()
        # __str__ is used in f-string formatting in SparqlExecutor print statements
        self.mock_db_connection.__str__ = MagicMock(return_value="MockDBConnection")
        self.mock_connection_manager.get_connection.return_value = self.mock_db_connection

        # 创建 SparqlExecutor 实例，传入 mock 的连接管理器
        # Create a SparqlExecutor instance, passing in the mocked connection manager
        self.executor = SparqlExecutor(self.mock_connection_manager)

    def test_initialization(self):
        # 测试初始化是否正确存储了连接管理器
        # Test if initialization correctly stored the connection manager
        self.assertIs(self.executor.connection_manager, self.mock_connection_manager)
        self.assertIsNone(self.executor.connection) # 初始内部连接应为 None
                                                    # Initial internal connection should be None

    def test_get_db_connection_success(self):
        # 测试成功获取数据库连接
        # Test successfully getting a database connection
        conn = self.executor._get_db_connection()
        self.mock_connection_manager.get_connection.assert_called_once()
        self.assertIs(conn, self.mock_db_connection)
        self.assertIs(self.executor.connection, self.mock_db_connection) # 内部连接已设置
                                                                        # Internal connection is set

    def test_get_db_connection_failure(self):
        # 测试获取数据库连接失败的情况
        # Test scenario where getting a database connection fails
        self.mock_connection_manager.get_connection.return_value = None # 模拟连接失败
                                                                      # Simulate connection failure
        with self.assertRaisesRegex(Exception, "Failed to establish database connection via ConnectionManager"):
            self.executor._get_db_connection()
        self.mock_connection_manager.get_connection.assert_called_once()

    @patch('builtins.print') # 假设执行方法中有打印语句
                             # Assume there are print statements in execution methods
    def test_execute_select(self, mock_print):
        # 测试执行 SELECT 查询
        # Test executing a SELECT query
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        # 模拟数据库连接的 execute 方法返回一些模拟数据
        # Simulate the database connection's execute method returning some mock data
        # (当前实现是打印并返回空列表，所以我们检查打印)
        # (The current implementation prints and returns an empty list, so we check the print)
        
        result = self.executor.execute_select(query)
        
        self.mock_connection_manager.get_connection.assert_called_once() # 确保获取了连接
                                                                        # Ensure connection was obtained
        # 检查打印输出是否包含查询语句 (根据 SparqlExecutor 的模拟实现)
        # Check if print output contains the query statement (based on SparqlExecutor's simulated implementation)
        mock_print.assert_any_call(f"Executing SELECT query on {self.mock_db_connection}:\n{query}")
        self.assertEqual(result, []) # 应返回模拟的空列表
                                     # Should return the simulated empty list

    @patch('builtins.print')
    def test_execute_insert(self, mock_print):
        # 测试执行 INSERT 查询
        # Test executing an INSERT query
        query = "INSERT DATA { <uri:s> <uri:p> <uri:o> }"
        self.executor.execute_insert(query)
        self.mock_connection_manager.get_connection.assert_called_once()
        mock_print.assert_any_call(f"Executing INSERT query on {self.mock_db_connection}:\n{query}")

    @patch('builtins.print')
    def test_execute_delete(self, mock_print):
        # 测试执行 DELETE 查询
        # Test executing a DELETE query
        query = "DELETE DATA { <uri:s> <uri:p> <uri:o> }"
        self.executor.execute_delete(query)
        self.mock_connection_manager.get_connection.assert_called_once()
        mock_print.assert_any_call(f"Executing DELETE query on {self.mock_db_connection}:\n{query}")

    @patch('builtins.print')
    def test_execute_update(self, mock_print):
        # 测试执行 UPDATE 查询
        # Test executing an UPDATE query
        query = "DELETE { ?s ?p ?o } INSERT { ?s ?p ?new_o }"
        self.executor.execute_update(query)
        self.mock_connection_manager.get_connection.assert_called_once()
        mock_print.assert_any_call(f"Executing UPDATE (DELETE/INSERT) query on {self.mock_db_connection}:\n{query}")

    @patch('builtins.print')
    def test_begin_transaction(self, mock_print):
        # 测试开始事务
        # Test beginning a transaction
        self.executor.begin_transaction()
        self.mock_connection_manager.get_connection.assert_called_once()
        # 检查模拟的事务开始打印
        # Check the simulated transaction begin print
        mock_print.assert_any_call(f"Beginning transaction on {self.mock_db_connection} (simulated).")
        # 如果实际实现中 self.mock_db_connection 有 begin() 方法，则用:
        # If the actual implementation has a begin() method on self.mock_db_connection, use:
        # self.mock_db_connection.begin.assert_called_once()

    @patch('builtins.print')
    def test_commit_transaction(self, mock_print):
        # 测试提交事务
        # Test committing a transaction
        self.executor.commit_transaction()
        self.mock_connection_manager.get_connection.assert_called_once()
        mock_print.assert_any_call(f"Committing transaction on {self.mock_db_connection} (simulated).")
        # self.mock_db_connection.commit.assert_called_once()

    @patch('builtins.print')
    def test_rollback_transaction(self, mock_print):
        # 测试回滚事务
        # Test rolling back a transaction
        self.executor.rollback_transaction()
        self.mock_connection_manager.get_connection.assert_called_once()
        mock_print.assert_any_call(f"Rolling back transaction on {self.mock_db_connection} (simulated).")
        # self.mock_db_connection.rollback.assert_called_once()

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
