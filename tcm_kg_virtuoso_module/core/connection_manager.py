from SPARQLWrapper import SPARQLWrapper, JSON, POST, BASIC, DIGEST
from tcm_kg_virtuoso_module.config import settings

class VirtuosoConnectionManager:
    def __init__(self):
        host = settings.VIRTUOSO_HOST
        if not host.startswith(('http://', 'https://')):
            host = f"http://{host}" 
            
        self.endpoint_url = f"{host}:{settings.VIRTUOSO_PORT}/sparql"
        self.user = settings.VIRTUOSO_USER
        self.password = settings.VIRTUOSO_PASSWORD

        self.sparql = SPARQLWrapper(self.endpoint_url)
        
        if self.user and self.password:
            # Using DIGEST authentication. This might need to be BASIC depending on Virtuoso setup.
            self.sparql.setHTTPAuth(DIGEST) 
            self.sparql.setCredentials(self.user, self.password)

        print(f"VirtuosoConnectionManager initialized for endpoint: {self.endpoint_url}")
        if self.user:
            print(f"Using credentials for user: {self.user}")

    def get_sparql_wrapper_instance(self) -> SPARQLWrapper:
        return self.sparql

    def get_connection(self):
        # This method is kept for now for potential compatibility with SparqlExecutor,
        # but SparqlExecutor should ideally use get_sparql_wrapper_instance().
        print("Warning: VirtuosoConnectionManager.get_connection() called. Consider updating caller to use get_sparql_wrapper_instance().")
        return self.sparql
