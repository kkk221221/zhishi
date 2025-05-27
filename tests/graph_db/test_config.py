# tests/graph_db/test_config.py
import os
import unittest
from unittest.mock import patch
from src.tcm_kg_virtuoso_module.core import config

class TestConfig(unittest.TestCase):

    def test_default_values_without_env(self):
        # Test that defaults are loaded if .env variables are not set
        with patch.dict(os.environ, {}, clear=True):
            # Reload config module to re-evaluate getenv calls
            import importlib
            importlib.reload(config)
            self.assertEqual(config.VIRTUOSO_URL, "http://localhost:8890/sparql")
            self.assertEqual(config.VIRTUOSO_USER, "dba")
            self.assertEqual(config.VIRTUOSO_PASSWORD, "dba")
            self.assertEqual(config.DEFAULT_GRAPH_URI, "http://localhost:8890/TCMKG")
            self.assertTrue("tcm_ont" in config.NAMESPACES)
            self.assertEqual(config.NAMESPACES["tcm_ont"], "http://example.com/ontology/tcm#")

    @patch.dict(os.environ, {
        "VIRTUOSO_URL": "http://testurl:1234/sparql",
        "VIRTUOSO_USER": "testuser",
        "VIRTUOSO_PASSWORD": "testpassword",
        "DEFAULT_GRAPH_URI": "http://testgraph.com/MyKG",
        "TCM_ONT_PREFIX": "http://custom.com/ont#",
    })
    def test_values_from_env(self):
        import importlib
        importlib.reload(config) # Reload to pick up mocked env variables
        self.assertEqual(config.VIRTUOSO_URL, "http://testurl:1234/sparql")
        self.assertEqual(config.VIRTUOSO_USER, "testuser")
        self.assertEqual(config.VIRTUOSO_PASSWORD, "testpassword")
        self.assertEqual(config.DEFAULT_GRAPH_URI, "http://testgraph.com/MyKG")
        self.assertEqual(config.NAMESPACES["tcm_ont"], "http://custom.com/ont#")

    def test_get_sparql_prefixes(self):
        import importlib
        importlib.reload(config) # Ensure config is loaded with its current state
        prefixes_str = config.get_sparql_prefixes()
        self.assertIn("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>", prefixes_str)
        self.assertIn(f"PREFIX tcm_ont: <{config.NAMESPACES['tcm_ont']}>", prefixes_str)
        # Check that all namespaces are included
        for prefix, uri in config.NAMESPACES.items():
            self.assertIn(f"PREFIX {prefix}: <{uri}>", prefixes_str)

if __name__ == '__main__':
    unittest.main()
