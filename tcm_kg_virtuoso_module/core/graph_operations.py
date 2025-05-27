# tcm_kg_virtuoso_module/core/graph_operations.py

from typing import Dict, List, Optional, Any # 确保导入 Any 以适应 entity_data 的值类型
                                           # Ensure Any is imported to accommodate value types in entity_data

from .data_formatter import prepare_entity_sparql_insert
from .sparql_executor import SparqlExecutor
from .connection_manager import VirtuosoConnectionManager
from .uri_minter import mint_entity_uri

def add_entity(entity_data: Dict[str, Any], conn_manager: VirtuosoConnectionManager) -> str:
    """
    将实体及其元数据添加到知识图谱中，并返回新创建实体的URI。

    此函数通过准备并执行SPARQL INSERT查询来添加实体。
    它处理事务以确保数据插入的原子性。

    参数:
    - entity_data (Dict[str, Any]): 包含实体信息的字典。预期键包括:
        - 'entity_type_name' (str, 必需): 实体的类型名称 (例如, "Herb")。
        - 'entity_label' (str, 必需): 实体的 rdfs:label。
        - 'entity_properties' (Dict[str, str], 可选): 实体的附加属性，
          键为CURIE或完整URI，值为字面量或完整URI。默认为空字典。
        - 'source_details' (Dict[str, str], 必需): 传递给 create_source_metadata 的参数字典。
        - 'entity_id_args' (Optional[List[str]], 可选): 用于 mint_entity_uri 的附加标识符参数。
          默认为 None。
    - conn_manager (VirtuosoConnectionManager): 用于管理数据库连接的连接管理器实例。

    返回:
    - str: The URI of the newly created entity.

    抛出:
    - ValueError: 如果 entity_data 中缺少必需的键。
    - Exception: 如果在SPARQL执行过程中发生任何其他错误 (例如数据库错误)，异常将被重新抛出。
    """

    # 3. 数据提取
    # 3. Data Extraction
    # 从 entity_data 字典中安全地提取所需信息。
    # Safely extract necessary information from the entity_data dictionary.

    # 检查必需的键是否存在
    # Check for the presence of required keys
    required_keys = ['entity_type_name', 'entity_label', 'source_details']
    for key in required_keys:
        if key not in entity_data:
            raise ValueError(f"错误：entity_data 字典中缺少必需的键 '{key}'。") # Chinese error message
            # Error: Missing required key '{key}' in entity_data dictionary.

    entity_type_name: str = entity_data['entity_type_name']
    entity_label: str = entity_data['entity_label']
    source_details: Dict[str, str] = entity_data['source_details']

    # 可选参数使用 .get() 方法以提供默认值
    # Optional parameters use the .get() method to provide default values
    entity_properties: Dict[str, str] = entity_data.get('entity_properties', {})
    entity_id_args: Optional[List[str]] = entity_data.get('entity_id_args', None)

    # 确保提取的数据类型符合预期 (基本类型检查)
    # Ensure extracted data types meet expectations (basic type checking)
    if not isinstance(entity_type_name, str):
        raise ValueError(f"错误：'entity_type_name' 应该是字符串，但得到的是 {type(entity_type_name)}。")
        # Error: 'entity_type_name' should be a string, but got {type(entity_type_name)}.
    if not isinstance(entity_label, str):
        raise ValueError(f"错误：'entity_label' 应该是字符串，但得到的是 {type(entity_label)}。")
        # Error: 'entity_label' should be a string, but got {type(entity_label)}.
    if not isinstance(entity_properties, dict):
        raise ValueError(f"错误：'entity_properties' 应该是字典，但得到的是 {type(entity_properties)}。")
        # Error: 'entity_properties' should be a dictionary, but got {type(entity_properties)}.
    if not isinstance(source_details, dict):
        raise ValueError(f"错误：'source_details' 应该是字典，但得到的是 {type(source_details)}。")
        # Error: 'source_details' should be a dictionary, but got {type(source_details)}.
    if entity_id_args is not None and not (isinstance(entity_id_args, list) and all(isinstance(arg, str) for arg in entity_id_args)):
        raise ValueError(f"错误：'entity_id_args' 应该是字符串列表或None，但得到的是 {type(entity_id_args)}。")
        # Error: 'entity_id_args' should be a list of strings or None, but got {type(entity_id_args)}.

    # Generate the entity URI before preparing the SPARQL query
    predicted_entity_uri = mint_entity_uri(
        entity_type_name, 
        entity_label, 
        *(entity_id_args if entity_id_args else [])
    )

    # 4. SPARQL查询生成
    # 4. SPARQL Query Generation
    # 调用 prepare_entity_sparql_insert 函数生成SPARQL查询字符串。
    # Call the prepare_entity_sparql_insert function to generate the SPARQL query string.
    print(f"信息：正在为实体 '{entity_label}' (类型: {entity_type_name}) 生成SPARQL查询。URI 将为 {predicted_entity_uri}") # Chinese info message
    # Info: Generating SPARQL query for entity '{entity_label}' (type: {entity_type_name}).
    
    sparql_query = prepare_entity_sparql_insert(
        entity_type_name=entity_type_name,
        entity_label=entity_label,
        entity_properties=entity_properties,
        source_details=source_details,
        entity_id_args=entity_id_args
    )

    # 5. SPARQL执行与事务管理
    # 5. SPARQL Execution with Transaction Management
    # 创建 SparqlExecutor 实例。
    # Create an instance of SparqlExecutor.
    executor = SparqlExecutor(conn_manager)

    try:
        # 执行更新 (SPARQL INSERT)
        # Execute update (SPARQL INSERT)
        print(f"信息：正在执行实体 '{entity_label}' 的SPARQL更新。") # Chinese info message
        # Info: Executing SPARQL update for entity '{entity_label}'.
        executor.execute_update(sparql_query) # This now directly executes the update.
                                            # SPARQLWrapper itself doesn't have explicit transaction commit/rollback methods
                                            # for single queries in the same way JDBC/ODBC might.
                                            # Each update is typically auto-committed or managed by Virtuoso settings.
        
        print(f"成功：实体 '{entity_label}' 的SPARQL更新已成功执行。URI: {predicted_entity_uri}") # Chinese success message
        # Success: SPARQL update for entity '{entity_label}' executed successfully. URI: {predicted_entity_uri}
        return predicted_entity_uri

    except Exception as e:
        # 如果发生任何错误
        # If any error occurs
        print(f"错误：在添加实体 '{entity_label}' 过程中执行SPARQL更新时发生错误。错误详情: {e}") # Chinese error message
        # Error: An error occurred while executing SPARQL update for entity '{entity_label}'. Error details: {e}
        # No explicit rollback call needed here as SPARQLWrapper doesn't manage transactions in this way.
        # Re-raise the exception so the caller can handle it
        raise e
    # finally 块在这里不是必需的，因为连接的关闭由 VirtuosoConnectionManager 的使用者（或其上下文管理器）负责。
    # A finally block is not strictly necessary here, as connection closing is managed by the
    # VirtuosoConnectionManager's user (or its context manager, if applicable).
    # 如果 SparqlExecutor 或 VirtuosoConnectionManager 需要显式清理，则可以添加 finally。
    # If SparqlExecutor or VirtuosoConnectionManager required explicit cleanup, a finally block could be added.
