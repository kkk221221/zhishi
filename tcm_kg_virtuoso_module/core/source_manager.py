# tcm_kg_virtuoso_module/core/source_manager.py

from typing import List, Tuple

# 1. 导入必要的模块和函数
# 1. Import necessary modules and functions
from .uri_minter import mint_source_uri
from .rdf_utils import create_rdf_triple, format_literal # COMMON_DATATYPES 会被 format_literal 间接使用
                                                             # COMMON_DATATYPES will be indirectly used by format_literal
from tcm_kg_virtuoso_module.config import settings

def create_source_metadata(
    citation: str, 
    original_text: str, 
    document_identifier: str, 
    source_type: str, 
    source_section: str, 
    source_subsection: str, 
    *uri_args: str
) -> Tuple[str, List[str]]:
    """
    创建来源元数据，并生成相应的RDF三元组。

    参数:
    - citation (str): 引文信息。
    - original_text (str): 原始文本。
    - document_identifier (str): 文档标识符。
    - source_type (str): 来源类型 (例如, 'Book', 'JournalArticle')。
    - source_section (str): 来源章节。
    - source_subsection (str): 来源子章节。
    - *uri_args (str): 用于生成URI的附加参数。

    返回:
    - Tuple[str, List[str]]: 一个元组，包含生成的来源URI和描述该来源的RDF三元组列表。
    """

    # 2. 生成来源URI
    # 2. Generate Source URI
    # 使用 mint_source_uri 函数，并传入所有必要的参数来唯一标识这个来源。
    # Use the mint_source_uri function, passing all necessary arguments to uniquely identify this source.
    source_uri = mint_source_uri(
        source_type, 
        document_identifier, 
        source_section, 
        source_subsection, 
        *uri_args
    )

    # 3. 定义谓词和类型URI
    # 3. Define Predicate/Type URIs
    # 从 settings.DEFAULT_PREFIXES 获取基础URI，并拼接具体的属性或类型名称。
    # 使用 .get(prefix, fallback_uri_string) 来安全地获取前缀，如果前缀不存在，则提供一个备用URI字符串。
    # (在此示例中，我们假设这些前缀总是存在于 DEFAULT_PREFIXES 中，但实践中最好有备用方案或错误处理)
    # (In this example, we assume these prefixes always exist in DEFAULT_PREFIXES, but in practice, it's better to have fallbacks or error handling)
    
    # rdf:type URI
    rdf_type_uri = settings.DEFAULT_PREFIXES.get('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#') + 'type'
    
    # tcm-onto:SourceContext URI (来源上下文类型)
    # 这里我们使用 settings.ONTOLOGY_BASE_URI 来构建，因为 tcm-onto 前缀通常指向本体库的基础URI
    # Here we use settings.ONTOLOGY_BASE_URI to construct, as the tcm-onto prefix usually points to the base URI of the ontology.
    # 或者，如果 DEFAULT_PREFIXES['tcm-onto'] 已经定义为完整的 "http://tcm.example.org/ontology/"，则可以直接用它
    # Alternatively, if DEFAULT_PREFIXES['tcm-onto'] is already defined as the full "http://tcm.example.org/ontology/", it can be used directly.
    # 为了与题目描述一致 (settings.DEFAULT_PREFIXES.get('tcm-onto') + 'SourceContext')，我们假设 'tcm-onto' 键存在且是基础路径。
    # To be consistent with the problem description (settings.DEFAULT_PREFIXES.get('tcm-onto') + 'SourceContext'), we assume the 'tcm-onto' key exists and is the base path.
    # 然而，更常见的是DEFAULT_PREFIXES['tcm-onto']本身就是 "http://tcm.example.org/ontology/"，
    # 那么 tcm_onto_source_context_uri 就应该是 f"{settings.DEFAULT_PREFIXES.get('tcm-onto')}SourceContext"
    # However, it's more common for DEFAULT_PREFIXES['tcm-onto'] itself to be "http://tcm.example.org/ontology/",
    # then tcm_onto_source_context_uri should be f"{settings.DEFAULT_PREFIXES.get('tcm-onto')}SourceContext"
    # 根据 settings.py 的定义，DEFAULT_PREFIXES["tcm-onto"] = ONTOLOGY_BASE_URI = "http://tcm.example.org/ontology/"
    # According to the definition in settings.py, DEFAULT_PREFIXES["tcm-onto"] = ONTOLOGY_BASE_URI = "http://tcm.example.org/ontology/"
    # 所以，正确的做法是：
    # So, the correct way is:
    tcm_onto_source_context_uri = settings.DEFAULT_PREFIXES.get('tcm-onto', 'http://tcm.example.org/ontology/') + 'SourceContext'

    # dcterms:bibliographicCitation URI (文献引用)
    dcterms_bibliographic_citation_uri = settings.DEFAULT_PREFIXES.get('dcterms', 'http://purl.org/dc/terms/') + 'bibliographicCitation'
    
    # tcm-onto:hasOriginalText URI (拥有原始文本)
    tcm_onto_has_original_text_uri = settings.DEFAULT_PREFIXES.get('tcm-onto', 'http://tcm.example.org/ontology/') + 'hasOriginalText'

    # 4. 格式化字面量
    # 4. Format Literals
    # 引文信息和原始文本都应作为字符串类型的字面量。
    # Both citation information and original text should be literals of type string.
    formatted_citation = format_literal(citation, datatype="string")
    formatted_original_text = format_literal(original_text, datatype="string")

    # 5. 创建RDF三元组
    # 5. Create Triples
    # 使用 create_rdf_triple 函数生成N-Triple格式的字符串。
    # Use the create_rdf_triple function to generate N-Triple formatted strings.
    triples = []

    # 三元组1: (来源URI, rdf:type, tcm-onto:SourceContext)
    # Triple 1: (source_uri, rdf:type, tcm-onto:SourceContext)
    # 这是一个类型声明，表明该 source_uri 是一个来源上下文实体。对象不是字面量。
    # This is a type declaration, indicating that this source_uri is a source context entity. The object is not a literal.
    triples.append(create_rdf_triple(source_uri, rdf_type_uri, tcm_onto_source_context_uri, is_object_literal=False))

    # 三元组2: (来源URI, dcterms:bibliographicCitation, "引文字符串"^^xsd:string)
    # Triple 2: (source_uri, dcterms:bibliographicCitation, "citation_string"^^xsd:string)
    # 引文信息是一个字面量。
    # Citation information is a literal.
    triples.append(create_rdf_triple(source_uri, dcterms_bibliographic_citation_uri, formatted_citation, is_object_literal=True))

    # 三元组3: (来源URI, tcm-onto:hasOriginalText, "原始文本字符串"^^xsd:string)
    # Triple 3: (source_uri, tcm-onto:hasOriginalText, "original_text_string"^^xsd:string)
    # 原始文本是一个字面量。
    # Original text is a literal.
    triples.append(create_rdf_triple(source_uri, tcm_onto_has_original_text_uri, formatted_original_text, is_object_literal=True))

    # 6. 返回来源URI和三元组列表
    # 6. Return the source URI and the list of triple strings
    return source_uri, triples
