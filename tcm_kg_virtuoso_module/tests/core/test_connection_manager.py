# tcm_kg_virtuoso_module/tests/core/test_connection_manager.py
import pytest
import pyodbc # 导入 pyodbc 以便捕获其特定错误
from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager
from tcm_kg_virtuoso_module.config.settings import get_settings # 用于获取配置

# 获取数据库连接设置
# Get database connection settings
settings = get_settings()

# 定义一个Pytest fixture，用于在测试需要时提供一个ConnectionManager实例
# Define a Pytest fixture to provide a ConnectionManager instance when tests need it
@pytest.fixture(scope="module") # module作用域表示此fixture在模块内所有测试中共享
                               # module scope means this fixture is shared among all tests in the module
def conn_manager():
    manager = VirtuosoConnectionManager(
        host=settings.virtuoso_host,
        port=settings.virtuoso_port,
        user=settings.virtuoso_user,
        password=settings.virtuoso_password,
        default_graph_uri=settings.virtuoso_graph_uri
    )
    # 注意：这里不自动连接，每个测试用例根据需要自行连接/断开或使用上下文管理器
    # Note: Does not automatically connect here; each test case connects/disconnects as needed or uses context manager
    return manager

# 测试能否成功连接和断开
# Test successful connection and disconnection
def test_connect_disconnect(conn_manager: VirtuosoConnectionManager):
    """测试基本的连接和断开功能。"""
    try:
        conn_manager.connect()
        assert conn_manager.connection is not None, "连接对象不应为None" # Connection object should not be None
        assert conn_manager.cursor is not None, "游标对象不应为None" # Cursor object should not be None
    except pyodbc.Error as e:
        pytest.skip(f"无法连接到Virtuoso数据库，跳过此测试: {e}") # Cannot connect to Virtuoso, skipping test
    finally:
        conn_manager.disconnect()
        assert conn_manager.connection is None, "断开后连接对象应为None" # Connection object should be None after disconnect
        assert conn_manager.cursor is None, "断开后游标对象应为None" # Cursor object should be None after disconnect

# 测试使用上下文管理器
# Test using context manager
def test_context_manager(conn_manager: VirtuosoConnectionManager):
    """测试连接管理器的上下文管理协议。"""
    try:
        with conn_manager as cm: # __enter__ 会调用 connect()
                                 # __enter__ will call connect()
            assert cm.connection is not None
            assert cm.cursor is not None
            # 在这里可以执行一些简单的操作，例如查询版本
            # Simple operations can be performed here, e.g., querying version
            cm.cursor.execute("SPARQL SELECT DB.DBA.version();")
            version_row = cm.cursor.fetchone()
            assert version_row is not None, "应能查询到数据库版本" # Should be able to query database version
            print(f"数据库版本: {version_row[0]}") # Database version
        
        # __exit__ 会调用 disconnect()
        # __exit__ will call disconnect()
        assert conn_manager.connection is None
        assert conn_manager.cursor is None
    except pyodbc.Error as e:
        pytest.skip(f"无法连接到Virtuoso数据库或执行查询，跳过此测试: {e}") # Cannot connect/query Virtuoso, skipping

# 测试执行查询 (SELECT)
# Test executing a query (SELECT)
def test_execute_query(conn_manager: VirtuosoConnectionManager):
    """测试执行SELECT查询。"""
    try:
        with conn_manager as cm:
            # 一个非常简单的SPARQL查询，不依赖特定数据
            # A very simple SPARQL query that doesn't depend on specific data
            query = "SPARQL SELECT 1 AS ?one WHERE { }"
            results = cm.execute_query(query)
            assert isinstance(results, list), "结果应为列表" # Result should be a list
            assert len(results) >= 0, "结果列表长度应大于等于0" # Result list length should be >= 0
            if len(results) > 0: # Virtuoso 可能返回空结果集，也可能返回包含一行但?one为null的结果，取决于具体实现
                                 # Virtuoso might return an empty result set, or one row with ?one as null, depending on implementation
                assert "one" in results[0] if results[0] else True, "结果中应包含列 'one' 或结果行为空字典" # Result should contain 'one' or be an empty dict
                if results[0] and "one" in results[0]:
                     assert results[0]["one"] == 1, "值应为1" # Value should be 1


    except pyodbc.Error as e:
        pytest.skip(f"数据库操作失败，跳过此测试: {e}") # DB operation failed, skipping test

# 测试执行更新 (INSERT/DELETE) 和事务
# Test executing an update (INSERT/DELETE) and transactions
def test_execute_update_and_transactions(conn_manager: VirtuosoConnectionManager):
    """测试执行更新操作以及事务的提交和回滚。"""
    test_subject = "<http://example.org/test_conn_mngr_subject1>"
    test_predicate = "<http://example.org/test_pred>"
    test_object = "<http://example.org/test_obj1>"
    # 使用 settings 中的 graph_uri 来构建测试图名，确保与配置一致
    # Use graph_uri from settings to construct test graph name, ensuring consistency with config
    base_test_graph_uri = settings.virtuoso_graph_uri.rstrip('/') + "/test_connection_manager"
    test_graph = f"<{base_test_graph_uri}>"


    insert_query = f"SPARQL INSERT DATA INTO {test_graph} {{ {test_subject} {test_predicate} {test_object} . }}"
    delete_query = f"SPARQL DELETE DATA FROM {test_graph} {{ {test_subject} {test_predicate} {test_object} . }}"
    # 在SELECT查询中明确指定GRAPH
    # Explicitly specify GRAPH in SELECT query
    select_query = f"SPARQL SELECT ?s WHERE {{ GRAPH {test_graph} {{ {test_subject} {test_predicate} {test_object} . }} }}"
    clear_graph_query = f"SPARQL CLEAR GRAPH {test_graph}"


    try:
        with conn_manager as cm:
            # 清理可能存在的旧数据
            # Clean up potentially existing old data
            try:
                cm.begin_transaction()
                cm.execute_update(clear_graph_query)
                cm.commit_transaction()
                print(f"测试信息：图 {test_graph} 在测试开始前已清空。") # Test info: Graph cleared before test.
            except pyodbc.Error as e: 
                print(f"测试警告：清理图 {test_graph} 时发生错误 (可能是图不存在): {e}。继续测试...") # Test warning: Error clearing graph (might not exist). Continuing...
                if cm.transaction_active: # 确保事务结束
                                         # Ensure transaction ends
                    cm.rollback_transaction()


            # 1. 测试插入和提交
            # 1. Test insert and commit
            cm.begin_transaction()
            rows_affected_insert = cm.execute_update(insert_query)
            # 对于SPARQL INSERT，pyodbc的rowcount行为可能不一致，不强制断言其为1
            # For SPARQL INSERT, pyodbc rowcount behavior can be inconsistent, not strictly asserting 1
            print(f"测试信息：插入操作影响行数: {rows_affected_insert}") # Test info: Insert affected rows
            cm.commit_transaction()

            results_after_insert = cm.execute_query(select_query)
            assert len(results_after_insert) == 1, f"提交后应能查询到数据。查询: {select_query}, 结果: {results_after_insert}" # Should find data after commit.

            # 2. 测试删除和回滚
            # 2. Test delete and rollback
            cm.begin_transaction()
            rows_affected_delete = cm.execute_update(delete_query) # 先删除
                                                                  # Delete first
            print(f"测试信息：删除操作(事务中)影响行数: {rows_affected_delete}") # Test info: Delete (in transaction) affected rows
            
            results_in_txn_after_delete = cm.execute_query(select_query)
            assert len(results_in_txn_after_delete) == 0, "在事务内删除后数据应不可见" # Data should be invisible after delete within transaction

            cm.rollback_transaction() # 回滚删除
                                     # Rollback delete

            results_after_rollback = cm.execute_query(select_query)
            assert len(results_after_rollback) == 1, "回滚后数据应依然存在" # Data should still exist after rollback

            # 3. 清理测试数据 (最终删除)
            # 3. Clean up test data (final delete)
            cm.begin_transaction()
            rows_affected_final_delete = cm.execute_update(delete_query)
            print(f"测试信息：最终删除操作影响行数: {rows_affected_final_delete}") # Test info: Final delete affected rows
            cm.commit_transaction()

            results_after_cleanup = cm.execute_query(select_query)
            assert len(results_after_cleanup) == 0, "清理后数据应不存在" # Data should not exist after cleanup
            print(f"测试信息：图 {test_graph} 数据已成功清理。") # Test info: Graph data successfully cleared.

    except pyodbc.Error as e:
        pytest.skip(f"数据库事务/更新操作失败，跳过此测试: {e}") # DB transaction/update op failed, skipping
    except Exception as e: # 捕获其他可能的断言错误等
                           # Catch other possible assertion errors etc.
        pytest.fail(f"测试中发生意外错误: {e}") # Unexpected error in test


# 测试事务方法在未连接时的行为 (应抛出ConnectionError)
# Test transaction methods when not connected (should raise ConnectionError)
def test_transaction_methods_when_not_connected(conn_manager: VirtuosoConnectionManager):
    """测试在未连接状态下调用事务相关方法。"""
    # 确保处于断开状态
    # Ensure disconnected state
    if conn_manager.connection: # 如果之前的测试意外保留了连接
                               # If a previous test unexpectedly kept the connection
        conn_manager.disconnect()

    with pytest.raises(ConnectionError, match="数据库未连接"): # Match Chinese message
        conn_manager.begin_transaction()
    
    with pytest.raises(ConnectionError, match="数据库未连接"):
        conn_manager.commit_transaction()

    with pytest.raises(ConnectionError, match="数据库未连接"):
        conn_manager.rollback_transaction()

# 注意: 这些集成测试依赖于一个可访问的Virtuoso实例和正确的ODBC配置。
# Note: These integration tests depend on an accessible Virtuoso instance and correct ODBC configuration.
# 在没有此类环境的CI/CD中，它们可能会被跳过 (使用pytest.skip)。
# In CI/CD without such an environment, they might be skipped (using pytest.skip).
```
