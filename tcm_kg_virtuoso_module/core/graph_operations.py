# tcm_kg_virtuoso_module/core/graph_operations.py

from typing import Dict, List, Optional, Any, Union # 确保导入 Any 和 Union

from .data_formatter import prepare_entity_sparql_insert, prepare_relationship_sparql_insert
from .sparql_executor import SparqlExecutor
from .connection_manager import VirtuosoConnectionManager

def add_entity(entity_data: Dict[str, Any], conn_manager: VirtuosoConnectionManager) -> str: # 返回类型变更为 str
    """
    将实体及其元数据添加到知识图谱中。

    此函数通过准备并执行SPARQL INSERT查询来添加实体。
    它处理事务以确保数据插入的原子性。

    参数:
    - entity_data (Dict[str, Any]): 包含实体信息的字典。预期键包括:
        - 'entity_type_name' (str, 必需): 实体的类型名称 (例如, "Herb")。
        - 'entity_label' (str, 必需): 实体的 rdfs:label。
        - 'attributes_list' (List[Dict[str, str]], 可选): 包含实体属性的字典列表。
          每个字典应有 'property' (CURIE或完整URI) 和 'value' (字面量或完整URI)键。
          默认为空列表。
        - 'source_details' (Dict[str, str], 必需): 传递给 create_source_metadata 的参数字典。
        - 'entity_id_args' (Optional[List[str]], 可选): 用于 mint_entity_uri 的附加标识符参数。
          默认为 None。
    - conn_manager (VirtuosoConnectionManager): 用于管理数据库连接的连接管理器实例。

    返回:
    - str: 成功添加的实体的URI。

    抛出:
    - ValueError: 如果 entity_data 中缺少必需的键或数据类型不正确。
    - Exception: 如果在SPARQL执行过程中发生任何其他错误 (例如数据库错误)，异常将被重新抛出。
    """

    # 1. 数据提取和校验 (更新以反映新的输入结构)
    # 1. Data Extraction and Validation (updated for new input structure)
    required_keys = ['entity_type_name', 'entity_label', 'source_details']
    for key in required_keys:
        if key not in entity_data:
            raise ValueError(f"错误：entity_data 字典中缺少必需的键 '{key}'。")

    entity_type_name: str = entity_data['entity_type_name']
    entity_label: str = entity_data['entity_label']
    source_details: Dict[str, str] = entity_data['source_details']
    
    # 可选参数
    # Optional parameters
    input_attributes_list: List[Dict[str, str]] = entity_data.get('attributes_list', []) 
    entity_id_args: Optional[List[str]] = entity_data.get('entity_id_args', None)

    # 类型校验 (基本)
    # Type validation (basic)
    if not isinstance(entity_type_name, str):
        raise ValueError(f"错误：'entity_type_name' 应该是字符串，但得到的是 {type(entity_type_name)}。")
    if not isinstance(entity_label, str):
        raise ValueError(f"错误：'entity_label' 应该是字符串，但得到的是 {type(entity_label)}。")
    if not isinstance(source_details, dict):
        raise ValueError(f"错误：'source_details' 应该是字典，但得到的是 {type(source_details)}。")
    if not isinstance(input_attributes_list, list) or not all(isinstance(item, dict) for item in input_attributes_list):
        raise ValueError(f"错误：'attributes_list' 应该是字典列表，但得到的是 {type(input_attributes_list)}。")
    if entity_id_args is not None and not (isinstance(entity_id_args, list) and all(isinstance(arg, str) for arg in entity_id_args)):
        raise ValueError(f"错误：'entity_id_args' 应该是字符串列表或None，但得到的是 {type(entity_id_args)}。")

    # 2. 转换 'attributes_list' 为 'entity_properties_for_formatter'
    # 2. Transform 'attributes_list' to 'entity_properties_for_formatter'
    entity_properties_for_formatter: Dict[str, Union[str, List[str]]] = {}
    for attr_item in input_attributes_list:
        prop_curie = attr_item.get('property')
        prop_value = attr_item.get('value')

        if not prop_curie or prop_value is None: # 基本校验
            print(f"警告：检测到无效的属性条目，已跳过: {attr_item}")
            continue

        if prop_curie in entity_properties_for_formatter:
            current_val = entity_properties_for_formatter[prop_curie]
            if isinstance(current_val, list):
                current_val.append(prop_value)
            else: 
                entity_properties_for_formatter[prop_curie] = [current_val, prop_value]
        else:
            entity_properties_for_formatter[prop_curie] = prop_value
            
    # 3. SPARQL查询生成
    # 3. SPARQL Query Generation
    print(f"信息：正在为实体 '{entity_label}' (类型: {entity_type_name}) 生成SPARQL查询。")
    
    # prepare_entity_sparql_insert 现在返回 (sparql_query, entity_uri)
    # prepare_entity_sparql_insert now returns (sparql_query, entity_uri)
    sparql_query, entity_uri = prepare_entity_sparql_insert(
        entity_type_name=entity_type_name,
        entity_label=entity_label,
        entity_properties=entity_properties_for_formatter, # 使用转换后的属性字典
                                                           # Use the transformed properties dictionary
        source_details=source_details,
        entity_id_args=entity_id_args
    )

    # 4. SPARQL执行与事务管理
    # 4. SPARQL Execution with Transaction Management
    executor = SparqlExecutor(conn_manager)

    try:
        executor.begin_transaction()
        print(f"信息：正在执行实体 '{entity_label}' (URI: {entity_uri}) 的SPARQL更新。")
        executor.execute_update(sparql_query)
        executor.commit_transaction()
        print(f"成功：实体 '{entity_label}' (URI: {entity_uri}) 已成功添加，事务已提交。")
    except Exception as e:
        print(f"错误：在添加实体 '{entity_label}' (URI: {entity_uri}) 过程中发生错误。正在回滚事务。错误详情: {e}")
        executor.rollback_transaction()
        raise e
    
    return entity_uri # 返回生成的实体URI
                     # Return the generated entity URI


def add_relationship(relationship_data: Dict[str, Any], conn_manager: VirtuosoConnectionManager) -> None:
    """
    Adds a relationship between two entities in the knowledge graph.

    This function prepares and executes a SPARQL INSERT query to add the relationship.
    It handles transactions to ensure atomicity of the data insertion.

    Args:
    - relationship_data (Dict[str, Any]): A dictionary containing relationship information. Expected keys:
        - 'subject_uri' (str, required): The URI of the subject entity.
        - 'predicate' (str, required): The CURIE of the predicate.
        - 'object_uri' (str, required): The URI of the object entity.
        - 'source_details' (Dict[str, str], required): Dictionary of parameters for create_source_metadata.
    - conn_manager (VirtuosoConnectionManager): An instance of the connection manager for database interactions.

    Raises:
    - ValueError: If required keys are missing from relationship_data or if data types are incorrect.
    - Exception: Re-raises any other exceptions that occur during SPARQL execution (e.g., database errors).
    """

    # 1. Data Extraction and Validation
    required_keys = ['subject_uri', 'predicate', 'object_uri', 'source_details']
    for key in required_keys:
        if key not in relationship_data:
            raise ValueError(f"Error: Missing required key '{key}' in relationship_data dictionary.")

    subject_uri: str = relationship_data['subject_uri']
    predicate: str = relationship_data['predicate']
    object_uri: str = relationship_data['object_uri']
    source_details: Dict[str, str] = relationship_data['source_details']

    # Type validation
    if not isinstance(subject_uri, str):
        raise ValueError(f"Error: 'subject_uri' should be a string, but got {type(subject_uri)}.")
    if not isinstance(predicate, str):
        raise ValueError(f"Error: 'predicate' should be a string (CURIE), but got {type(predicate)}.")
    if not isinstance(object_uri, str):
        raise ValueError(f"Error: 'object_uri' should be a string, but got {type(object_uri)}.")
    if not isinstance(source_details, dict):
        raise ValueError(f"Error: 'source_details' should be a dictionary, but got {type(source_details)}.")

    # 2. (Handled by imports) Import prepare_relationship_sparql_insert from .data_formatter

    # 3. SPARQL Query Generation
    print(f"Info: Generating SPARQL query for relationship: {subject_uri} - {predicate} - {object_uri}")
    sparql_query = prepare_relationship_sparql_insert(
        subject_uri=subject_uri,
        predicate_curie=predicate,
        object_uri=object_uri,
        source_details=source_details
    )

    # 4. (Handled by imports) Import SparqlExecutor from .sparql_executor

    # 5. Instantiate SparqlExecutor
    executor = SparqlExecutor(conn_manager)

    # 6. SPARQL Execution with Transaction Management
    try:
        executor.begin_transaction()
        print(f"Info: Executing SPARQL update for relationship: {subject_uri} - {predicate} - {object_uri}")
        executor.execute_update(sparql_query)
        executor.commit_transaction()
        print(f"Success: Relationship {subject_uri} - {predicate} - {object_uri} added successfully, transaction committed.")
    except Exception as e:
        print(f"Error: An error occurred while adding relationship {subject_uri} - {predicate} - {object_uri}. Rolling back transaction. Error details: {e}")
        executor.rollback_transaction()
        raise e
