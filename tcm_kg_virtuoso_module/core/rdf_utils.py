# tcm_kg_virtuoso_module/core/rdf_utils.py
from typing import Dict, List, Optional

from tcm_kg_virtuoso_module.config.settings import DEFAULT_PREFIXES

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

def format_literal(value, datatype: Optional[str] = None, lang: Optional[str] = None) -> str:
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
    
    if lang is not None: # Check if a language tag was provided at all
        # 考虑对 lang 进行基本验证，例如符合 BCP 47 标准
        # Consider basic validation for lang, e.g., conforming to BCP 47 standards
        # 此处仅作简单示例
        # Simple example here
        if isinstance(lang, str) and lang:  # lang is a non-empty string
                                          # Ensure lang is a non-empty string
             return f'"{escaped_value}"@{lang}'
        else:  # lang is not a string OR lang is an empty string
            # 如果lang无效，打印警告并作为普通字面量处理
            # If lang is invalid, print a warning and treat as a plain literal
            print(f"警告：语言标签 '{lang}' 无效。将省略语言标签。") # Chinese warning
            # Fall through to return plain literal

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
