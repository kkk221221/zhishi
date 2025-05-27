# tcm_kg_virtuoso_module/core/sparql_executor.py
from typing import List, Dict, Any, Optional # Any 已添加
from .connection_manager import VirtuosoConnectionManager

class SparqlExecutor:
    """
    执行SPARQL查询和更新的执行器，使用VirtuosoConnectionManager。
    Executor for SPARQL queries and updates, using VirtuosoConnectionManager.
    """
    def __init__(self, connection_manager: VirtuosoConnectionManager):
        """
        初始化SparqlExecutor。

        参数:
        - connection_manager (VirtuosoConnectionManager): 用于数据库交互的连接管理器。
                                                        Connection manager for database interaction.
        """
        if not isinstance(connection_manager, VirtuosoConnectionManager):
            raise TypeError("错误：connection_manager 必须是 VirtuosoConnectionManager 的一个实例。") # Error: connection_manager must be an instance of VirtuosoConnectionManager.
        self.connection_manager = connection_manager
        # SparqlExecutor 自身不直接管理连接状态 (connect/disconnect)，
        # The SparqlExecutor itself does not directly manage connection state (connect/disconnect),
        # 而是依赖于 connection_manager 的上下文管理或显式调用。
        # but relies on the context management or explicit calls of connection_manager.

    def execute_select(self, sparql_query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        执行SPARQL SELECT查询。

        参数:
        - sparql_query (str): 要执行的SPARQL SELECT查询。
        - params (Optional[tuple]): 查询参数 (用于pyodbc的 ? 占位符)。

        返回:
        - List[Dict[str, Any]]: 查询结果，每行是一个字典。
        """
        # connection_manager 的方法会处理 _ensure_connected
        # The connection_manager's methods will handle _ensure_connected
        print(f"信息：SparqlExecutor 准备执行 SELECT 查询：{sparql_query[:200]}...") # Info: SparqlExecutor preparing to execute SELECT query...
        try:
            results = self.connection_manager.execute_query(sparql_query, params)
            print(f"信息：SELECT 查询成功执行。返回 {len(results)} 行。") # Info: SELECT query executed successfully. Returned X rows.
            return results
        except Exception as e:
            print(f"错误：SparqlExecutor 执行 SELECT 查询失败。错误：{e}") # Error: SparqlExecutor failed to execute SELECT query. Error: ...
            raise # 将异常向上传播
                  # Propagate the exception upwards

    def execute_update(self, sparql_update: str, params: Optional[tuple] = None) -> int:
        """
        执行SPARQL更新操作 (INSERT, DELETE, etc.)。

        参数:
        - sparql_update (str): 要执行的SPARQL更新语句。
        - params (Optional[tuple]): 更新参数。

        返回:
        - int: 受操作影响的行数。
        """
        print(f"信息：SparqlExecutor 准备执行 UPDATE 操作：{sparql_update[:200]}...") # Info: SparqlExecutor preparing to execute UPDATE operation...
        try:
            affected_rows = self.connection_manager.execute_update(sparql_update, params)
            print(f"信息：UPDATE 操作成功执行。影响行数：{affected_rows}。") # Info: UPDATE operation executed successfully. Rows affected: X.
            return affected_rows
        except Exception as e:
            print(f"错误：SparqlExecutor 执行 UPDATE 操作失败。错误：{e}") # Error: SparqlExecutor failed to execute UPDATE operation. Error: ...
            raise

    def begin_transaction(self) -> None:
        """
        通过连接管理器开始一个事务。
        Begins a transaction via the connection manager.
        """
        print("信息：SparqlExecutor 请求开始事务。") # Info: SparqlExecutor requesting to begin transaction.
        try:
            self.connection_manager.begin_transaction()
        except Exception as e:
            print(f"错误：SparqlExecutor 开始事务失败。错误：{e}") # Error: SparqlExecutor failed to begin transaction. Error: ...
            raise

    def commit_transaction(self) -> None:
        """
        通过连接管理器提交当前事务。
        Commits the current transaction via the connection manager.
        """
        print("信息：SparqlExecutor 请求提交事务。") # Info: SparqlExecutor requesting to commit transaction.
        try:
            self.connection_manager.commit_transaction()
        except Exception as e:
            print(f"错误：SparqlExecutor 提交事务失败。错误：{e}") # Error: SparqlExecutor failed to commit transaction. Error: ...
            raise

    def rollback_transaction(self) -> None:
        """
        通过连接管理器回滚当前事务。
        Rolls back the current transaction via the connection manager.
        """
        print("信息：SparqlExecutor 请求回滚事务。") # Info: SparqlExecutor requesting to rollback transaction.
        try:
            self.connection_manager.rollback_transaction()
        except Exception as e:
            print(f"错误：SparqlExecutor 回滚事务失败。错误：{e}") # Error: SparqlExecutor failed to rollback transaction. Error: ...
            raise

# 示例用法 (用于演示，实际中 SparqlExecutor 通常由其他服务或组件使用)
# Example usage (for demonstration, in practice SparqlExecutor is usually used by other services or components)
if __name__ == '__main__':
    # 这个示例需要一个正在运行的Virtuoso实例和配置好的ODBC环境
    # This example requires a running Virtuoso instance and a configured ODBC environment.
    from .connection_manager import VirtuosoConnectionManager

    # 请根据您的环境修改这些设置
    # Please modify these settings according to your environment
    db_manager = VirtuosoConnectionManager(
        host="localhost", 
        port=1111, 
        user="dba", 
        password="dba", # 请使用强密码! Please use a strong password!
        default_graph_uri="http://tcm.example.org/graph"
    )
    
    # 创建 SparqlExecutor 实例
    # Create SparqlExecutor instance
    executor = SparqlExecutor(db_manager)

    try:
        # 使用上下文管理器确保数据库连接的正确打开和关闭
        # Use context manager to ensure proper opening and closing of database connection
        with db_manager: # 这会调用 db_manager.connect() 和 db_manager.disconnect()
                         # This will call db_manager.connect() and db_manager.disconnect()
            
            # 1. 尝试开始事务并执行插入
            # 1. Try to begin a transaction and execute an insert
            print("\n--- 示例1: 插入数据 ---") # Example 1: Insert data
            executor.begin_transaction()
            
            insert_query = "SPARQL INSERT DATA INTO <http://tcm.example.org/test_graph> { <ex:s_main> <ex:p_main> <ex:o_main> . }"
            print(f"执行插入: {insert_query}") # Executing insert
            affected_rows = executor.execute_update(insert_query)
            print(f"插入操作影响的行数: {affected_rows}") # Rows affected by insert operation
            
            # 提交事务
            # Commit transaction
            executor.commit_transaction()
            print("插入事务已提交。") # Insert transaction committed.

            # 2. 执行查询以验证插入
            # 2. Execute a query to verify the insertion
            print("\n--- 示例2: 查询数据 ---") # Example 2: Query data
            select_query = "SPARQL SELECT ?s ?p ?o FROM <http://tcm.example.org/test_graph> WHERE { ?s ?p ?o } LIMIT 5"
            print(f"执行查询: {select_query}") # Executing query
            results = executor.execute_select(select_query)
            if results:
                print("查询结果:") # Query results:
                for row in results:
                    print(row)
            else:
                print("未查询到结果或查询失败。") # No results found or query failed.
            
            assert any(r['s'] == 'ex:s_main' for r in results), "插入的数据未找到！" # Inserted data not found!

            # 3. 尝试回滚事务
            # 3. Try to roll back a transaction
            print("\n--- 示例3: 回滚事务 ---") # Example 3: Rollback transaction
            executor.begin_transaction()
            insert_query_for_rollback = "SPARQL INSERT DATA INTO <http://tcm.example.org/test_graph> { <ex:s_rollback> <ex:p_rollback> <ex:o_rollback> . }"
            print(f"执行用于回滚的插入: {insert_query_for_rollback}") # Executing insert for rollback
            executor.execute_update(insert_query_for_rollback)
            
            # 回滚事务
            # Rollback transaction
            executor.rollback_transaction()
            print("插入事务已回滚。") # Insert transaction rolled back.

            # 查询以验证回滚 (应找不到 <ex:s_rollback>)
            # Query to verify rollback (should not find <ex:s_rollback>)
            select_query_after_rollback = "SPARQL SELECT ?s FROM <http://tcm.example.org/test_graph> WHERE { ?s <ex:p_rollback> <ex:o_rollback> }"
            results_after_rollback = executor.execute_select(select_query_after_rollback)
            assert len(results_after_rollback) == 0, "回滚失败，数据依然存在！" # Rollback failed, data still exists!
            print("用于回滚的数据未在数据库中找到，回滚成功。") # Data for rollback not found in DB, rollback successful.

            # 清理测试数据
            # Clean up test data
            print("\n--- 清理测试数据 ---") # Clean up test data
            executor.begin_transaction()
            clear_graph_query = "SPARQL CLEAR GRAPH <http://tcm.example.org/test_graph>"
            print(f"执行清空图: {clear_graph_query}") # Executing clear graph
            executor.execute_update(clear_graph_query)
            executor.commit_transaction()
            print("测试图已清空。") # Test graph cleared.

    except Exception as e:
        print(f"SparqlExecutor 示例执行过程中发生错误: {e}") # Error during SparqlExecutor example execution
        # 如果在事务中发生错误，确保回滚 (尽管上下文管理器会尝试)
        # If an error occurs during a transaction, ensure rollback (although context manager will try)
        if db_manager.transaction_active:
            try:
                print("检测到活动事务，尝试回滚...") # Active transaction detected, attempting rollback...
                db_manager.rollback_transaction()
            except Exception as rb_ex:
                print(f"尝试回滚事务时发生错误: {rb_ex}") # Error during transaction rollback attempt.
