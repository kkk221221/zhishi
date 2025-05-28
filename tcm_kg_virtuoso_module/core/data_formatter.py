# tcm_kg_virtuoso_module/core/data_formatter.py
from typing import Dict, List, Optional, Union, Tuple, Any  # 确保导入 Union 和 Tuple
from datetime import datetime  # 用于修正记录中的时间戳

from tcm_kg_virtuoso_module.config import settings
from tcm_kg_virtuoso_module.config.settings import DEFAULT_PREFIXES  # 显式导入以供 _expand_curie 使用
from .uri_minter import mint_entity_uri
 # 确保导入

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
        value = str(value)
    # 对于三引号字符串，内部的双引号不一定需要转义，除非它们构成三个连续的双引号。
    # 然而，转义它们是无害的，并且如果我们以后切换回单双引号或在其他地方使用转义值，则可以简化逻辑。
    # 三引号字符串主要关注的是匹配分隔符的三个引号序列和反斜杠。
    return value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t',
                                                                                                             '\\t')


# In tcm_kg_virtuoso_module/core/data_formatter.py

# COMMON_DATATYPES and _expand_curie remain the same.
# The old escape_literal_value may no longer be directly used or can be replaced.

def format_literal(value, datatype: str = None, lang: str = None) -> str:
    """
    Formats an RDF literal for SPARQL using standard short double-quoted strings ("...")
    with N-Triples style escaping, including \\uXXXX for non-ASCII characters.
    """
    s_value = str(value)  # Ensure input is a string

    escaped_chars = []
    for char_val in s_value:
        char_ord = ord(char_val)
        if char_val == '\\':
            escaped_chars.append("\\\\")
        elif char_val == '"':
            escaped_chars.append('\\"')
        elif char_val == '\n':
            escaped_chars.append("\\n")
        elif char_val == '\r':
            escaped_chars.append("\\r")
        elif char_val == '\t':
            escaped_chars.append("\\t")
        # Note: N-Triples also escapes \b and \f, but they are less common in typical text.
        # You can add them here if necessary:
        # elif char_val == '\b':
        #     escaped_chars.append("\\b")
        # elif char_val == '\f':
        #     escaped_chars.append("\\f")
        elif 32 <= char_ord <= 126:  # Printable ASCII characters (excluding \ and ")
            escaped_chars.append(char_val)
        else:  # Non-printable ASCII or any non-ASCII (Unicode) character
            if char_ord > 0xFFFF:  # Supplementary characters
                escaped_chars.append(f"\\U{char_ord:08x}")
            else:  # Basic Multilingual Plane
                escaped_chars.append(f"\\u{char_ord:04x}")

    content = "".join(escaped_chars)

    # Construct the final literal string
    if lang:
        # Ensure lang tag is valid (basic check for non-empty string)
        if isinstance(lang, str) and lang:
            return f'"{content}"@{lang}'
        else:
            print(f"WARNING: Language tag '{lang}' is invalid. Omitting language tag.")
            # Fallback to typed literal xsd:string if lang is invalid and no other datatype is given
            effective_datatype = datatype if datatype else COMMON_DATATYPES.get("string",
                                                                                "http://www.w3.org/2001/XMLSchema#string")
            return f'"{content}"^^<{effective_datatype}>'

    elif datatype:
        final_datatype_uri = None
        if datatype in COMMON_DATATYPES:
            final_datatype_uri = COMMON_DATATYPES[datatype]
        elif ":" in datatype:  # Assume if it contains a colon, it is a full URI
            final_datatype_uri = datatype

        if final_datatype_uri:
            return f'"{content}"^^<{final_datatype_uri}>'
        else:
            print(f"WARNING: Datatype '{datatype}' not recognized. Omitting datatype.")
            # Fallback to plain literal if datatype is unrecognized, though ideally literals should be typed or lang-tagged.
            return f'"{content}"'  # Or default to xsd:string
    else:
        # Default to xsd:string if no language and no datatype is specified.
        # This is a common convention for RDF plain literals.
        default_xsd_string = COMMON_DATATYPES.get("string", "http://www.w3.org/2001/XMLSchema#string")
        return f'"{content}"^^<{default_xsd_string}>'


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
        formatted_object = obj
    else:
        # 对象是URI
        formatted_object = format_uri(obj)

    return f"{formatted_subject} {formatted_predicate} {formatted_object} ."


def _expand_curie(curie: str, prefixes: Dict[str, str]) -> str:
    """
    辅助函数：展开CURIE (Compact URI Expression) 为完整的URI。

    参数:
    - curie (str): CURIE字符串，例如 "tcm-onto:hasTaste"。
    - prefixes (Dict[str, str]): 一个包含前缀到URI基础的映射字典。

    返回:
    - str: 展开后的完整URI。如果CURIE不包含':'，或者前缀未在prefixes中找到，则假定输入已经是完整URI或需要作为错误处理（当前实现是返回原始字符串）。
    """
    if ":" in curie:
        prefix, local_part = curie.split(":", 1)
        base_uri = prefixes.get(prefix)
        if base_uri:
            return base_uri + local_part
        else:
            # 前缀未找到，可能是一个错误或需要不同的处理方式
            print(f"警告：CURIE前缀 '{prefix}' 在提供的映射中未找到。CURIE: '{curie}'")  # 中文警告
            return curie  # 或者抛出异常: raise ValueError(f"Prefix '{prefix}' not found in provided prefixes for CURIE: {curie}")
    else:
        # 没有':'，假定已经是完整URI或需要其他处理
        # 例如，可以检查它是否以 "http://" 等开头
        if curie.startswith(("http://", "https://", "urn:")):
            return curie
        else:
            print(f"警告：输入值 '{curie}' 不是有效的CURIE且不是可识别的完整URI。")  # 中文警告
            return curie  # 或者抛出异常


# --- 函数 prepare_entity_sparql_insert 修改开始 ---
def prepare_entity_sparql_insert(
        entity_type_name: str,
        entity_label: str,
        entity_properties: Dict[str, Union[str, List[str]]],
        source_details: Dict[str, str],
        entity_id_args: Optional[List[str]] = None
) -> Tuple[str, str]:
    # from .source_manager import create_source_metadata # Already imported at module level

    entity_class_uri = _expand_curie(f"tcm-onto:{entity_type_name}", DEFAULT_PREFIXES)
    entity_uri = mint_entity_uri(entity_type_name, entity_label, *(entity_id_args if entity_id_args else []))

    # Use the imported 'settings' module directly
    CONFIG = settings.get_settings() # Get settings instance using the imported 'settings'
    source_named_graph_uri, source_metadata_triples = create_source_metadata(**source_details)

    entity_triples_list = []
    rdf_type_uri = _expand_curie("rdf:type", DEFAULT_PREFIXES)
    rdfs_label_uri = _expand_curie("rdfs:label", DEFAULT_PREFIXES)
    xsd_string_datatype_key = "string"

    entity_triples_list.append(create_rdf_triple(entity_uri, rdf_type_uri, entity_class_uri, is_object_literal=False))
    formatted_label = format_literal(entity_label, datatype=xsd_string_datatype_key)
    entity_triples_list.append(create_rdf_triple(entity_uri, rdfs_label_uri, formatted_label, is_object_literal=True))

    for prop_curie, prop_value_or_values in entity_properties.items():
        prop_predicate_uri = _expand_curie(prop_curie, DEFAULT_PREFIXES)
        values_to_process = []
        if isinstance(prop_value_or_values, list):
            values_to_process.extend(prop_value_or_values)
        else:
            values_to_process.append(prop_value_or_values)

        for single_value in values_to_process:
            single_value_str = str(single_value)
            obj_formatted: str
            is_literal = True
            if single_value_str.startswith(("http://", "https://", "urn:")):
                obj_formatted = format_uri(single_value_str)
                is_literal = False
            else:
                obj_formatted = format_literal(single_value_str, datatype=xsd_string_datatype_key)
            entity_triples_list.append(
                create_rdf_triple(entity_uri, prop_predicate_uri, obj_formatted, is_object_literal=is_literal)
            )

    entity_triples_str = "\n".join(entity_triples_list)
    source_metadata_triples_str = "\n".join(source_metadata_triples)

    if source_metadata_triples_str:
        query_body = f"""INSERT DATA {{
    GRAPH <{source_named_graph_uri}> {{
        {entity_triples_str}
    }}
    GRAPH <{CONFIG.virtuoso_graph_uri}> {{ # Place source metadata in the configured default graph
        {source_metadata_triples_str}
    }}
}}"""
    else:
        query_body = f"""INSERT DATA {{
    GRAPH <{source_named_graph_uri}> {{
        {entity_triples_str}
    }}
}}"""

    final_sparql_query = f"SPARQL {query_body.strip()}"
    final_query_to_return = final_sparql_query.strip()

    print(
        f"DEBUG [data_formatter.prepare_entity_sparql_insert]: 返回的查询 (前70字符): '{final_query_to_return[:70]}'")

    return final_query_to_return, entity_uri

# --- 函数 prepare_entity_sparql_insert 修改结束 ---

def prepare_relationship_sparql_insert(subject_uri: str, predicate_curie: str, object_uri: str,
                                       source_details: Dict[str, str]) -> str:
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
    from .source_manager import create_source_metadata
    # 步骤2: 调用 create_source_metadata 获取来源图URI和来源元数据三元组
    source_named_graph_uri, source_metadata_triples = create_source_metadata(**source_details)

    # 步骤3: 展开谓词CURIE为完整URI
    expanded_predicate_uri = _expand_curie(predicate_curie, DEFAULT_PREFIXES)

    # 步骤4 & 5: 创建关系三元组字符串 (宾语不是字面量)
    # create_rdf_triple 会处理主语、谓词、宾语的URI格式化 (添加尖括号)
    relationship_triple_string = create_rdf_triple(subject_uri, expanded_predicate_uri, object_uri,
                                                   is_object_literal=False)

    # 步骤6: 构建SPARQL INSERT DATA查询
    all_source_metadata_triples_string = "\n".join(source_metadata_triples)

    sparql_query = f"""
SPARQL INSERT DATA {{
    GRAPH <{source_named_graph_uri}> {{
        {relationship_triple_string}
    }}
    {all_source_metadata_triples_string}
}}
"""
    # 步骤7: 返回完整的SPARQL查询字符串
    return sparql_query.strip()


# --- 新增用于实体更新的SPARQL准备函数 ---

from .source_manager import create_source_metadata
# from datetime import datetime # 已在模块顶部导入

def prepare_sparql_for_attribute_supersede(
        entity_uri: str,
        attributes_to_add: List[Dict[str, Any]],
        # 每个字典包含 'property': str (CURIE), 'value': Any, 'datatype': Optional[str]
        source_details: Dict[str, str]  # 用于 create_source_metadata
) -> List[str]:
    """
    为Scenario 1（替换属性）准备SPARQL查询。
    此函数处理 "attributes_to_add_or_update" 列表中的条目，这些条目不通过 "correction_details" 处理。
    它首先删除指定实体和属性的所有现有三元组，然后在与新来源关联的新命名图中插入新值。
    """
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

        # 4.e. 生成删除查询: 删除指定实体和属性的所有现有三元组 (在任何图中)
        delete_query = f"""
SPARQL DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} ?old_value . }} }}
WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} ?old_value . }} }};
"""
        sparql_queries.append(delete_query.strip())

        # 4.f. 准备新值
        formatted_new_value: str
        is_new_value_literal = True  # 假设新值是字面量
        # 检查 prop_value 是否为 HttpUrl 实例或表示URI的字符串
        # from pydantic import HttpUrl (假设 HttpUrl 可能被传入，但通常在API层已转为str)
        if isinstance(prop_value, str) and prop_value.startswith(("http://", "https://", "urn:")):
            formatted_new_value = format_uri(prop_value)  # 如果是URI，格式化为URI
            is_new_value_literal = False  # 标记为非字面量
        else:
            formatted_new_value = format_literal(prop_value, datatype=prop_datatype)  # 否则格式化为字面量

        # 4.g. 生成插入新值的查询
        # 使用 create_rdf_triple 生成标准的三元组字符串 (包含末尾的点号)
        new_triple = create_rdf_triple(entity_uri, expanded_prop_uri, formatted_new_value,
                                       is_object_literal=is_new_value_literal)

        insert_new_triple_query = f"""
SPARQL INSERT DATA {{ GRAPH <{new_source_named_graph_uri}> {{ {new_triple} }} }};
"""  # new_triple 自身已包含句点
        sparql_queries.append(insert_new_triple_query.strip())

    # 5. 生成插入来源元数据的查询 (如果存在元数据三元组)
    if source_metadata_triples:
        merged_source_metadata_triples_string = "\n".join(source_metadata_triples)
        insert_source_metadata_query = f"""
SPARQL INSERT DATA {{
{merged_source_metadata_triples_string}
}};
"""
        sparql_queries.append(insert_source_metadata_query.strip())

    # 6. 返回SPARQL查询列表
    return sparql_queries


def prepare_sparql_for_attribute_correction(
        entity_uri: str,
        property_to_correct_curie: str,  # 来自 correction_details.property_to_correct
        new_value: Any,  # 来自 attributes_to_add_or_update 中匹配的条目
        new_value_datatype: Optional[str],  # 来自 attributes_to_add_or_update 中匹配的条目
        target_graph_uri: str,  # 来自 correction_details.targetNamedGraphUri
        source_details: Dict[str, str]  # 当前PUT请求的source，用于更新目标图的元数据
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
    formatted_prop_uri = format_uri(expanded_prop_uri)  # 确保属性URI也带尖括号

    # 3. 格式化新值
    formatted_new_value: str
    is_new_value_literal = True  # 假设新值是字面量
    if isinstance(new_value, str) and new_value.startswith(("http://", "https://", "urn:")):
        formatted_new_value = format_uri(new_value)  # 如果是URI，格式化为URI
        is_new_value_literal = False  # 标记为非字面量
    else:
        formatted_new_value = format_literal(new_value, datatype=new_value_datatype)  # 否则格式化为字面量

    # 4. 生成删除旧值的查询 (在目标图中)
    # 使用 WITH <graph_uri> DELETE { ... } WHERE { ... } 确保操作在特定图内。
    # ?old_value 较为鲁棒，如果确切的旧值未知或要删除所有匹配属性的旧值。
    # `WITH <graph> DELETE ... WHERE ...` 是标准的 SPARQL 1.1 Update 结构。
    delete_old_value_query = f"""
WITH <{target_graph_uri}>
DELETE {{ {formatted_entity_uri} {formatted_prop_uri} ?old_value . }}
WHERE {{ {formatted_entity_uri} {formatted_prop_uri} ?old_value . }};
"""
    sparql_queries.append(delete_old_value_query.strip())

    # 5. 生成插入新值的查询 (在目标图中)
    # 使用 create_rdf_triple 生成标准的三元组字符串
    new_corrected_triple = create_rdf_triple(entity_uri, expanded_prop_uri, formatted_new_value,
                                             is_object_literal=is_new_value_literal)
    insert_new_value_query = f"""
INSERT DATA {{ GRAPH <{target_graph_uri}> {{ {new_corrected_triple} }} }};
"""  # new_corrected_triple 自身已包含句点
    sparql_queries.append(insert_new_value_query.strip())

    # 6. 生成更新目标图来源元数据的查询 (添加修正说明)
    tcm_correctionNote_curie = "tcm-onto:correctionNote"  # 假设此CURIE已定义
    tcm_correctionNote_uri = _expand_curie(tcm_correctionNote_curie, DEFAULT_PREFIXES)

    # 获取当前时间并格式化为ISO 8601字符串
    correction_timestamp = datetime.now().isoformat()

    # 构建修正说明文本，可以包含更多细节
    citation_info = source_details.get('citation', '未提供引用')
    original_text_info = source_details.get('original_text', '未提供原始文本')
    doc_id_info = source_details.get('document_identifier', '未提供文档ID')

    correction_text = (
        f"属性 {property_to_correct_curie} 于 {correction_timestamp} 被修正。"
        f"新值为 '{str(new_value)}'。"
        f"依据来源：引用='{citation_info}', 原始文本='{original_text_info}', 文档ID='{doc_id_info}'。"
    )
    # 修正说明作为字符串字面量
    formatted_correction_note = format_literal(correction_text,
                                               datatype="string")  # COMMON_DATATYPES['string'] 或 "xsd:string" 也可以

    # 修正说明是关于 target_graph_uri 的元数据，通常插入到默认图。
    # <target_graph_uri> <tcm-onto:correctionNote> "修正说明文本" .
    # create_rdf_triple 会为主语和谓词添加尖括号，为宾语（字面量）添加引号和类型。
    correction_note_triple = create_rdf_triple(target_graph_uri, tcm_correctionNote_uri, formatted_correction_note,
                                               is_object_literal=True)

    insert_correction_note_query = f"""
INSERT DATA {{ {correction_note_triple} }}; 
"""  # correction_note_triple 自身已包含句点
    sparql_queries.append(insert_correction_note_query.strip())

    # 7. 返回SPARQL查询列表
    return sparql_queries


def prepare_sparql_for_attribute_delete(
        entity_uri: str,
        attributes_to_delete: List[Dict[str, Any]]
        # 每个字典包含 'property': str, 'value': Optional[Any], 'datatype': Optional[str]
) -> List[str]:
    """
    为 "attributes_to_delete" 列表中的条目准备SPARQL DELETE查询。
    """
    # 1. 初始化SPARQL查询列表
    sparql_queries: List[str] = []

    # 2. 处理每个要删除的属性
    for attr_to_del in attributes_to_delete:
        prop_curie = attr_to_del['property']
        prop_value = attr_to_del.get('value')  # 使用 .get() 因为 value 是可选的
        prop_datatype = attr_to_del.get('datatype')  # 使用 .get() 因为 datatype 是可选的

        expanded_prop_uri = _expand_curie(prop_curie, DEFAULT_PREFIXES)
        formatted_entity_uri = format_uri(entity_uri)
        formatted_prop_uri = format_uri(expanded_prop_uri)

        delete_query_segment: str
        if prop_value is not None:
            # 2.c. 如果 prop_value 存在 (删除特定值)
            formatted_value_to_delete: str
            # 检查值是否为URI
            if isinstance(prop_value, str) and prop_value.startswith(("http://", "https://", "urn:")):
                formatted_value_to_delete = format_uri(prop_value)
            else:  # 否则视为字面量
                formatted_value_to_delete = format_literal(prop_value, datatype=prop_datatype)

            # 删除特定三元组，无论它在哪个图中。
            # DELETE { GRAPH ?g { <subj> <pred> <obj_formatted> . } } WHERE { GRAPH ?g { <subj> <pred> <obj_formatted> . } }
            # 这种形式更通用，因为它不需要预先知道图的URI。
            delete_query_segment = f"""
SPARQL DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} {formatted_value_to_delete} . }} }}
WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} {formatted_value_to_delete} . }} }};
"""
        else:
            # 2.d. 如果 prop_value 不存在 (删除所有具有该属性的值)
            # 删除所有具有此主语和属性的三元组，无论宾语是什么，也无论在哪个图中。
            delete_query_segment = f"""
SPARQL DELETE {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} ?any_value . }} }}
WHERE  {{ GRAPH ?g {{ {formatted_entity_uri} {formatted_prop_uri} ?any_value . }} }};
"""
        sparql_queries.append(delete_query_segment.strip())

    # 3. 返回SPARQL查询列表
    return sparql_queries