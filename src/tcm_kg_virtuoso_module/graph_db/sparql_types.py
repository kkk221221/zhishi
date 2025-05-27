# src/tcm_kg_virtuoso_module/graph_db/sparql_types.py
from typing import TypedDict, List as TypingList, Optional, Literal, Dict, Any # Ensure all necessary typing imports

# TypedDicts for SPARQL JSON results (basic structure)
class SparqlBindingValue(TypedDict, total=False):
    """单个SPARQL绑定值的结构 (例如 ?s, ?p, ?o 中的一个) """
    type: Literal["uri", "literal", "typed-literal", "bnode"] # 值类型
    value: str  # 值本身
    datatype: Optional[str] # 数据类型URI (例如 xsd:integer)，仅当type为typed-literal时存在
    xml_lang: Optional[str] # 语言标签 (例如 @en)，仅当type为literal且有语言标签时存在

class SparqlBinding(TypedDict, total=False): # total=False to make all keys optional by default
    """
    SPARQL查询结果中单个绑定行 (binding) 的结构。
    键是查询中的变量名。实际使用时，键可以是任意字符串。
    为了更强的类型检查，具体的服务方法在处理绑定时，
    可以期望特定的键（如 "s", "p", "o", "predicate", "object"）。
    This defines that a binding is a dictionary where keys are strings (variable names)
    and values are SparqlBindingValue objects.
    Using Dict[str, SparqlBindingValue] would be more general if variable names are not fixed.
    For now, we'll keep it flexible here and let specific usages (like in EntityService)
    expect certain keys using .get().
    If specific keys like "predicate" and "object" are *always* expected for certain queries,
    they could be defined here, but that might make SparqlBinding less reusable for other queries.
    Let's define it as a general Dict for now, and specific TypedDicts can inherit if needed.
    However, the Pylance errors were specific to known keys, so let's try defining common ones.
    """
    s: Optional[SparqlBindingValue]
    p: Optional[SparqlBindingValue]
    o: Optional[SparqlBindingValue]
    predicate: Optional[SparqlBindingValue] # As used in EntityService
    object: Optional[SparqlBindingValue]    # As used in EntityService
    # Add other common variable names if they appear frequently and need type checking

class SparqlSelectResults(TypedDict):
    """SPARQL SELECT查询结果中 "results" 键对应的值的结构。"""
    bindings: TypingList[Dict[str, SparqlBindingValue]] # Changed SparqlBinding to Dict[str, SparqlBindingValue] for more generality

class SparqlQuerySolution(TypedDict, total=False):
    """SPARQL查询返回的完整JSON对象的顶层结构 (简化版)。"""
    head: Optional[Dict[str, TypingList[str]]]
    results: Optional[SparqlSelectResults] # results can be missing (e.g. for ASK query that failed before boolean)
    boolean: Optional[bool] # 对于ASK查询
