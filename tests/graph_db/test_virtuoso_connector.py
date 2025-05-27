# tests/graph_db/test_virtuoso_connector.py
import os
import unittest
from unittest.mock import patch, MagicMock
from SPARQLWrapper import SPARQLWrapper, JSON, RDFXML
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed, EndPointNotFound, SPARQLWrapperException

# Module under test
from src.tcm_kg_virtuoso_module.graph_db import virtuoso_connector
# Import config to allow reloading if necessary for env var testing, though less critical here
from src.tcm_kg_virtuoso_module.core import config 

class TestVirtuosoConnector(unittest.TestCase):

    @patch.dict(os.environ, {
        "VIRTUOSO_URL": "http://mockurl:8890/sparql",
        "VIRTUOSO_USER": "mockuser",
        "VIRTUOSO_PASSWORD": "mockpassword",
        "DEFAULT_GRAPH_URI": "http://mockgraph.com/MockKG"
    })
    @patch('SPARQLWrapper.SPARQLWrapper') # Mock the SPARQLWrapper class itself
    def setUp(self, MockSPARQLWrapper):
        # Reload config in case other tests changed os.environ without reload
        import importlib
        importlib.reload(config)
        importlib.reload(virtuoso_connector) # Reload connector to use reloaded config

        # Configure the mock instance that SPARQLWrapper() will return
        self.mock_sparql_instance = MockSPARQLWrapper.return_value
        self.mock_sparql_instance.query.return_value.convert.return_value = {"results": {"bindings": []}} # Default good response

        self.connector = virtuoso_connector.VirtuosoConnector(
            endpoint_url=config.VIRTUOSO_URL, # Use reloaded config
            username=config.VIRTUOSO_USER,
            password=config.VIRTUOSO_PASSWORD,
            default_graph=config.DEFAULT_GRAPH_URI
        )
        # Ensure the connector's SPARQLWrapper instance is our mock
        self.connector.sparql = self.mock_sparql_instance


    def test_initialization(self):
        self.assertEqual(self.connector.endpoint_url, "http://mockurl:8890/sparql")
        self.assertEqual(self.connector.username, "mockuser")
        self.assertEqual(self.connector.password, "mockpassword")
        self.assertEqual(self.connector.default_graph, "http://mockgraph.com/MockKG")
        self.mock_sparql_instance.setHTTPAuth.assert_called_with(SPARQLWrapper.DIGEST)
        self.mock_sparql_instance.setCredentials.assert_called_with("mockuser", "mockpassword")

    def test_execute_select_query_success(self):
        expected_result = {"results": {"bindings": [{"var": {"value": "test"}}]}}
        self.mock_sparql_instance.query.return_value.convert.return_value = expected_result
        
        query = "SELECT ?var WHERE { ?s ?p ?var }"
        result = self.connector.execute_select_query(query)
        
        self.mock_sparql_instance.setQuery.assert_called()
        self.assertIn(query, self.mock_sparql_instance.setQuery.call_args[0][0]) # Check query string is in the call
        self.mock_sparql_instance.setReturnFormat.assert_called_with(JSON)
        self.mock_sparql_instance.query.assert_called_once()
        self.assertEqual(result, expected_result)

    def test_execute_select_query_bad_formed(self):
        self.mock_sparql_instance.query.side_effect = QueryBadFormed("Bad query")
        
        query = "SELECT messed up query"
        # Use assertLogs to capture print output for errors
        with self.assertLogs(level='ERROR') as log_capture: # Assuming print calls map to ERROR in a real logger
            result = self.connector.execute_select_query(query)
        
        self.assertIsNone(result)
        self.assertTrue(any("SPARQL Query Error (Bad Formed): Bad query" in msg for msg in log_capture.output))

    def test_execute_select_query_endpoint_not_found(self):
        self.mock_sparql_instance.query.side_effect = EndPointNotFound("Endpoint missing")
        with self.assertLogs(level='ERROR') as log_capture:
            result = self.connector.execute_select_query("SELECT ?s WHERE {?s ?p ?o}")
        self.assertIsNone(result)
        self.assertTrue(any("SPARQL Endpoint Error (Not Found): Endpoint missing" in msg for msg in log_capture.output))

    def test_execute_construct_query_success(self):
        expected_rdf = "<rdf:RDF>...</rdf:RDF>" # Example RDF/XML string
        self.mock_sparql_instance.query.return_value.convert.return_value = expected_rdf
        
        query = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
        result = self.connector.execute_construct_describe_query(query, query_type="CONSTRUCT", return_format=RDFXML)
        
        self.mock_sparql_instance.setQuery.assert_called()
        self.mock_sparql_instance.setReturnFormat.assert_called_with(RDFXML)
        self.assertEqual(result, expected_rdf)

    def test_execute_update_query_success(self):
        # Reset side_effect if it was set by other tests
        self.mock_sparql_instance.query.side_effect = None 
        # For updates, .query() itself might not return much, success is no exception
        self.mock_sparql_instance.query.return_value = MagicMock() # Mock the result of query() call
        
        update_query = "INSERT DATA { <s1> <p1> <o1> }"
        success = self.connector.execute_update_query(update_query)
        
        self.mock_sparql_instance.setQuery.assert_called()
        self.assertIn(update_query, self.mock_sparql_instance.setQuery.call_args[0][0])
        self.mock_sparql_instance.setMethod.assert_called_with("POST")
        self.assertTrue(success)

    def test_execute_update_query_failure_exception(self):
        self.mock_sparql_instance.query.side_effect = SPARQLWrapperException("Update failed")
        
        with self.assertLogs(level='ERROR') as log_capture:
            success = self.connector.execute_update_query("INSERT DATA { <s2> <p2> <o2> }")
        
        self.assertFalse(success)
        self.assertTrue(any("SPARQL Wrapper Exception during update: Update failed" in msg for msg in log_capture.output))

    def test_query_string_includes_prefixes(self):
        query_body = "SELECT ?s WHERE { ?s rdf:type <http://example.com/Thing> }"
        self.connector.execute_select_query(query_body)
        
        # Check that the actual query passed to SPARQLWrapper contains prefixes
        final_query_arg = self.mock_sparql_instance.setQuery.call_args[0][0]
        self.assertIn("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>", final_query_arg)
        self.assertIn("PREFIX tcm_ont:", final_query_arg) # Check one of the custom prefixes
        self.assertTrue(final_query_arg.endswith(query_body))


if __name__ == '__main__':
    # Need to import os for the @patch.dict decorator if running this file directly
    # import os # This is already imported at the top of the file.
    unittest.main()
