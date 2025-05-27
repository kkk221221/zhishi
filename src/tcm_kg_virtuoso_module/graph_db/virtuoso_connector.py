# tcm_kg_virtuoso_module/graph_db/virtuoso_connector.py
from SPARQLWrapper import SPARQLWrapper, JSON, XML, N3, RDFXML
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed, EndPointNotFound, SPARQLWrapperException
from ..core.config import VIRTUOSO_URL, VIRTUOSO_USER, VIRTUOSO_PASSWORD, DEFAULT_GRAPH_URI, get_sparql_prefixes
from .sparql_types import SparqlQuerySolution # Added import
from typing import Optional, Union, Dict, Any # Added typing imports

# Common return formats for SELECT queries
RETURN_FORMAT_JSON = JSON
RETURN_FORMAT_XML = XML

# Common return formats for CONSTRUCT/DESCRIBE queries
RETURN_FORMAT_N3 = N3
RETURN_FORMAT_RDFXML = RDFXML


class VirtuosoConnector:
    def __init__(self, endpoint_url=VIRTUOSO_URL, username=VIRTUOSO_USER, password=VIRTUOSO_PASSWORD, default_graph=DEFAULT_GRAPH_URI):
        self.endpoint_url = endpoint_url
        self.username = username
        self.password = password
        self.default_graph = default_graph
        
        self.sparql = SPARQLWrapper(self.endpoint_url)
        self.sparql.setHTTPAuth(SPARQLWrapper.DIGEST) # Or BASIC, if your Virtuoso is configured for it
        self.sparql.setCredentials(self.username, self.password)

        # Add default prefixes for convenience
        self.sparql_prefixes = get_sparql_prefixes()

    def _prepare_query(self, query_string: str, query_type: str = "SELECT") -> None:
        """Internal method to prepare the SPARQLWrapper object."""
        full_query = f"{self.sparql_prefixes}\n\n{query_string}"
        self.sparql.setQuery(full_query)
        
        if query_type.upper() in ["SELECT", "ASK"]:
            self.sparql.setReturnFormat(JSON) # Default to JSON for SELECT/ASK
        elif query_type.upper() in ["CONSTRUCT", "DESCRIBE"]:
            self.sparql.setReturnFormat(RDFXML) # Default to RDF/XML for graph returns
        # For UPDATE queries, setReturnFormat is not applicable in the same way.
        # SPARQLWrapper handles this via queryType or directly in execute_update.

    def execute_select_query(self, query_string: str, return_format=RETURN_FORMAT_JSON) -> Optional[SparqlQuerySolution]:
        """
        Executes a SPARQL SELECT or ASK query.
        For ASK queries, result will be {'boolean': True/False}.
        Returns results in the specified format (default JSON for SELECT/ASK).
        Returns None if an error occurs.
        """
        self._prepare_query(query_string, query_type="SELECT")
        self.sparql.setReturnFormat(return_format)
        try:
            results = self.sparql.query().convert()
            return results
        except QueryBadFormed as e:
            print(f"SPARQL Query Error (Bad Formed): {e}")
            print(f"Query: \n{self.sparql.queryString}")
        except EndPointNotFound as e:
            print(f"SPARQL Endpoint Error (Not Found): {e}")
        except SPARQLWrapperException as e:
            print(f"SPARQL Wrapper Exception: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during SELECT query execution: {e}")
        return None

    def execute_construct_describe_query(self, query_string: str, query_type: str = "CONSTRUCT", return_format=RETURN_FORMAT_RDFXML) -> Optional[Union[str, bytes]]:
        """
        Executes a SPARQL CONSTRUCT or DESCRIBE query.
        Returns results as a string (e.g., RDF/XML, Turtle) or bytes.
        Returns None if an error occurs.
        """
        if query_type.upper() not in ["CONSTRUCT", "DESCRIBE"]:
            raise ValueError("Query type must be CONSTRUCT or DESCRIBE.")
        
        self._prepare_query(query_string, query_type=query_type)
        self.sparql.setReturnFormat(return_format)
        try:
            results = self.sparql.query().convert()
            return results
        except QueryBadFormed as e:
            print(f"SPARQL Query Error (Bad Formed): {e}")
            print(f"Query: \n{self.sparql.queryString}")
        except EndPointNotFound as e:
            print(f"SPARQL Endpoint Error (Not Found): {e}")
        except SPARQLWrapperException as e:
            print(f"SPARQL Wrapper Exception: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during {query_type} query execution: {e}")
        return None

    def execute_update_query(self, update_string: str) -> bool:
        """
        Executes a SPARQL UPDATE query (INSERT, DELETE, etc.).
        Returns True if successful, False otherwise.
        Note: SPARQLWrapper's support for direct transaction management (BEGIN/COMMIT/ROLLBACK)
        is limited. Each update is typically a separate request.
        For transactional updates, a more direct Virtuoso driver or HTTP requests might be needed.
        """
        self._prepare_query(update_string, query_type="UPDATE")
        self.sparql.setMethod("POST") # Updates must be POST
        # self.sparql.setRequestMethod(SPARQLWrapper.POST) # Alternative way for some versions

        try:
            # For update queries, query().response.read() gives the response body
            # A successful update usually returns a 2xx status code with an empty or minimal body.
            # We check the response code implicitly by not getting an exception.
            self.sparql.query() 
            # print(f"Update response: {results.response.read()}") # For debugging
            return True
        except QueryBadFormed as e:
            print(f"SPARQL Update Error (Bad Formed): {e}")
            print(f"Query: \n{self.sparql.queryString}")
        except EndPointNotFound as e:
            print(f"SPARQL Endpoint Error (Not Found): {e}")
        except SPARQLWrapperException as e:
            # SPARQLWrapper might raise a generic exception for HTTP errors (4xx, 5xx) on updates.
            print(f"SPARQL Wrapper Exception during update: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during UPDATE query execution: {e}")
        return False

if __name__ == '__main__':
    # This is a placeholder for basic testing.
    # Requires a running Virtuoso instance and .env file configured.
    print("Attempting to initialize VirtuosoConnector...")
    try:
        connector = VirtuosoConnector()
        print("VirtuosoConnector initialized successfully.")

        # Example: Test with a simple ASK query
        # (Assumes default graph exists or is not strictly required for this query)
        ask_query = "ASK { ?s ?p ?o . }"
        print(f"\nExecuting ASK query: {ask_query}")
        result = connector.execute_select_query(ask_query)
        if result is not None:
            print(f"ASK Query Result: {result}") # Expected: {'head': {}, 'boolean': True/False}
        else:
            print("ASK Query failed or returned None.")

        # Example: Test with a simple SELECT query
        select_query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o . } LIMIT 3"
        print(f"\nExecuting SELECT query: {select_query}")
        result = connector.execute_select_query(select_query)
        if result is not None:
            # print(f"SELECT Query Result (JSON): {result}")
            if result.get('results', {}).get('bindings'):
                 print(f"Found {len(result['results']['bindings'])} results.")
            else:
                 print("No bindings found in SELECT results or unexpected format.")
        else:
            print("SELECT Query failed or returned None.")
            
        # Example: Test INSERT (Use with caution, modifies data)
        # Ensure your default graph is set and writable
        # insert_query = f'''
        # INSERT DATA {{
        #   GRAPH <{connector.default_graph}> {{
        #     <http://example.com/subject1> <http://example.com/predicate1> "object1" .
        #   }}
        # }}
        # '''
        # print(f"\nExecuting INSERT query...")
        # success = connector.execute_update_query(insert_query)
        # print(f"INSERT Query Success: {success}")

        # if success:
        #     # Example: Test DELETE (Use with caution)
        #     delete_query = f'''
        #     DELETE DATA {{
        #       GRAPH <{connector.default_graph}> {{
        #         <http://example.com/subject1> <http://example.com/predicate1> "object1" .
        #       }}
        #     }}
        #     '''
        #     print(f"\nExecuting DELETE query...")
        #     delete_success = connector.execute_update_query(delete_query)
        #     print(f"DELETE Query Success: {delete_success}")

    except Exception as e:
        print(f"Error during VirtuosoConnector self-test: {e}")
        print("Please ensure Virtuoso is running and .env is configured correctly.")
        print("Also, ensure SPARQLWrapper is installed (`pip install SPARQLWrapper`).")
