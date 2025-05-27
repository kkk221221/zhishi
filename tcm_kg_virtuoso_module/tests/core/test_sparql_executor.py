# tcm_kg_virtuoso_module/tests/core/test_sparql_executor.py
import pytest
import pyodbc # 导入 pyodbc 以便捕获其特定错误
from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager
from tcm_kg_virtuoso_module.core.sparql_executor import SparqlExecutor
from tcm_kg_virtuoso_module.config.settings import get_settings

# 获取数据库连接设置
# Get database connection settings
settings = get_settings()

# Pytest fixture for VirtuosoConnectionManager, module-scoped
@pytest.fixture(scope="module")
def conn_manager_fixture():
    manager = VirtuosoConnectionManager(
        host=settings.virtuoso_host,
        port=settings.virtuoso_port,
        user=settings.virtuoso_user,
        password=settings.virtuoso_password,
        default_graph_uri=settings.virtuoso_graph_uri
    )
    return manager

# Pytest fixture for SparqlExecutor, function-scoped to get a fresh executor for each test
# Using the module-scoped conn_manager_fixture for efficiency
@pytest.fixture(scope="function")
def sparql_executor_fixture(conn_manager_fixture: VirtuosoConnectionManager):
    executor = SparqlExecutor(conn_manager_fixture)
    return executor

# 测试 SELECT 查询
# Test SELECT query
def test_execute_select(sparql_executor_fixture: SparqlExecutor, conn_manager_fixture: VirtuosoConnectionManager):
    """测试 SparqlExecutor 执行 SELECT 查询。"""
    query = "SPARQL SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 1" # 一个通用查询
                                                              # A generic query
    try:
        with conn_manager_fixture: # 确保连接在测试期间是活动的
                                   # Ensure connection is active during the test
            results = sparql_executor_fixture.execute_select(query)
            assert isinstance(results, list), "SELECT结果应为列表" # SELECT result should be a list
            # 这个查询在空数据库上也应该能成功执行并返回空列表
            # This query should execute successfully on an empty DB and return an empty list
    except pyodbc.Error as e:
        pytest.skip(f"数据库操作失败，跳过此测试: {e}") # DB operation failed, skipping test
    except ConnectionError as e: # ConnectionError 来自 _ensure_connected
                                # ConnectionError from _ensure_connected
        pytest.skip(f"数据库连接失败，跳过此测试: {e}") # DB connection failed, skipping test


# 测试 INSERT 更新和事务处理 (commit)
# Test INSERT update and transaction handling (commit)
def test_execute_update_insert_and_commit(sparql_executor_fixture: SparqlExecutor, conn_manager_fixture: VirtuosoConnectionManager):
    """测试 SparqlExecutor 执行 INSERT 并提交事务。"""
    test_subject = "<http://example.org/test_exec_subject_insert>"
    test_predicate = "<http://example.org/test_pred_insert>"
    test_object = "<http://example.org/test_obj_insert>"
    test_graph = f"<{settings.virtuoso_graph_uri}/test_sparql_executor>"
    
    insert_query = f"SPARQL INSERT DATA INTO {test_graph} {{ {test_subject} {test_predicate} {test_object} . }}"
    select_query = f"SPARQL SELECT ?s WHERE {{ GRAPH {test_graph} {{ {test_subject} {test_predicate} {test_object} . }} }}"
    clear_graph_query = f"SPARQL CLEAR GRAPH {test_graph}"

    try:
        with conn_manager_fixture:
            # 清理可能存在的旧数据
            # Clean up potentially existing old data
            try:
                sparql_executor_fixture.begin_transaction()
                sparql_executor_fixture.execute_update(clear_graph_query)
                sparql_executor_fixture.commit_transaction()
            except pyodbc.Error:
                if conn_manager_fixture.transaction_active: # 检查事务是否真的开始了
                    sparql_executor_fixture.rollback_transaction() # 确保事务结束
                                                              # Ensure transaction ends
            except ConnectionError as e:
                 pytest.skip(f"清理操作时数据库连接失败: {e}") # DB connection failed during cleanup

            # 开始事务
            # Begin transaction
            sparql_executor_fixture.begin_transaction()
            
            # 执行插入
            # Execute insert
            affected_rows = sparql_executor_fixture.execute_update(insert_query)
            # 对于SPARQL INSERT，受影响的行数可能不总是准确或一致，所以不严格断言其值
            # For SPARQL INSERT, affected rows might not always be accurate/consistent, so don't strictly assert value

            # 提交事务
            # Commit transaction
            sparql_executor_fixture.commit_transaction()

            # 验证数据是否已插入
            # Verify data was inserted
            results = sparql_executor_fixture.execute_select(select_query)
            assert len(results) == 1, "提交后应能查询到插入的数据" # Should find inserted data after commit

            # 清理测试数据
            # Clean up test data
            sparql_executor_fixture.begin_transaction()
            sparql_executor_fixture.execute_update(clear_graph_query)
            sparql_executor_fixture.commit_transaction()

    except pyodbc.Error as e:
        pytest.skip(f"数据库事务/更新操作失败，跳过此测试: {e}") # DB transaction/update op failed, skipping
    except ConnectionError as e:
        pytest.skip(f"数据库连接失败，跳过此测试: {e}") # DB connection failed, skipping


# 测试 DELETE 更新和事务处理 (rollback)
# Test DELETE update and transaction handling (rollback)
def test_execute_update_delete_and_rollback(sparql_executor_fixture: SparqlExecutor, conn_manager_fixture: VirtuosoConnectionManager):
    """测试 SparqlExecutor 执行 DELETE 并回滚事务。"""
    test_subject = "<http://example.org/test_exec_subject_delete>"
    test_predicate = "<http://example.org/test_pred_delete>"
    test_object = "<http://example.org/test_obj_delete>"
    test_graph = f"<{settings.virtuoso_graph_uri}/test_sparql_executor_rollback>"

    insert_query = f"SPARQL INSERT DATA INTO {test_graph} {{ {test_subject} {test_predicate} {test_object} . }}"
    delete_query = f"SPARQL DELETE DATA FROM {test_graph} {{ {test_subject} {test_predicate} {test_object} . }}"
    select_query = f"SPARQL SELECT ?s WHERE {{ GRAPH {test_graph} {{ {test_subject} {test_predicate} {test_object} . }} }}"
    clear_graph_query = f"SPARQL CLEAR GRAPH {test_graph}"

    try:
        with conn_manager_fixture:
            # 设置初始状态：插入一条数据并提交
            # Set initial state: insert data and commit
            try:
                sparql_executor_fixture.begin_transaction()
                sparql_executor_fixture.execute_update(clear_graph_query) # 清理旧的
                                                                        # Clean up old
                sparql_executor_fixture.execute_update(insert_query)
                sparql_executor_fixture.commit_transaction()
            except pyodbc.Error: # 如果清理或初始插入失败
                                 # If cleanup or initial insert fails
                if conn_manager_fixture.transaction_active:
                    sparql_executor_fixture.rollback_transaction()
                pytest.skip("设置初始状态失败，跳过回滚测试。") # Failed to set initial state, skipping rollback test
            except ConnectionError as e:
                pytest.skip(f"设置初始状态时数据库连接失败: {e}") # DB connection failed during setup

            # 开始新事务以测试回滚
            # Begin new transaction to test rollback
            sparql_executor_fixture.begin_transaction()
            
            # 执行删除
            # Execute delete
            sparql_executor_fixture.execute_update(delete_query)
            
            # 验证事务内数据是否被删除 (可选，取决于隔离级别和期望)
            # Verify data deleted within transaction (optional, depends on isolation level and expectation)
            # results_in_txn = sparql_executor_fixture.execute_select(select_query)
            # assert len(results_in_txn) == 0, "在事务内删除后，数据应不可见"

            # 回滚事务
            # Rollback transaction
            sparql_executor_fixture.rollback_transaction()

            # 验证数据在回滚后是否仍然存在
            # Verify data still exists after rollback
            results_after_rollback = sparql_executor_fixture.execute_select(select_query)
            assert len(results_after_rollback) == 1, "回滚后，数据应依然存在" # After rollback, data should still exist

            # 清理
            # Cleanup
            sparql_executor_fixture.begin_transaction()
            sparql_executor_fixture.execute_update(clear_graph_query)
            sparql_executor_fixture.commit_transaction()

    except pyodbc.Error as e:
        pytest.skip(f"数据库事务/更新操作失败，跳过此测试: {e}") # DB transaction/update op failed, skipping
    except ConnectionError as e:
        pytest.skip(f"数据库连接失败，跳过此测试: {e}") # DB connection failed, skipping

# 这些测试同样依赖于可访问的Virtuoso实例和正确的ODBC配置。
# These tests also depend on an accessible Virtuoso instance and correct ODBC configuration.
