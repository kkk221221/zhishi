# tests/graph_db/test_sparql_builder.py
import unittest
from tcm_kg_virtuoso_module.graph_db import sparql_builder
from tcm_kg_virtuoso_module.core.config import DEFAULT_GRAPH_URI, NAMESPACES

class TestSparqlBuilder(unittest.TestCase):

    def test_format_term(self):
        # URIs
        self.assertEqual(sparql_builder._format_term("http://example.com/res"), "<http://example.com/res>")
        self.assertEqual(sparql_builder._format_term("http://example.com/res", is_uri=True), "<http://example.com/res>")
        self.assertEqual(sparql_builder._format_term("custom:id123"), "custom:id123") # Prefixed name
        self.assertEqual(sparql_builder._format_term("custom:id123", is_uri=True), "<custom:id123>") # Forced as full URI

        # Literals
        self.assertEqual(sparql_builder._format_term("Hello"), '"Hello"')
        self.assertEqual(sparql_builder._format_term("Hello", is_uri=False), '"Hello"')
        self.assertEqual(sparql_builder._format_term('Already "Quoted" literal', is_uri=False), '"Already \\"Quoted\\" literal"') # Ensure quotes in literals are escaped for SPARQL if not already
        
        # Numbers
        self.assertEqual(sparql_builder._format_term(123), "123")
        self.assertEqual(sparql_builder._format_term(123.45), "123.45")
        
        # Booleans
        self.assertEqual(sparql_builder._format_term(True), "true")
        self.assertEqual(sparql_builder._format_term(False), "false")

        # Auto-detect already quoted literal
        self.assertEqual(sparql_builder._format_term('"A quoted string"'), '"A quoted string"')


    def test_build_insert_triples_sparql(self):
        graph = "http://example.com/graph"
        triples = [
            ("ex:sub1", "rdf:type", "ex:Class1"),
            ("ex:sub2", "rdfs:label", "Label for Sub2"),
            ("ex:sub3", "ex:hasValue", 100),
            ("ex:sub4", "ex:isValid", True),
        ]
        query = sparql_builder.build_insert_triples_sparql(graph, triples)

        self.assertIn(f"GRAPH <{graph}>", query)
        self.assertIn("<ex:sub1> <rdf:type> <ex:Class1> .", query) # Forced URIs for s, p
        self.assertIn("<ex:sub2> <rdfs:label> \"Label for Sub2\" .", query)
        self.assertIn("<ex:sub3> <ex:hasValue> 100 .", query)
        self.assertIn("<ex:sub4> <ex:isValid> true .", query)
        
        # Test with prefixes from config
        self.assertIn("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>", query)
        self.assertIn(f"PREFIX tcm_entity: <{NAMESPACES['tcm_entity']}>", query)


    def test_build_select_entity_properties_sparql(self):
        graph = "http://example.com/graph"
        entity_uri = "http://example.com/entity/e1"
        query = sparql_builder.build_select_entity_properties_sparql(graph, entity_uri)

        self.assertIn(f"GRAPH <{graph}>", query)
        self.assertIn(f"<{entity_uri}> ?predicate ?object .", query)
        self.assertIn("SELECT ?predicate ?object", query)
        self.assertIn("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>", query)

    def test_build_delete_triples_sparql(self):
        graph = "http://example.com/graph"
        triples = [
            ("ex:sub1", "rdf:type", "ex:Class1"),
            ("ex:sub2", "rdfs:label", "Label for Sub2"),
        ]
        query = sparql_builder.build_delete_triples_sparql(graph, triples)

        self.assertIn(f"GRAPH <{graph}>", query)
        self.assertIn("<ex:sub1> <rdf:type> <ex:Class1> .", query)
        self.assertIn("<ex:sub2> <rdfs:label> \"Label for Sub2\" .", query)
        self.assertIn("DELETE DATA", query)
        self.assertIn(f"PREFIX tcm_prop: <{NAMESPACES['tcm_prop']}>", query)

    def test_empty_triples_list(self):
        graph = "http://example.com/graph"
        self.assertEqual(sparql_builder.build_insert_triples_sparql(graph, []), "")
        self.assertEqual(sparql_builder.build_delete_triples_sparql(graph, []), "")

if __name__ == '__main__':
    unittest.main()
