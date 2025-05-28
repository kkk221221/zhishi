# tcm_kg_virtuoso_module/core/data_formatter.py
from typing import Dict, List, Optional, Union, Tuple # 确保导入 Union 和 Tuple

from tcm_kg_virtuoso_module.config import settings
from tcm_kg_virtuoso_module.config.settings import DEFAULT_PREFIXES # 显式导入以供 _expand_curie 使用
from .uri_minter import mint_entity_uri




# 通用数据类型，使用 XSD 命名空间
# COMMON_DATATYPES 字典定义了常用的 RDF 数据类型，主要基于 XML Schema Definition (XSD)。
# 这些数据类型用于在生成 RDF 字面量 (literals) 时指定其确切类型。
# 例如，"string" 对应 "http://www.w3.org/2001/XMLSchema#string"，
# "integer" 对应 "http://www.w3.org/2001/XMLSchema#integer"。
COMMON_DATATYPES = {
    "string": f"{DEFAULT_PREFIXES['xsd']}string",
    "integer": f"{DEFAULT_PREFIXES['xsd']}integer",
    "decimal": f"{DEFAULT_PREFIXES['xsd']}decimal",
    "double": f"{DEFAULT_PREFIXES['xsd']}double",
    "boolean": f"{DEFAULT_PREFIXES['xsd']}boolean",
    "date": f"{DEFAULT_PREFIXES['xsd']}date",
    "dateTime": f"{DEFAULT_PREFIXES['xsd']}dateTime",
    "time": f"{DEFAULT_PREFIXES['xsd']}time",
    "anyURI": f"{DEFAULT_PREFIXES['xsd']}anyURI",
    # 根据需要可以添加更多类型
    # Add more types as needed
}

def format_uri(uri: str) -> str:
    """
    格式化URI，确保它被尖括号包围。
    如果URI已经是正确的格式（以<开头并以>结尾），则直接返回。
    例如："http://example.com" -> "<http://example.com>"
          "<http://example.com>" -> "<http://example.com>"
    """
    if not isinstance(uri, str):
        # 如果输入不是字符串，尝试转换为字符串
        # If the input is not a string, try to convert it to a string
        uri = str(uri)
    if not uri.startswith("<") and not uri.endswith(">"):
        return f"<{uri}>"
    return uri

def escape_literal_value(value: str) -> str:
    """
    为N-Triples字符串字面量转义特殊字符。
    需要转义的字符包括反斜杠 (\\), 双引号 ("), 换行符 (\\n), 回车符 (\\r), 和制表符 (\\t)。
    确保输入值是字符串类型。
    """
    if not isinstance(value, str):
        # 如果输入不是字符串，尝试转换为字符串
        # If the input is not a string, try to convert it to a string
        value = str(value)
    return value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')

def format_literal(value, datatype: str = None, lang: str = None) -> str:
    """
    格式化RDF字面量。
    使用 escape_literal_value 对输入值进行转义。
    - 如果提供了 datatype:
        - 在 COMMON_DATATYPES 中查找完整的数据类型URI。
        - 如果 datatype 本身是完整的URI (包含':')，则直接使用。
        - 格式为 "escaped_value"^^<datatype_uri>。
        - 如果 datatype 未被识别或无效，则打印警告并默认为普通字面量。
    - 否则，如果提供了 lang (语言标签):
        - 格式为 "escaped_value"@lang。 (可考虑对语言标签进行基本验证)
    - 否则，格式为普通字面量 "escaped_value"。
    - datatype 和 lang 是互斥的；优先使用 datatype。
    """
    escaped_value = escape_literal_value(value)

    if datatype:
        final_datatype_uri = None
        if datatype in COMMON_DATATYPES:
            final_datatype_uri = COMMON_DATATYPES[datatype]
        elif ":" in datatype: # 假设如果包含冒号，则它是一个完整的URI
                              # Assume if it contains a colon, it's a full URI
            final_datatype_uri = datatype
        
        if final_datatype_uri:
            return f'"{escaped_value}"^^<{final_datatype_uri}>' 
        else:
            # 如果datatype未被识别，打印警告并作为普通字面量处理
            # If datatype is not recognized, print a warning and treat as a plain literal
            print(f"警告：数据类型 '{datatype}' 未被识别。将省略数据类型。") # Chinese warning
            # Fall through to plain literal without lang
    
    if lang is not None:
        # 考虑对 lang 进行基本验证，例如符合 BCP 47 标准
        # Consider basic validation for lang, e.g., conforming to BCP 47 standards
        # 此处仅作简单示例
        # Simple example here
        if isinstance(lang, str) and lang: # 确保 lang 是一个非空字符串
                                          # Ensure lang is a non-empty string
             return f'"{escaped_value}"@{lang}'
        else:
            # 如果lang无效，打印警告并作为普通字面量处理
            # If lang is invalid, print a warning and treat as a plain literal
            print(f"警告：语言标签 '{lang}' 无效。将省略语言标签。") # Chinese warning
            # Fall through to plain literal
            return f'"{escaped_value}"'

    return f'"{escaped_value}"' # 普通字面量
                               # Plain literal

def create_rdf_triple(subject: str, predicate: str, obj: str, is_object_literal: bool = False) -> str:
    """
    创建RDF三元组字符串 (N-Triple格式)。
    - subject 和 predicate 使用 format_uri 进行格式化。
    - 如果 is_object_literal 为 True，则 obj 被假定已由 format_literal 预先格式化，直接使用。
    - 如果 is_object_literal 为 False，则 obj 使用 format_uri 进行格式化 (即对象是一个URI)。
    - 返回完整的N-Triple字符串: "{formatted_subject} {formatted_predicate} {formatted_object} ."
    """
    formatted_subject = format_uri(subject)
    formatted_predicate = format_uri(predicate)
    
    if is_object_literal:
        # 对象是字面量，应该已经由 format_literal 处理过了
        # Object is a literal, should have been processed by format_literal already
        formatted_object = obj 
    else:
        # 对象是URI
        # Object is a URI
        formatted_object = format_uri(obj)
        
    return f"{formatted_subject} {formatted_predicate} {formatted_object} ."


def _expand_curie(curie: str, prefixes: Dict[str, str]) -> str:
    """
    辅助函数：展开CURIE (Compact URI Expression) 为完整的URI。
    Helper function: Expand a CURIE (Compact URI Expression) to a full URI.

    参数:
    - curie (str): CURIE字符串，例如 "tcm-onto:hasTaste"。
    - prefixes (Dict[str, str]): 一个包含前缀到URI基础的映射字典。

    返回:
    - str: 展开后的完整URI。如果CURIE不包含':'，或者前缀未在prefixes中找到，
           则假定输入已经是完整URI或需要作为错误处理（当前实现是返回原始字符串）。
           The expanded full URI. If the CURIE does not contain ':', or the prefix is not found in prefixes,
           it is assumed that the input is already a full URI or needs error handling (current implementation returns the original string).
    """
    if ":" in curie:
        prefix, local_part = curie.split(":", 1)
        base_uri = prefixes.get(prefix)
        if base_uri:
            return base_uri + local_part
        else:
            # 前缀未找到，可能是一个错误或需要不同的处理方式
            # Prefix not found, could be an error or require different handling
            print(f"警告：CURIE前缀 '{prefix}' 在提供的映射中未找到。CURIE: '{curie}'") # Chinese warning
            return curie # 或者抛出异常: raise ValueError(f"Prefix '{prefix}' not found in provided prefixes for CURIE: {curie}")
    else:
        # 没有':'，假定已经是完整URI或需要其他处理
        # No ':', assume it's already a full URI or needs other handling
        # 例如，可以检查它是否以 "http://" 等开头
        # For example, could check if it starts with "http://" etc.
        if curie.startswith(("http://", "https://", "urn:")):
            return curie
        else:
            print(f"警告：输入值 '{curie}' 不是有效的CURIE且不是可识别的完整URI。") # Chinese warning
            return curie # 或者抛出异常

# --- 函数 prepare_entity_sparql_insert 修改开始 ---
# --- Function prepare_entity_sparql_insert modification starts here ---
def prepare_entity_sparql_insert(
    entity_type_name: str, 
    entity_label: str, 
    entity_properties: Dict[str, Union[str, List[str]]], # 允许属性值为字符串或字符串列表
                                                        # Allow property value to be string or list of strings
    source_details: Dict[str, str], 
    entity_id_args: Optional[List[str]] = None
) -> Tuple[str, str]: # 返回类型更改为元组 (SPARQL查询, 实体URI)
                      # Return type changed to tuple (SPARQL query, entity URI)
    from .source_manager import create_source_metadata
    """
    准备用于插入实体及其元数据的SPARQL INSERT查询。

    参数:
    - entity_type_name (str): 实体类型名称 (例如, "Herb", "Formula")。
    - entity_label (str): 实体的rdfs:label。
    - entity_properties (Dict[str, Union[str, List[str]]]): 包含实体属性的字典，
      键是CURIE或完整URI，值可以是单个字符串（字面量或URI）或字符串列表。
      The dictionary containing entity properties. Keys are CURIEs or full URIs. 
      Values can be a single string (literal or URI) or a list of strings.
    - source_details (Dict[str, str]): 传递给 create_source_metadata 的参数字典。
    - entity_id_args (Optional[List[str]]): 用于 mint_entity_uri 的附加标识符参数。

    返回:
    - Tuple[str, str]: 一个包含构造好的SPARQL INSERT DATA查询字符串和实体URI的元组。
                       A tuple containing the constructed SPARQL INSERT DATA query string and the entity URI.
    """
    # 1. 实体URI生成
    # 1. Entity URI Generation
    entity_class_curie = f"tcm-onto:{entity_type_name}"
    entity_class_uri = _expand_curie(entity_class_curie, DEFAULT_PREFIXES)

    # 实体实例URI - 注意：根据测试用例的期望，mint_entity_uri 的第一个参数现在是完整的类URI
    # Entity instance URI - Note: Based on test case expectations, the first argument to mint_entity_uri is now the full class URI
    entity_uri = mint_entity_uri(entity_class_uri, entity_label, *(entity_id_args if entity_id_args else []))
    formatted_entity_uri = format_uri(entity_uri) # 用于三元组构建
                                                 # Used for triple construction

    # 2. 来源元数据生成
    # 2. Source Metadata Generation
    source_named_graph_uri, source_metadata_triples = create_source_metadata(**source_details)

    # 3. 实体三元组生成 (N-Triple 字符串列表)
    # 3. Entity Triples Generation (list of N-Triple strings)
    entity_triples_list = []
    
    # 常用谓词和数据类型键
    # Common predicates and datatype keys
    rdf_type_uri = _expand_curie("rdf:type", DEFAULT_PREFIXES)
    rdfs_label_uri = _expand_curie("rdfs:label", DEFAULT_PREFIXES)
    xsd_string_key = "string" 

    # 三元组1: 类型声明 (entity_uri rdf:type entity_class_uri)
    # Triple 1: Type declaration
    entity_triples_list.append(create_rdf_triple(entity_uri, rdf_type_uri, entity_class_uri))

    # 三元组2: 标签 (entity_uri rdfs:label "entity_label"^^xsd:string)
    # Triple 2: Label
    formatted_label = format_literal(entity_label, datatype=xsd_string_key)
    entity_triples_list.append(create_rdf_triple(entity_uri, rdfs_label_uri, formatted_label, is_object_literal=True))

    # 属性三元组 - 修改以处理列表和单个值
    # Property Triples - Modified to handle lists and single values
    for prop_curie, prop_value_or_values in entity_properties.items():
        prop_predicate_uri = _expand_curie(prop_curie, DEFAULT_PREFIXES) # 使用 settings.DEFAULT_PREFIXES 或此处作用域内的 DEFAULT_PREFIXES
                                                                       # Use settings.DEFAULT_PREFIXES or DEFAULT_PREFIXES in this scope
        
        values_to_process = []
        if isinstance(prop_value_or_values, list):
            values_to_process.extend(prop_value_or_values)
        else:
            values_to_process.append(prop_value_or_values) # 将单个值视为单项列表以便统一处理
                                                         # Treat single value as a single-item list for uniform processing

        for single_value in values_to_process:
            # 确保 single_value 是字符串，因为后续的 startswith 或 format_literal 需要
            # Ensure single_value is a string for subsequent startswith or format_literal
            if not isinstance(single_value, str):
                single_value_str = str(single_value) # 例如，处理数字等类型的值
                                                     # For example, handle values of types like numbers
            else:
                single_value_str = single_value

            obj_formatted: str
            is_literal = True # 默认对象是字面量
                              # Default object is a literal
            if single_value_str.startswith(("http://", "https://", "urn:")):
                # 如果属性值是明显的全路径URI
                # If the property value is clearly a full path URI
                obj_formatted = format_uri(single_value_str)
                is_literal = False # 对象是URI
                                   # Object is a URI
            else:
                # 否则视为字面量
                # Otherwise, treat as a literal
                obj_formatted = format_literal(single_value_str, datatype=xsd_string_key)
                # is_literal 保持 True
                # is_literal remains True
            
            # 使用 create_rdf_triple 函数构建三元组
            # Use the create_rdf_triple function to construct the triple
            entity_triples_list.append(
                create_rdf_triple(entity_uri, prop_predicate_uri, obj_formatted, is_object_literal=is_literal)
            )

    # 4. SPARQL查询构建
    # 4. SPARQL Query Construction
    entity_triples_str = "\n".join(entity_triples_list)
    source_metadata_triples_str = "\n".join(source_metadata_triples)

    sparql_query = f"""
INSERT DATA {{
    GRAPH <{source_named_graph_uri}> {{
        {entity_triples_str}
    }}
    {source_metadata_triples_str}
}}
"""
    # 返回SPARQL查询和实体URI
    # Return the SPARQL query and the entity URI
    return sparql_query.strip(), entity_uri
# --- 函数 prepare_entity_sparql_insert 修改结束 ---
# --- Function prepare_entity_sparql_insert modification ends here ---

def prepare_relationship_sparql_insert(subject_uri: str, predicate_curie: str, object_uri: str, source_details: Dict[str, str]) -> str:
    """
    准备用于插入关系及其元数据的SPARQL INSERT查询。

    参数:
    - subject_uri (str): 主语的完整URI。
    - predicate_curie (str): 谓词的CURIE (例如, "tcm-onto:hasSymptom")。
    - object_uri (str): 宾语的完整URI。
    - source_details (Dict[str, str]): 传递给 create_source_metadata 的参数字典。

    返回:
    - str: 构造好的SPARQL INSERT DATA查询字符串。
    """
    # 步骤2: 调用 create_source_metadata 获取来源图URI和来源元数据三元组
    # Step 2: Call create_source_metadata to get the source graph URI and source metadata triples
    source_named_graph_uri, source_metadata_triples = create_source_metadata(**source_details)

    # 步骤3: 展开谓词CURIE为完整URI
    # Step 3: Expand the predicate CURIE to a full URI
    # 注意：根据要求，tcm-ontology 对应 DEFAULT_PREFIXES 中的 tcm-onto
    # Note: According to requirements, tcm-ontology corresponds to tcm-onto in DEFAULT_PREFIXES
    expanded_predicate_uri = _expand_curie(predicate_curie, DEFAULT_PREFIXES)

    # 步骤4: 格式化主语、谓词和宾语URI
    # Step 4: Format the subject, predicate, and object URIs
    formatted_subject_uri = format_uri(subject_uri)
    # _expand_curie 可能返回的已经是完整 URI，但为了确保尖括号，再次使用 format_uri
    # _expand_curie might already return a full URI, but use format_uri again to ensure angle brackets
    formatted_predicate_uri = format_uri(expanded_predicate_uri) 
    formatted_object_uri = format_uri(object_uri)

    # 步骤5: 创建关系三元组字符串
    # Step 5: Create the relationship triple string
    # 格式: {formatted_subject_uri} <{expanded_predicate_uri}> {formatted_object_uri} .
    # The format_uri function already adds angle brackets, so no need to add them again for expanded_predicate_uri here.
    # However, the problem description implies the predicate in the triple should be <expanded_predicate_uri>,
    # so we use formatted_predicate_uri which is <expanded_predicate_uri>
    relationship_triple_string = f"{formatted_subject_uri} {formatted_predicate_uri} {formatted_object_uri} ."

    # 步骤6: 构建SPARQL INSERT DATA查询
    # Step 6: Construct the SPARQL INSERT DATA query
    all_source_metadata_triples_string = "\n".join(source_metadata_triples)

    sparql_query = f"""
INSERT DATA {{
    GRAPH <{source_named_graph_uri}> {{
        {relationship_triple_string}
    }}
    {all_source_metadata_triples_string}
}}
"""
    # 步骤7: 返回完整的SPARQL查询字符串
    # Step 7: Return the complete SPARQL query string
    return sparql_query.strip()


# --- 新增用于实体更新的SPARQL准备函数 ---
# --- New SPARQL preparation functions for entity update ---

from .source_manager import create_source_metadata # 确保导入
from datetime import datetime # 用于修正记录中的时间戳

def prepare_sparql_for_attribute_supersede(
    entity_uri: str,
    attributes_to_add: List[Dict[str, Any]], # 每个字典包含 'property': str (CURIE), 'value': Any, 'datatype': Optional[str]
    source_details: Dict[str, str] # 用于 create_source_metadata
) -> List[str]:
    """
    为Scenario 1（替换属性）准备SPARQL查询。
    此函数处理 "attributes_to_add_or_update" 列表中的条目，这些条目不通过 "correction_details" 处理。
    它首先删除指定实体和属性的所有现有三元组，然后在与新来源关联的新命名图中插入新值。
    """
    # 1. 导入 create_source_metadata (已在函数外处理)
    # 2. 调用 create_source_metadata 生成新的来源信息
    new_source_named_graph_uri, source_metadata_triples = create_source_metadata(**source_details)

    # 3. 初始化SPARQL查询列表
    sparql_queries: List[str] = []

    # 4. 处理每个要添加/更新的属性
    for attr in attributes_to_add:
        prop_curie = attr['property']
        prop_value = attr['value']
        prop_datatype = attr.get('datatype')

        expanded_prop_uri = _expand_curie(prop_curie, DEFAULT_PREFIXES)
        formatted_entity_uri = format_uri(entity_uri)
        formatted_prop_uri = format_uri(expanded_prop_uri)

        # 4.e. 生成删除查询
        delete_query = f"""
DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} ?old_value . }} }}
WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} ?old_value . }} }};
"""
        sparql_queries.append(delete_query.strip())

        # 4.f. 准备新值
        formatted_new_value: str
        # 检查 prop_value 是否为 HttpUrl 实例或表示URI的字符串
        # from pydantic import HttpUrl # 假设 HttpUrl 可能被传入
        # if isinstance(prop_value, HttpUrl) or (isinstance(prop_value, str) and prop_value.startswith(("http://", "https://", "urn:"))):
        # 为了简化，我们依赖于 request_schemas.py 中的 AttributeUpdate.value: Any 的灵活性，
        # 并假设调用此函数前，HttpUrl 对象已转换为字符串。
        if isinstance(prop_value, str) and prop_value.startswith(("http://", "https://", "urn:")):
            formatted_new_value = format_uri(prop_value)
        else:
            formatted_new_value = format_literal(prop_value, datatype=prop_datatype)
        
        # 4.g. 生成插入新值的查询
        insert_new_triple_query = f"""
INSERT DATA {{ GRAPH <{new_source_named_graph_uri}> {{ {formatted_entity_uri} {formatted_prop_uri} {formatted_new_value} . }} }};
"""
        sparql_queries.append(insert_new_triple_query.strip())

    # 5. 生成插入来源元数据的查询
    if source_metadata_triples: # 仅当有元数据三元组时才添加
        merged_source_metadata_triples_string = "\n".join(source_metadata_triples)
        insert_source_metadata_query = f"""
INSERT DATA {{
{merged_source_metadata_triples_string}
}};
"""
        sparql_queries.append(insert_source_metadata_query.strip())
    
    # 6. 返回SPARQL查询列表
    return sparql_queries

def prepare_sparql_for_attribute_correction(
    entity_uri: str,
    property_to_correct_curie: str, # 来自 correction_details.property_to_correct
    new_value: Any, # 来自 attributes_to_add_or_update 中匹配的条目
    new_value_datatype: Optional[str], # 来自 attributes_to_add_or_update 中匹配的条目
    target_graph_uri: str, # 来自 correction_details.targetNamedGraphUri
    source_details: Dict[str, str] # 当前PUT请求的source，用于更新目标图的元数据
) -> List[str]:
    """
    为Scenario 2（在特定原始来源上下文中修正断言）准备SPARQL查询。
    它在 target_graph_uri 中删除旧的属性值，并插入新值。
    然后，它使用当前请求的 source_details 来更新 target_graph_uri 的来源元数据 (通过添加修正注释)。
    """
    # 1. 初始化SPARQL查询列表
    sparql_queries: List[str] = []

    # 2. 扩展和格式化URI
    formatted_entity_uri = format_uri(entity_uri)
    expanded_prop_uri = _expand_curie(property_to_correct_curie, DEFAULT_PREFIXES)
    formatted_prop_uri = format_uri(expanded_prop_uri)
    
    # 3. 格式化新值
    formatted_new_value: str
    if isinstance(new_value, str) and new_value.startswith(("http://", "https://", "urn:")):
        formatted_new_value = format_uri(new_value)
    else:
        formatted_new_value = format_literal(new_value, datatype=new_value_datatype)

    # 4. 生成删除旧值的查询 (在目标图中)
    # 使用 WITH <graph_uri> DELETE { ... } WHERE { ... } 确保操作在特定图内
    # Virtuoso specific: DELETE DATA FROM <graph_uri> { triple_to_delete } is simpler if we know the exact old triple.
    # However, ?old_value is more robust if the exact old value isn't known or to remove all.
    # The `WITH <graph> DELETE ... WHERE ...` is a standard SPARQL 1.1 Update construct.
    delete_old_value_query = f"""
WITH <{target_graph_uri}>
DELETE {{ {formatted_entity_uri} {formatted_prop_uri} ?old_value . }}
WHERE {{ {formatted_entity_uri} {formatted_prop_uri} ?old_value . }};
"""
    sparql_queries.append(delete_old_value_query.strip())

    # 5. 生成插入新值的查询 (在目标图中)
    insert_new_value_query = f"""
INSERT DATA {{ GRAPH <{target_graph_uri}> {{ {formatted_entity_uri} {formatted_prop_uri} {formatted_new_value} . }} }};
"""
    sparql_queries.append(insert_new_value_query.strip())

    # 6. 生成更新目标图来源元数据的查询 (添加修正说明)
    tcm_correctionNote_curie = "tcm-onto:correctionNote" # 假设这个CURIE在DEFAULT_PREFIXES中定义或可直接使用
    tcm_correctionNote_uri = _expand_curie(tcm_correctionNote_curie, DEFAULT_PREFIXES)
    
    # 获取当前时间并格式化为ISO 8601字符串
    correction_timestamp = datetime.now().isoformat()
    
    # 构建修正说明文本，可以包含更多细节
    # 例如：从 source_details 中提取引用信息
    citation_info = source_details.get('citation', '未提供引用') # Default if not provided
    original_text_info = source_details.get('original_text', '未提供原始文本') # Default
    doc_id_info = source_details.get('document_identifier', '未提供文档ID') # Default

    correction_text = (
        f"属性 {property_to_correct_curie} 于 {correction_timestamp} 被修正。"
        f"新值为 '{str(new_value)}'。"
        f"依据来源：引用='{citation_info}', 原始文本='{original_text_info}', 文档ID='{doc_id_info}'。"
    )
    
    formatted_correction_note = format_literal(correction_text, datatype="xsd:string") # 确保是字符串类型

    # 假设来源元数据是关于命名图本身的，并且存储在默认图或特定的元数据管理图中
    # 这里我们遵循之前的模式，直接在SPARQL查询的顶层插入，这通常意味着默认图
    # 如果 target_graph_uri 的元数据也存储在自身图中，则需要 GRAPH <target_graph_uri> { ... }
    # 为了简化，并遵循“添加修正说明到 target_graph_uri 的元数据中”，我们假定 target_graph_uri 本身就是其元数据的主体。
    # <target_graph_uri> <tcm-onto:correctionNote> "correction text" .
    
    # 注意：通常，命名图的URI自身作为主语，其元数据（如来源、创建日期等）在默认图或其他元数据图中描述。
    # 例如：<target_graph_uri> dcterms:created "YYYY-MM-DD" .
    # 如果要将修正说明附加到 target_graph_uri 的元数据中，SPARQL应如下：
    # INSERT DATA { <target_graph_uri> <tcm-onto:correctionNote> "text" . }
    # 这会将其添加到默认图。如果元数据在特定图中，则需要 GRAPH <metadata_graph_uri> { ... }
    # 根据现有 prepare_entity_sparql_insert 和 prepare_relationship_sparql_insert 的模式，
    # 来源元数据三元组是直接插入的，没有额外的 GRAPH 子句，这意味着它们进入默认图。
    
    insert_correction_note_query = f"""
INSERT DATA {{ <{target_graph_uri}> <{tcm_correctionNote_uri}> {formatted_correction_note} . }};
"""
    sparql_queries.append(insert_correction_note_query.strip())
    
    # 7. 返回SPARQL查询列表
    return sparql_queries

def prepare_sparql_for_attribute_delete(
    entity_uri: str,
    attributes_to_delete: List[Dict[str, Any]] # 每个字典包含 'property': str, 'value': Optional[Any], 'datatype': Optional[str]
) -> List[str]:
    """
    为 "attributes_to_delete" 列表中的条目准备SPARQL DELETE查询。
    """
    # 1. 初始化SPARQL查询列表
    sparql_queries: List[str] = []

    # 2. 处理每个要删除的属性
    for attr_to_del in attributes_to_delete:
        prop_curie = attr_to_del['property']
        prop_value = attr_to_del.get('value') # 使用 .get() 因为 value 是可选的
        prop_datatype = attr_to_del.get('datatype') # 使用 .get() 因为 datatype 是可选的

        expanded_prop_uri = _expand_curie(prop_curie, DEFAULT_PREFIXES)
        formatted_entity_uri = format_uri(entity_uri)
        formatted_prop_uri = format_uri(expanded_prop_uri)

        delete_query_segment: str
        if prop_value is not None:
            # 2.c. 如果 prop_value 存在 (删除特定值)
            formatted_value_to_delete: str
            if isinstance(prop_value, str) and prop_value.startswith(("http://", "https://", "urn:")):
                formatted_value_to_delete = format_uri(prop_value)
            else:
                formatted_value_to_delete = format_literal(prop_value, datatype=prop_datatype)
            
            delete_query_segment = f"""
DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} {formatted_value_to_delete} . }} }}
WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} {formatted_value_to_delete} . }} }};
"""
        else:
            # 2.d. 如果 prop_value 不存在 (删除所有具有该属性的值)
            delete_query_segment = f"""
DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} ?any_value . }} }}
WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} ?any_value . }} }};
"""
        sparql_queries.append(delete_query_segment.strip())
        
    # 3. 返回SPARQL查询列表
    return sparql_queries
