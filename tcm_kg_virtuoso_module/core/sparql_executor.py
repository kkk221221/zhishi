from typing import List, Dict, Any, Optional
from SPARQLWrapper import SPARQLWrapper, JSON, POST 

from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager

class SparqlExecutor:
    def __init__(self, connection_manager: VirtuosoConnectionManager):
        self.connection_manager = connection_manager

    def _get_sparql_wrapper(self) -> SPARQLWrapper:
        sparql_wrapper = self.connection_manager.get_sparql_wrapper_instance()
        if not sparql_wrapper:
            raise Exception("Failed to get SPARQLWrapper instance from ConnectionManager")
        return sparql_wrapper

    def execute_select(self, query: str) -> List[Dict[str, Any]]:
        sparql = self._get_sparql_wrapper()
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        # Consider sparql.setMethod(POST) if queries can be large
        try:
            print(f"Executing SELECT query:\n{query}") # Escaped newline for subtask
            results = sparql.queryAndConvert()
            return results.get("results", {}).get("bindings", [])
        except Exception as e:
            print(f"Error executing SELECT query: {e}\nQuery:\n{query}") # Escaped newline
            raise

    def execute_update(self, query: str) -> bool:
        sparql = self._get_sparql_wrapper()
        sparql.setQuery(query)
        sparql.setMethod(POST)
        try:
            print(f"Executing UPDATE query:\n{query}") # Escaped newline
            sparql.query() # Executes the update
            print(f"Update query executed successfully.")
            return True 
        except Exception as e:
            print(f"Error executing UPDATE query: {e}\nQuery:\n{query}") # Escaped newline
            raise

# Transaction methods (begin_transaction, commit_transaction, rollback_transaction)
# are removed as they don't directly map to standard SPARQLWrapper operations.
