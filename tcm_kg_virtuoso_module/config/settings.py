# config/settings.py
VIRTUOSO_HOST = "localhost"
VIRTUOSO_PORT = 1111 # Default Virtuoso port
VIRTUOSO_USER = "dba"
VIRTUOSO_PASSWORD = "dba"
VIRTUOSO_DSN = f"VOS_DSN={VIRTUOSO_HOST}:{VIRTUOSO_PORT}" # Or specific DSN for your driver

BASE_URI = "http://tcm.example.org/"
ENTITY_BASE_URI = f"{BASE_URI}entity/"
ONTOLOGY_BASE_URI = f"{BASE_URI}ontology/"
SOURCE_BASE_URI = f"{BASE_URI}source/"

# Common prefixes for SPARQL
DEFAULT_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dcterms": "http://purl.org/dc/terms/",
    "tcm-entity": ENTITY_BASE_URI,
    "tcm-onto": ONTOLOGY_BASE_URI, # Your custom ontology prefix
    "tcm-source": SOURCE_BASE_URI,
}
