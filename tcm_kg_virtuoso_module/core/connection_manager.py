# tcm_kg_virtuoso_module/core/connection_manager.py
import pyodbc
from typing import Optional, List, Dict, Any

class VirtuosoConnectionManager:
    """
    使用 pyodbc 管理 Virtuoso 数据库连接。
    Manages Virtuoso database connections using pyodbc.
    """
    def __init__(self, host: str, port: int, user: str, password: str, default_graph_uri: Optional[str] = None):
        """
        初始化连接管理器。

        参数:
        - host (str): Virtuoso 服务器主机名或IP地址。
        - port (int): Virtuoso 服务器端口。
        - user (str): Virtuoso 用户名。
        - password (str): Virtuoso 密码。
        - default_graph_uri (Optional[str]): 默认图URI (当前未使用，但保留以备将来之需)。
                                            Default graph URI (currently unused, but kept for future needs).
        """
        self.driver: str = "{Virtuoso (Open Source)}" # ODBC 驱动名称，需要确保系统中已安装并配置
                                       # ODBC driver name, ensure it's installed and configured in the system
        self.server: str = host
        self.port: int = port
        self.database: str = "VOS" # Virtuoso 的默认数据库名通常是 VOS 或 virtuoso
                                   # Virtuoso's default database name is usually VOS or virtuoso
        self.user: str = user
        self.password: str = password
        dsn_name = "VirtuosoDSN"  # O DSN que você criou e testou
        self.conn_string: str = f"DSN={dsn_name};UID={self.user};PWD={self.password};LoginTimeout=30;"
        #self.conn_string: str = (
        #    f"DRIVER={self.driver};SERVER={self.server},{self.port};"
        #    f"DATABASE={self.database};UID={self.user};PWD={self.password};"
        #    # 根据需要添加更多连接参数，例如：
        #    # Add more connection parameters as needed, e.g.:
        #    # ReadOnly=N; ResultSetMode=Scrollable; MaxQueryTimeout=0;
        #)
        self.connection: Optional[pyodbc.Connection] = None
        self.cursor: Optional[pyodbc.Cursor] = None
        self.transaction_active: bool = False # 跟踪事务状态
                                             # Track transaction status

    def connect(self) -> None:
        """
        连接到 Virtuoso 数据库。
        Connects to the Virtuoso database.
        """
        if self.connection:
            print("信息：已存在一个连接。如需新连接，请先断开。") # Info: A connection already exists. Disconnect first for a new one.
            return

        try:
            print(f"信息：尝试使用连接字符串连接到 Virtuoso：{self.conn_string.replace(self.password, '********')}") # Info: Attempting to connect to Virtuoso with connection string...
            self.connection = pyodbc.connect(self.conn_string, autocommit=False) # 关闭自动提交以进行手动事务管理
                                                                               # Disable autocommit for manual transaction management
            self.cursor = self.connection.cursor()
            print("信息：成功连接到 Virtuoso 数据库。") # Info: Successfully connected to Virtuoso database.
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            message = ex.args[1]
            print(f"错误：连接 Virtuoso 数据库失败。SQLSTATE: {sqlstate}, 错误信息: {message}") # Error: Failed to connect to Virtuoso database. SQLSTATE: ..., Error message: ...
            # 可以考虑更具体的错误处理，例如检查驱动是否安装
            # Consider more specific error handling, e.g., checking if the driver is installed
            if "01000" in sqlstate or "IM002" in sqlstate: # IM002: Data source name not found and no default driver specified
                print(f"错误提示：请确保 Virtuoso ODBC 驱动已正确安装，并且驱动名称 '{self.driver}' 无误。") # Error hint: Ensure Virtuoso ODBC driver is installed correctly and driver name is correct.
            self.connection = None
            self.cursor = None
            raise  # 重新抛出异常，让调用者处理
                   # Re-throw the exception for the caller to handle

    def disconnect(self) -> None:
        """
        断开与 Virtuoso 数据库的连接。
        Disconnects from the Virtuoso database.
        """
        if self.transaction_active:
            print("警告：断开连接时存在活动事务。将尝试回滚。") # Warning: Active transaction during disconnect. Attempting rollback.
            self.rollback_transaction() # 确保事务被处理
                                       # Ensure transaction is handled

        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.connection:
            self.connection.close()
            self.connection = None
        print("信息：已断开与 Virtuoso 数据库的连接。") # Info: Disconnected from Virtuoso database.

    def _ensure_connected(self) -> None:
        """
        确保存在活动的数据库连接和游标。
        Ensures an active database connection and cursor exist.
        """
        if not self.connection or not self.cursor:
            # print("信息：连接不存在，正在尝试重新连接...") # Info: Connection does not exist, attempting to reconnect...
            # self.connect() # 或者直接抛出异常，要求调用者显式连接
            #                 # Or throw an exception, requiring the caller to connect explicitly
            raise ConnectionError("错误：数据库未连接。请先调用 connect() 方法。") # Error: Database not connected. Call connect() first.


    def execute_query(self, sparql_query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        执行 SPARQL SELECT 查询并返回结果。

        参数:
        - sparql_query (str): 要执行的 SPARQL 查询字符串。
        - params (Optional[tuple]): 查询参数 (pyodbc中使用 ? 作为占位符)。

        返回:
        - List[Dict[str, Any]]: 查询结果列表，每行是一个字典。
        """
        self._ensure_connected()
        try:
            # pyodbc 的 `execute` 方法用于所有类型的SQL/SPARQL
            # pyodbc's `execute` method is used for all types of SQL/SPARQL
            if params:
                self.cursor.execute(sparql_query, params)
            else:
                self.cursor.execute(sparql_query)
            
            columns = [column[0] for column in self.cursor.description or []]
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            message = ex.args[1]
            print(f"错误：执行查询失败。SQLSTATE: {sqlstate}, 查询: '{sparql_query[:100]}...', 错误: {message}") # Error: Failed to execute query.
            raise

    def execute_update(self, sparql_update: str, params: Optional[tuple] = None) -> int:
        """
        执行 SPARQL UPDATE (INSERT, DELETE, etc.) 操作。

        参数:
        - sparql_update (str): 要执行的 SPARQL 更新字符串。
        - params (Optional[tuple]): 更新参数。

        返回:
        - int: 受操作影响的行数。
        """
        self._ensure_connected()
        try:
            if params:
                self.cursor.execute(sparql_update, params)
            else:
                self.cursor.execute(sparql_update)
            
            # 对于非 SELECT 查询，rowcount 通常表示受影响的行数
            # For non-SELECT queries, rowcount usually indicates the number of affected rows
            affected_rows = self.cursor.rowcount
            
            # 如果没有活动的事务，并且连接未设置为自动提交，则需要手动提交
            # If no active transaction and connection is not set to autocommit, manual commit is needed
            if not self.transaction_active and not self.connection.autocommit:
                self.connection.commit() # 对于单个更新操作，如果不在事务中，则提交
                                        # For single update operations, commit if not in a transaction
                print(f"信息：更新操作已执行并提交。影响行数：{affected_rows}") # Info: Update operation executed and committed. Rows affected.
            else:
                print(f"信息：更新操作已执行。影响行数：{affected_rows}。处于活动事务中，等待提交或回滚。") # Info: Update op executed. Rows affected. In active transaction, awaiting commit/rollback.
            return affected_rows
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            message = ex.args[1]
            print(f"错误：执行更新失败。SQLSTATE: {sqlstate}, 更新: '{sparql_update[:100]}...', 错误: {message}") # Error: Failed to execute update.
            raise

    def begin_transaction(self) -> None:
        """
        开始一个新的数据库事务。
        """
        self._ensure_connected()
        if self.connection.autocommit:
            print("警告：连接配置为自动提交，手动事务控制可能无效。") # Warning: Connection is autocommit, manual transaction control might be ineffective.
            # self.connection.autocommit = False # 可以考虑在此处强制关闭，但需谨慎
                                                # Could consider forcing it off here, but be cautious
        
        if self.transaction_active:
            print("警告：已存在一个活动事务。请先提交或回滚当前事务。") # Warning: Active transaction already exists. Commit or rollback first.
            return

        # pyodbc 的事务是隐式的，通过关闭 autocommit 和调用 commit/rollback 来管理
        # pyodbc transactions are implicit, managed by turning off autocommit and calling commit/rollback
        # self.connection.commit() # 如果之前有未提交的操作，先处理掉（通常不应该发生）
                                  # If there were previous uncommitted operations, handle them (should not normally happen)
        self.transaction_active = True
        print("信息：数据库事务已开始。") # Info: Database transaction started.

    def commit_transaction(self) -> None:
        """
        提交当前事务。
        """
        self._ensure_connected()
        if not self.transaction_active:
            print("警告：没有活动的事务可供提交。") # Warning: No active transaction to commit.
            return
        try:
            self.connection.commit()
            self.transaction_active = False
            print("信息：事务已成功提交。") # Info: Transaction successfully committed.
        except pyodbc.Error as ex:
            print(f"错误：提交事务失败。错误: {ex}") # Error: Failed to commit transaction.
            # 提交失败通常意味着需要回滚或进行其他错误处理
            # Transaction commit failure usually means rollback or other error handling is needed.
            raise

    def rollback_transaction(self) -> None:
        """
        回滚当前事务。
        """
        self._ensure_connected()
        if not self.transaction_active:
            # 如果没有标记为活动的事务，但连接存在且autocommit为False，
            # 任何未提交的操作都可能通过connection.rollback()回滚
            # If no transaction marked active, but connection exists and autocommit is False,
            # any uncommitted operations might be rolled back by connection.rollback()
            if self.connection and not self.connection.autocommit:
                 print("信息：没有显式开始的事务，但将尝试回滚连接上的任何挂起操作。") # Info: No explicitly started transaction, but will try to roll back pending ops.
            else:
                print("警告：没有活动的事务可供回滚。") # Warning: No active transaction to rollback.
                return
        try:
            self.connection.rollback()
            self.transaction_active = False # 确保在回滚后重置状态
                                           # Ensure state is reset after rollback
            print("信息：事务已回滚。") # Info: Transaction rolled back.
        except pyodbc.Error as ex:
            print(f"错误：回滚事务失败。错误: {ex}") # Error: Failed to rollback transaction.
            # 回滚失败是严重问题
            # Rollback failure is a serious issue.
            raise

    def __enter__(self):
        """上下文管理器进入方法，自动连接。"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出方法，自动断开连接。"""
        # 如果在 'with' 块内发生异常，并且存在活动事务，则回滚
        # If an exception occurred within the 'with' block and an active transaction exists, rollback.
        if exc_type is not None and self.transaction_active:
            print(f"信息：在 'with' 块中发生异常({exc_type})，将回滚活动事务。") # Info: Exception in 'with' block, rolling back active transaction.
            try:
                self.rollback_transaction()
            except pyodbc.Error as e:
                print(f"警告：在 __exit__ 中回滚事务失败: {e}") # Warning: Failed to rollback transaction in __exit__.
        
        self.disconnect()

# 示例用法 (用于测试，实际使用时应通过依赖注入等方式管理)
# Example usage (for testing, should be managed via dependency injection etc. in actual use)
if __name__ == '__main__':
    # 假设 Virtuoso 服务正在本地运行，并且 ODBC 驱动已配置
    # Assume Virtuoso service is running locally and ODBC driver is configured
    # 请根据您的环境修改这些设置
    # Please modify these settings according to your environment
    manager = VirtuosoConnectionManager(
        host="localhost", 
        port=1111, 
        user="dba", 
        password="dba", # 请使用强密码! Please use a strong password!
        default_graph_uri="http://tcm.example.org/graph"
    )

    try:
        with manager: # 使用上下文管理器确保连接和断开
                      # Use context manager to ensure connection and disconnection
            # 示例：开始事务
            # Example: begin transaction
            manager.begin_transaction()

            # 示例：执行更新 (假设有一个测试图)
            # Example: execute update (assuming a test graph)
            test_graph = "http://tcm.example.org/test_graph"
            insert_query = f"""
            SPARQL INSERT DATA INTO <{test_graph}> {{ 
                <http://example.com/s1> <http://example.com/p1> <http://example.com/o1> .
            }}
            """
            print(f"执行插入查询: {insert_query}") # Executing insert query
            manager.execute_update(insert_query)

            # 示例：执行查询
            # Example: execute query
            select_query = f"SPARQL SELECT ?s ?p ?o FROM <{test_graph}> WHERE {{ ?s ?p ?o }} LIMIT 10"
            print(f"执行查询: {select_query}") # Executing select query
            results = manager.execute_query(select_query)
            print("查询结果:") # Query results:
            for row in results:
                print(row)

            # 提交事务
            # Commit transaction
            manager.commit_transaction()
            print("事务已提交。") # Transaction committed.

            # 验证插入（应在提交后可见）
            # Verify insertion (should be visible after commit)
            results_after_commit = manager.execute_query(select_query)
            print("提交后的查询结果:") # Query results after commit:
            for row in results_after_commit:
                print(row)
            assert len(results_after_commit) > 0, "数据未成功插入或查询失败。" # Data not inserted or query failed.


            # 示例：测试回滚
            # Example: test rollback
            manager.begin_transaction()
            insert_query_2 = f"""
            SPARQL INSERT DATA INTO <{test_graph}> {{ 
                <http://example.com/s2> <http://example.com/p2> <http://example.com/o2> .
            }}
            """
            print(f"执行第二次插入查询: {insert_query_2}") # Executing second insert query
            manager.execute_update(insert_query_2)
            manager.rollback_transaction()
            print("事务已回滚。") # Transaction rolled back.

            results_after_rollback = manager.execute_query(f"SPARQL SELECT ?s FROM <{test_graph}> WHERE {{ ?s <http://example.com/p2> <http://example.com/o2> }}")
            assert len(results_after_rollback) == 0, "数据回滚失败。" # Data rollback failed.
            print("第二次插入的数据已成功回滚。") # Data from second insert successfully rolled back.

            # 清理测试数据
            # Clean up test data
            manager.begin_transaction()
            clear_graph_query = f"SPARQL CLEAR GRAPH <{test_graph}>"
            print(f"执行清空图查询: {clear_graph_query}") # Executing clear graph query
            manager.execute_update(clear_graph_query)
            manager.commit_transaction()
            print(f"测试图 <{test_graph}> 已清空。") # Test graph cleared.


    except pyodbc.Error as e:
        print(f"发生 pyodbc 错误: {e}") # A pyodbc error occurred
    except ConnectionError as e:
        print(f"发生连接错误: {e}") # A connection error occurred
    except Exception as e:
        print(f"发生未知错误: {e}") # An unknown error occurred
