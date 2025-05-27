# tcm_kg_virtuoso_module/core/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Virtuoso Connection Parameters
VIRTUOSO_URL = os.getenv("VIRTUOSO_URL", "http://localhost:8890/sparql")
VIRTUOSO_USER = os.getenv("VIRTUOSO_USER", "dba")
VIRTUOSO_PASSWORD = os.getenv("VIRTUOSO_PASSWORD", "dba")
# For SPARQLWrapper, the port is usually part of the URL if not default.
# If direct JDBC/ODBC, a separate port might be needed.
# VIRTUOSO_PORT = os.getenv("VIRTUOSO_PORT", "1111") 

# Default Named Graph URI
DEFAULT_GRAPH_URI = os.getenv("DEFAULT_GRAPH_URI", "http://localhost:8890/TCMKG")

# Common Namespace Prefixes
# Using a dictionary for easier management and potential use in SPARQL queries
NAMESPACES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    # Custom TCM ontology prefixes - to be defined by the user/project
    # Example:
    "tcm_ont": os.getenv("TCM_ONT_PREFIX", "http://example.com/ontology/tcm#"),
    "tcm_prop": os.getenv("TCM_PROP_PREFIX", "http://example.com/property/tcm#"),
    "tcm_entity": os.getenv("TCM_ENTITY_PREFIX", "http://example.com/entity/tcm/"),
}

def get_sparql_prefixes() -> str:
    """Returns a string of SPARQL PREFIX declarations for use in queries."""
    return "\n".join([f"PREFIX {prefix}: <{uri}>" for prefix, uri in NAMESPACES.items()])

if __name__ == '__main__':
    # Example of how to access the configurations
    print(f"Virtuoso URL: {VIRTUOSO_URL}")
    print(f"Virtuoso User: {VIRTUOSO_USER}")
    # print(f"Virtuoso Password: {VIRTUOSO_PASSWORD}") # Avoid printing passwords
    print(f"Default Graph URI: {DEFAULT_GRAPH_URI}")
    print("\nSPARQL Prefixes:")
    print(get_sparql_prefixes())
    print(f"\nCustom TCM Ontology Prefix: {NAMESPACES.get('tcm_ont')}")
