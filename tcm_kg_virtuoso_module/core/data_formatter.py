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
