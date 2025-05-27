# tcm_kg_virtuoso_module/utils/uri_utils.py
import re
from urllib.parse import quote_plus, urlparse
from ..core.config import NAMESPACES

# 编译一个简单的正则表达式，用于基础的URI格式校验
# 这个正则表达式检查是否存在协议头 (e.g., http://, ftp://) 或者是否是一个已知的命名空间前缀
# 注意：这只是一个非常基础的校验，并不保证URI的绝对有效性或可解析性。
# 对于已注册的前缀，它会检查是否符合 "prefix:localname" 的格式。
KNOWN_PREFIXES_REGEX_PART = "|".join(re.escape(prefix) for prefix in NAMESPACES.keys())
URI_REGEX = re.compile(
    r'^(?:[a-zA-Z][a-zA-Z0-9+.-]*://|'  # 匹配协议头 (e.g., http://)
    r'(?:(' + KNOWN_PREFIXES_REGEX_PART + r'):))'  # 或者匹配已知前缀 (e.g., rdf:, tcm_ont:)
    r'[^\s<>"{}`|^\[\]]*$',  # URI 主体部分，不允许包含某些特殊字符
    re.IGNORECASE
)

# 一个更简单的正则表达式，用于检查是否是有效的 CURIE (Compact URI Expression) 或完整 URI
# 主要检查是否存在不允许的空格或特定分隔符，并且如果使用前缀，则前缀后必须有内容。
SIMPLE_CURIE_OR_URI_REGEX = re.compile(r"^(?:[a-zA-Z_][a-zA-Z0-9_-]*:)?[^ 	


<>"{}|\^`\[\]]*$")


def generate_entity_uri(entity_type_key: str, entity_name_or_id: str) -> str:
    """
    根据实体类型在配置中的键名和实体名称/ID生成URI。

    例如:
    generate_entity_uri("tcm_entity", "Herb001") -> "http://example.com/entity/tcm/Herb001"
    (假设 "tcm_entity" 在 NAMESPACES 中定义为 "http://example.com/entity/tcm/")

    generate_entity_uri("tcm_ont", "GinsengSymptom") -> "http://example.com/ontology/tcm#GinsengSymptom"

    参数:
        entity_type_key (str): 在 NAMESPACES 字典中定义的实体类型的基础URI的键名 (例如, "tcm_entity", "tcm_ont")。
        entity_name_or_id (str): 实体的唯一名称或ID，将附加到基础URI后面。
                                 建议使用URL安全的字符，或此函数会尝试进行编码。

    返回:
        str: 生成的完整URI。

    异常:
        ValueError: 如果 entity_type_key 在 NAMESPACES 中未定义。
    """
    if entity_type_key not in NAMESPACES:
        raise ValueError(f"命名空间前缀键 '{entity_type_key}' 在配置的 NAMESPACES 中未定义。")

    base_uri = NAMESPACES[entity_type_key]
    
    # 对名称或ID进行URL编码，以确保URI的有效性
    # quote_plus 用于路径部分，它会将空格替换为 '+'，但对于URI路径，通常期望 %20
    # 更安全的做法是只编码那些在URI中非法的字符，但这里为了简单起见，使用 quote_plus
    # 对于本体的Local Name部分，通常不需要完全的URL编码，但需要处理特殊字符
    # 简化处理：替换常见非法字符，例如空格，但不进行完整百分比编码，除非必要
    
    # 假设 entity_name_or_id 通常是sparql合规的local name，不需要额外编码
    # 如果 entity_name_or_id 可能包含空格或特殊字符，需要更严格的编码
    safe_name_or_id = str(entity_name_or_id).replace(" ", "_").replace("/", "_").replace("#", "_")
    # safe_name_or_id = quote_plus(str(entity_name_or_id))


    # 确保基础URI以 / 或 # 结尾，如果不是，则添加 /
    # 这取决于本体设计的惯例，有些本体用 # 分隔，有些用 /
    if not base_uri.endswith(("#", "/")):
        base_uri += "/"
        
    return f"{base_uri}{safe_name_or_id}"


def validate_uri_format(uri: str) -> bool:
    """
    对给定的字符串进行基础的URI格式校验。

    校验逻辑:
    1. 检查是否为空或None。
    2. 使用正则表达式 `SIMPLE_CURIE_OR_URI_REGEX` 进行校验。
       - 允许完整的URI (如 "http://example.com/path")。
       - 允许CURIE形式 (如 "rdf:type", "tcm_ont:Herb")，其中前缀必须是已知的。
       - 不允许包含空格或某些特殊字符，除非它们是协议部分的一部分或经过编码。

    参数:
        uri (str): 需要校验的URI字符串。

    返回:
        bool: 如果URI格式基本正确则返回True，否则返回False。
    """
    if not uri:
        return False

    # 使用 urlparse 检查是否为绝对URI且包含scheme和netloc
    try:
        parsed = urlparse(uri)
        if parsed.scheme and parsed.netloc: # e.g. http://example.com
            # 对于绝对URI，可以添加更多检查，例如不允许片段中的非法字符等
            # 但为了简单，这里认为 scheme 和 netloc 存在即为一种有效的绝对URI形式
            return True 
    except ValueError: # urlparse 失败通常意味着格式非常糟糕
        return False

    # 如果不是一个可解析的绝对URI，则检查是否为合法的CURIE或相对路径（无scheme但无非法字符）
    # 对于CURIE，我们检查前缀是否已知
    if ":" in uri:
        prefix = uri.split(":", 1)[0]
        if prefix in NAMESPACES:
            # 进一步检查CURIE的剩余部分是否有效 (例如，不应包含空格)
            return SIMPLE_CURIE_OR_URI_REGEX.match(uri) is not None
        else:
            # 未知前缀，但如果urlparse没有将其识别为绝对URI，则可能是一个 URN 或其他自定义 scheme
            # 此时，我们依赖 SIMPLE_CURIE_OR_URI_REGEX 进行基础字符校验
            return SIMPLE_CURIE_OR_URI_REGEX.match(uri) is not None
    else:
        # 没有冒号，不是CURIE，也不是绝对URI。可能是一个相对路径或片段。
        # 检查是否只包含合法字符。
        return SIMPLE_CURIE_OR_URI_REGEX.match(uri) is not None


if __name__ == '__main__':
    print("--- URI 生成示例 ---")
    try:
        herb_uri = generate_entity_uri("tcm_entity", "GinsengRoot 1")
        print(f"草药 'GinsengRoot 1' (tcm_entity) URI: {herb_uri}")

        symptom_uri = generate_entity_uri("tcm_ont", "HeadacheTypeA")
        print(f"症状 'HeadacheTypeA' (tcm_ont) URI: {symptom_uri}")
        
        # 尝试使用不存在的前缀键
        # generate_entity_uri("non_existent_prefix", "TestData")
    except ValueError as e:
        print(f"生成URI时出错: {e}")

    print("\n--- URI 校验示例 ---")
    valid_uris = [
        "http://example.com/resource1",
        "https://example.com/path/to/resource?query=value#fragment",
        "urn:isbn:0451450523",
        "rdf:type",
        "tcm_ont:Symptom",
        NAMESPACES["tcm_entity"] + "Herb123",
        "valid-local-name-without-prefix" # 某些场景下也可能被接受为相对URI或片段
    ]
    invalid_uris = [
        None,
        "",
        "http:// example.com/invalid space", # 包含空格
        "ftp:/no_double_slash",
        "prefix_without_colon", # 不是有效的CURIE或绝对URI
        "unknown_prefix:SomeValue", # 如果 "unknown_prefix" 不在 NAMESPACES 中, validate_uri_format 会更严格
        "<http://example.com/still_valid_if_angle_brackets_ignored_by_regex>" # 正则需要考虑这个
    ]

    for uri_to_test in valid_uris:
        is_valid = validate_uri_format(uri_to_test)
        print(f"URI: '{uri_to_test}' -> 校验结果: {'有效' if is_valid else '无效'}")

    print("\n--- 无效 URI 校验示例 ---")
    for uri_to_test in invalid_uris:
        is_valid = validate_uri_format(uri_to_test)
        print(f"URI: '{uri_to_test}' -> 校验结果: {'有效' if is_valid else '无效'}")

    # 特殊情况
    print(f"URI: 'rdf:type with space' -> 校验结果: {'有效' if validate_uri_format('rdf:type with space') else '无效'}")
    print(f"URI: '<http://example.com/with space>' -> 校验结果: {'有效' if validate_uri_format('<http://example.com/with space>') else '无效'}")
