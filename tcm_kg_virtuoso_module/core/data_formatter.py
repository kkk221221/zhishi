# tcm_kg_virtuoso_module/core/data_formatter.py
from typing import Dict, List, Optional # 确保类型提示在文件顶部导入
                                        # Ensure type hints are imported at the top of the file

from tcm_kg_virtuoso_module.config import settings
# DEFAULT_PREFIXES has been moved to rdf_utils.py
from .uri_minter import mint_entity_uri
from .source_manager import create_source_metadata
# Functions COMMON_DATATYPES, format_uri, escape_literal_value, format_literal, create_rdf_triple, _expand_curie
# have been moved to tcm_kg_virtuoso_module/core/rdf_utils.py
# Import them from there if needed by other functions in this file.
# For example:
from .rdf_utils import (
    COMMON_DATATYPES,
    format_uri,
    escape_literal_value,
    format_literal,
    create_rdf_triple,
    _expand_curie,
    DEFAULT_PREFIXES # Re-import if used by prepare_entity_sparql_insert
)


# --- 新增函数从这里开始 ---
# --- New functions start here ---

# _expand_curie is now in rdf_utils.py.
# Ensure it's imported if prepare_entity_sparql_insert uses it directly or indirectly.

def prepare_entity_sparql_insert(
    entity_type_name: str, 
    entity_label: str, 
    entity_properties: Dict[str, str], 
    source_details: Dict[str, str], 
    entity_id_args: Optional[List[str]] = None
) -> str:
    """
    准备用于插入实体及其元数据的SPARQL INSERT查询。

    参数:
    - entity_type_name (str): 实体类型名称 (例如, "Herb", "Formula")，用于构建 tcm-onto:{entity_type_name}。
    - entity_label (str): 实体的rdfs:label。
    - entity_properties (Dict[str, str]): 包含实体属性的字典，键是CURIE或完整URI，值是字面量值或完整URI。
    - source_details (Dict[str, str]): 传递给 create_source_metadata 的参数字典。
    - entity_id_args (Optional[List[str]]): 用于 mint_entity_uri 的附加标识符参数。

    返回:
    - str: 构造好的SPARQL INSERT DATA查询字符串。
    """
    # 1. 实体URI生成
    # 1. Entity URI Generation
    # 实体类别URI，例如 tcm-onto:Herb
    # Entity class URI, e.g., tcm-onto:Herb
    # entity_type_name 应该是像 "Herb" 这样的纯名称
    # entity_type_name should be a plain name like "Herb"
    entity_class_curie = f"tcm-onto:{entity_type_name}"
    # _expand_curie and DEFAULT_PREFIXES are now imported from rdf_utils
    entity_class_uri = _expand_curie(entity_class_curie, DEFAULT_PREFIXES)

    # 实体实例URI
    # Entity instance URI
    # mint_entity_uri 的第一个参数应该是实体类型（这里是其URI），第二个是主要标识（标签），之后是可选参数
    # The first argument to mint_entity_uri should be the entity type (here its URI), the second is the main identifier (label), followed by optional arguments.
    # 根据uri_minter.py的mint_entity_uri(entity_type: str, entity_name: str, *args: str)，
    # entity_type参数似乎期望的是字符串类型而不是完整的URI。
    # According to uri_minter.py's mint_entity_uri(entity_type: str, entity_name: str, *args: str),
    # the entity_type parameter seems to expect a string type rather than a full URI.
    # 为了保持一致性，如果mint_entity_uri期望的是类别名（如"Herb"），则直接使用entity_type_name。
    # For consistency, if mint_entity_uri expects the class name (like "Herb"), then use entity_type_name directly.
    # 假设 mint_entity_uri 的第一个参数是概念的“类型”字符串，而不是完整的类URI。
    # Assuming the first argument to mint_entity_uri is the "type" string of the concept, not the full class URI.
    entity_uri = mint_entity_uri(entity_type_name, entity_label, *(entity_id_args if entity_id_args else []))

    # 2. 来源元数据生成
    # 2. Source Metadata Generation
    # create_source_metadata 返回的是 (原始source_uri, N-Triple字符串列表)
    # create_source_metadata returns (raw source_uri, list of N-Triple strings)
    source_named_graph_uri, source_metadata_triples = create_source_metadata(**source_details)
    # source_named_graph_uri 是 mint_source_uri 的直接输出，应该是原始URI，适合 GRAPH <uri>
    # source_named_graph_uri is the direct output of mint_source_uri, should be a raw URI, suitable for GRAPH <uri>

    # 3. 实体三元组生成 (N-Triple 字符串列表)
    # 3. Entity Triples Generation (list of N-Triple strings)
    entity_triples_list = []
    
    # 常用谓词和数据类型键
    # Common predicates and datatype keys
    # _expand_curie and DEFAULT_PREFIXES are now imported from rdf_utils
    rdf_type_uri = _expand_curie("rdf:type", DEFAULT_PREFIXES)
    rdfs_label_uri = _expand_curie("rdfs:label", DEFAULT_PREFIXES)
    xsd_string_key = "string" # 用于 format_literal 的 datatype 参数
                              # Datatype parameter for format_literal

    # 三元组1: 类型声明 (entity_uri rdf:type entity_class_uri)
    # Triple 1: Type declaration
    # 对象是URI，所以 is_object_literal=False (create_rdf_triple的默认值)
    # The object is a URI, so is_object_literal=False (default for create_rdf_triple)
    # create_rdf_triple is now imported from rdf_utils
    entity_triples_list.append(create_rdf_triple(entity_uri, rdf_type_uri, entity_class_uri))

    # 三元组2: 标签 (entity_uri rdfs:label "entity_label"^^xsd:string)
    # Triple 2: Label
    # 对象是字面量
    # The object is a literal
    # format_literal is now imported from rdf_utils
    formatted_label = format_literal(entity_label, datatype=xsd_string_key)
    entity_triples_list.append(create_rdf_triple(entity_uri, rdfs_label_uri, formatted_label, is_object_literal=True))

    # 属性三元组
    # Property Triples
    for prop_curie, prop_value in entity_properties.items():
        # _expand_curie and DEFAULT_PREFIXES are now imported from rdf_utils
        prop_predicate_uri = _expand_curie(prop_curie, DEFAULT_PREFIXES)
        
        obj_formatted: str
        is_literal = True # 默认对象是字面量
                          # Default object is a literal
        if isinstance(prop_value, str) and prop_value.startswith(("http://", "https://", "urn:")):
            # 如果属性值是明显的全路径URI
            # If the property value is clearly a full path URI
            # format_uri is now imported from rdf_utils
            obj_formatted = format_uri(prop_value) # format_uri 会添加尖括号
                                                 # format_uri will add angle brackets
            is_literal = False # 对象是URI
                               # Object is a URI
        else:
            # 否则视为字面量
            # Otherwise, treat as a literal
            # format_literal is now imported from rdf_utils
            obj_formatted = format_literal(prop_value, datatype=xsd_string_key)
            # is_literal 保持 True
            # is_literal remains True
        
        # create_rdf_triple is now imported from rdf_utils
        entity_triples_list.append(
            create_rdf_triple(entity_uri, prop_predicate_uri, obj_formatted, is_object_literal=is_literal)
        )

    # 4. SPARQL查询构建
    # 4. SPARQL Query Construction
    entity_triples_str = "\n".join(entity_triples_list)
    # source_metadata_triples 已经是N-Triple字符串列表
    # source_metadata_triples is already a list of N-Triple strings
    source_metadata_triples_str = "\n".join(source_metadata_triples)

    # SPARQL查询模板
    # SPARQL query template
    # 注意: GRAPH <{source_named_graph_uri}> 中的 URI 不应再被 format_uri 包裹，
    # 因为 mint_source_uri (被 create_source_metadata 调用) 应返回原始URI。
    # Note: The URI in GRAPH <{source_named_graph_uri}> should not be wrapped by format_uri again,
    # as mint_source_uri (called by create_source_metadata) should return the raw URI.
    sparql_query = f"""
INSERT DATA {{
    GRAPH <{source_named_graph_uri}> {{
        {entity_triples_str}
    }}
    {source_metadata_triples_str}
}}
"""
    return sparql_query.strip() # 移除可能的前后空白
                                # Remove potential leading/trailing whitespace
