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
    print(f"信息：正在为关系 {subject_uri} - {predicate} - {object_uri} 生成SPARQL查询。") # Chinese print
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
        print(f"信息：正在执行关系 {subject_uri} - {predicate} - {object_uri} 的SPARQL更新。") # Chinese print
        executor.execute_update(sparql_query)
        executor.commit_transaction()
        print(f"成功：关系 {subject_uri} - {predicate} - {object_uri} 已成功添加，事务已提交。") # Chinese print
    except Exception as e:
        print(f"错误：在添加关系 {subject_uri} - {predicate} - {object_uri} 过程中发生错误。正在回滚事务。错误详情: {e}") # Chinese print
        executor.rollback_transaction()
        raise e

# --- 新增用于实体更新的函数 ---
# --- New function for entity update ---
from .data_formatter import (
    prepare_sparql_for_attribute_supersede,
    prepare_sparql_for_attribute_correction,
    prepare_sparql_for_attribute_delete
)

def update_entity(
    entity_uri: str,
conn_manager: VirtuosoConnectionManager,
    attributes_to_add_or_update: Optional[List[Dict[str, Any]]] = None,
    attributes_to_delete: Optional[List[Dict[str, Any]]] = None,
    source_info: Optional[Dict[str, str]] = None, 
    correction_details_info: Optional[Dict[str, Any]] = None, 

) -> None:
    """
    更新指定实体的属性。
    此函数根据提供的参数，协调对实体属性的添加、更新（替换或修正）和删除操作。
    所有数据库操作都在单个事务中执行。

    参数:
    - entity_uri (str): 要更新的实体的完整URI。
    - attributes_to_add_or_update (Optional[List[Dict[str, Any]]]): 要添加或更新的属性列表。
      每个字典应包含 'property' (str), 'value' (Any), Optional 'datatype' (str)。
    - attributes_to_delete (Optional[List[Dict[str, Any]]]): 要删除的属性列表。
      每个字典应包含 'property' (str), Optional 'value' (Any), Optional 'datatype' (str)。
    - source_info (Optional[Dict[str, str]]): 新属性或替换属性的来源信息。
      对应于API请求中的 EntityUpdate.source。
    - correction_details_info (Optional[Dict[str, Any]]]): 修正操作的详细信息。
      对应于API请求中的 EntityUpdate.correction_details。包含 'targetNamedGraphUri' 和 'property_to_correct'。
    - conn_manager (VirtuosoConnectionManager): 用于管理数据库连接的连接管理器实例。

    抛出:
    - ValueError: 如果输入数据不一致或缺少执行操作所必需的信息 (例如，Scenario 1缺少source_info)。
    - Exception: 如果在SPARQL执行过程中发生任何其他错误 (例如数据库错误)，异常将被重新抛出。
    """
    
    # 1. 初始化一个空列表 all_sparql_queries 来收集所有需要执行的SPARQL语句。
    all_sparql_queries: List[str] = []

    # 确保传入的列表参数如果为None，则视为空列表，以便于后续处理
    if attributes_to_add_or_update is None:
        attributes_to_add_or_update = []
    if attributes_to_delete is None:
        attributes_to_delete = []

    # 2. 处理属性删除 (attributes_to_delete):
    if attributes_to_delete:
        print(f"信息：正在为实体 <{entity_uri}> 准备属性删除查询。")
        delete_queries = prepare_sparql_for_attribute_delete(entity_uri, attributes_to_delete)
        all_sparql_queries.extend(delete_queries)
        print(f"信息：已为属性删除生成 {len(delete_queries)} 条查询。")

    # 3. 处理属性添加/更新 (attributes_to_add_or_update):
    # 创建一个副本用于处理，因为我们可能会从中移除条目
    remaining_attributes_to_add_or_update = list(attributes_to_add_or_update) # 使用 list() 创建副本

    if attributes_to_add_or_update: # 检查原始列表是否非空
        # 检查是否为 Scenario 2 (修正):
        if correction_details_info and correction_details_info.get('property_to_correct') and correction_details_info.get('targetNamedGraphUri'):
            prop_to_correct_curie = correction_details_info['property_to_correct']
            target_graph = str(correction_details_info['targetNamedGraphUri']) # 确保 HttpUrl 转为 str

            attr_for_correction = None
            # 在 remaining_attributes_to_add_or_update 中查找匹配的属性
            # 注意：我们应该迭代副本，并从副本中移除
            temp_remaining_list = []
            found_correction_attr = False
            for attr_dict in remaining_attributes_to_add_or_update:
                if attr_dict.get('property') == prop_to_correct_curie and not found_correction_attr:
                    attr_for_correction = attr_dict
                    found_correction_attr = True # 标记已找到，不再将后续匹配项视为修正（如果有多个）
                    # 不立即从迭代中的列表移除，而是在构建新列表时跳过它
                else:
                    temp_remaining_list.append(attr_dict)
            
            remaining_attributes_to_add_or_update = temp_remaining_list # 更新为移除了修正属性的列表

            if attr_for_correction:
                print(f"信息：正在为实体 <{entity_uri}> 准备属性修正查询（Scenario 2）。")
                if not source_info:
                    # Scenario 2 (修正) 也需要 source_info 来记录修正操作的来源
                    raise ValueError("错误：修正操作 (Scenario 2) 需要提供 'source_info' 以记录修正的来源。")

                correction_queries = prepare_sparql_for_attribute_correction(
                    entity_uri=entity_uri,
                    property_to_correct_curie=prop_to_correct_curie,
                    new_value=attr_for_correction['value'],
                    new_value_datatype=attr_for_correction.get('datatype'),
                    target_graph_uri=target_graph,
                    source_details=source_info  # 使用顶层 source_info 作为修正操作的来源
                )
                all_sparql_queries.extend(correction_queries)
                print(f"信息：已为属性修正生成 {len(correction_queries)} 条查询。")
            elif prop_to_correct_curie: # correction_details_info 提供了 property_to_correct，但列表中没有
                raise ValueError(
                    f"错误：修正操作指定了属性 '{prop_to_correct_curie}'，"
                    f"但在 'attributes_to_add_or_update' 列表中未找到该属性的新值。"
                )
        
        # 处理剩余的 Scenario 1 (替换/添加):
        if remaining_attributes_to_add_or_update: # 如果处理完Scenario 2后列表仍不为空
            print(f"信息：正在为实体 <{entity_uri}> 准备属性替换/添加查询（Scenario 1）。")
            if not source_info:
                raise ValueError("错误：属性添加/更新操作 (Scenario 1) 需要 'source_info' 来创建新的命名图。")
            
            supersede_queries = prepare_sparql_for_attribute_supersede(
                entity_uri, 
                remaining_attributes_to_add_or_update, # 传递已移除修正属性的列表
                source_info
            )
            all_sparql_queries.extend(supersede_queries)
            print(f"信息：已为属性替换/添加生成 {len(supersede_queries)} 条查询。")

    # 4. 执行SPARQL查询 (事务处理):
    if not all_sparql_queries:
        print(f"信息：实体 <{entity_uri}> 无更新操作需要执行。")
        return

    executor = SparqlExecutor(conn_manager)
    try:
        print(f"信息：开始为实体 <{entity_uri}> 执行更新事务，共 {len(all_sparql_queries)} 条查询。")
        executor.begin_transaction()
        for i, sparql_query in enumerate(all_sparql_queries):
            print(f"信息：正在执行查询 {i+1}/{len(all_sparql_queries)}: \n{sparql_query[:200]}...") # 打印部分查询以供调试
            executor.execute_update(sparql_query)
        executor.commit_transaction()
        print(f"成功：实体 <{entity_uri}> 的更新事务已成功提交。")
    except Exception as e:
        print(f"错误：在为实体 <{entity_uri}> 执行更新事务过程中发生错误。正在回滚事务。错误详情: {e}")
        executor.rollback_transaction()
        raise e
    finally:
        # 可以在这里添加额外的清理逻辑，如果需要的话
        pass
