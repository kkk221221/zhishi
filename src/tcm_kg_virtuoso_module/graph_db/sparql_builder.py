# tcm_kg_virtuoso_module/graph_db/sparql_builder.py
from ..core.config import get_sparql_prefixes

# Reusable SPARQL prefixes string
SPARQL_PREFIXES = get_sparql_prefixes()

def _format_term(term, is_uri=None):
    """
    Formats a term for SPARQL queries.
    If is_uri is True, formats as a URI.
    If is_uri is False, formats as a literal.
    If is_uri is None (default), attempts to auto-detect if it's a known prefixed URI or a full URI.
    Literals are enclosed in quotes. URIs are enclosed in angle brackets.
    Numeric literals are not enclosed in quotes.
    Boolean literals are lowercased.
    """
    if isinstance(term, (int, float, bool)):
        return str(term).lower() if isinstance(term, bool) else str(term)

    term_str = str(term)

    if is_uri is True:
        return f"<{term_str}>"
    if is_uri is False:
        # Simple literal, ensure quotes are handled if already present.
        # More sophisticated literal handling (e.g., language tags, datatypes) can be added.
        if term_str.startswith('"') and term_str.endswith('"'):
            return term_str
        return f'"{term_str}"' # Default to string literal

    # Auto-detection (basic)
    if term_str.startswith("http://") or term_str.startswith("https://") or ":" in term_str.split()[0]: # Check for full URI or prefixed name
        # Crude check for prefixed name (e.g., "rdf:type", "tcm_ont:Herb")
        # This doesn't validate against actual prefixes in NAMESPACES but is a common pattern.
        if ":" in term_str and not term_str.startswith("<"): # Likely a prefixed URI, SPARQL handles these directly
            return term_str
        return f"<{term_str}>" # Assume full URI
    
    # Default to literal if not clearly a URI
    if term_str.startswith('"') and term_str.endswith('"'):
        return term_str
    return f'"{term_str}"'


def build_insert_triples_sparql(graph_uri: str, triples_list: list[tuple[str, str, str]]) -> str:
    """
    Builds a SPARQL INSERT DATA query for a list of triples.
    Each triple is a tuple (subject, predicate, object).
    Terms are formatted automatically (URIs vs Literals).
    """
    if not triples_list:
        return ""

    triples_str = ""
    for s, p, o in triples_list:
        # For INSERT DATA, subjects and predicates are typically URIs. Objects can be URI or literal.
        # _format_term will try to guess, but for s and p, we are more certain they should be URIs or prefixed names.
        # For objects, auto-detection is generally fine.
        formatted_s = _format_term(s, is_uri=True) # Force subject as URI
        formatted_p = _format_term(p, is_uri=True) # Force predicate as URI
        formatted_o = _format_term(o)              # Auto-detect object type
        triples_str += f"  {formatted_s} {formatted_p} {formatted_o} .\n"

    sparql_query = f"""
{SPARQL_PREFIXES}

INSERT DATA {{
  GRAPH <{graph_uri}> {{
{triples_str.rstrip()}
  }}
}}
"""
    return sparql_query


def build_select_entity_properties_sparql(graph_uri: str, entity_uri: str) -> str:
    """
    Builds a SPARQL SELECT query to get all properties of a given entity.
    """
    formatted_entity_uri = _format_term(entity_uri, is_uri=True)
    
    sparql_query = f"""
{SPARQL_PREFIXES}

SELECT ?predicate ?object
WHERE {{
  GRAPH <{graph_uri}> {{
    {formatted_entity_uri} ?predicate ?object .
  }}
}}
"""
    return sparql_query

def build_delete_triples_sparql(graph_uri: str, triples_list: list[tuple[str, str, str]]) -> str:
    """
    Builds a SPARQL DELETE DATA query for a list of triples.
    Each triple is a tuple (subject, predicate, object).
    Terms are formatted automatically (URIs vs Literals).
    """
    if not triples_list:
        return ""

    triples_str = ""
    for s, p, o in triples_list:
        formatted_s = _format_term(s, is_uri=True)
        formatted_p = _format_term(p, is_uri=True)
        formatted_o = _format_term(o)
        triples_str += f"  {formatted_s} {formatted_p} {formatted_o} .\n"

    sparql_query = f"""
{SPARQL_PREFIXES}

DELETE DATA {{
  GRAPH <{graph_uri}> {{
{triples_str.rstrip()}
  }}
}}
"""
    return sparql_query


if __name__ == '__main__':
    from ..core.config import DEFAULT_GRAPH_URI, NAMESPACES

    print("--- Example INSERT Query ---")
    triples_to_insert = [
        ("tcm_entity:Herb001", "rdfs:label", "Ginseng"),
        ("tcm_entity:Herb001", "tcm_prop:hasTaste", "tcm_entity:SweetTaste"),
        ("tcm_entity:Herb001", "tcm_prop:qiAmount", 100), # Numeric literal
        ("tcm_entity:Herb001", "tcm_prop:isToxic", False) # Boolean literal
    ]
    insert_q = build_insert_triples_sparql(DEFAULT_GRAPH_URI, triples_to_insert)
    print(insert_q)

    print("\n--- Example SELECT Entity Properties Query ---")
    entity = "tcm_entity:Herb001" # Could also be a full URI like "http://example.com/entity/tcm/Herb001"
    select_q = build_select_entity_properties_sparql(DEFAULT_GRAPH_URI, entity)
    print(select_q)
    
    print("\n--- Example DELETE Query ---")
    # Typically, you'd query for specific triples to delete or use variables in a DELETE WHERE.
    # DELETE DATA is for exact known triples.
    triples_to_delete = [
        ("tcm_entity:Herb001", "tcm_prop:isToxic", False)
    ]
    delete_q = build_delete_triples_sparql(DEFAULT_GRAPH_URI, triples_to_delete)
    print(delete_q)

    print("\n--- Test _format_term ---")
    print(f"'http://example.com/uri' (auto) -> {_format_term('http://example.com/uri')}")
    print(f"'http://example.com/uri' (is_uri=True) -> {_format_term('http://example.com/uri', is_uri=True)}")
    print(f"'custom:ID001' (auto) -> {_format_term('custom:ID001')}")
    print(f"'custom:ID001' (is_uri=True) -> {_format_term('custom:ID001', is_uri=True)}")
    print(f"'A literal string' (auto) -> {_format_term('A literal string')}")
    print(f"'A literal string' (is_uri=False) -> {_format_term('A literal string', is_uri=False)}")
    print(f'123 (auto) -> {_format_term(123)}')
    print(f'True (auto) -> {_format_term(True)}')
    print(f'"Already Quoted"' (auto) -> {_format_term('"Already Quoted"')})
