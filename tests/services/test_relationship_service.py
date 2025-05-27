# tests/services/test_relationship_service.py
import unittest
from unittest.mock import MagicMock, patch
from src.tcm_kg_virtuoso_module.services.relationship_service import RelationshipService
from src.tcm_kg_virtuoso_module.models.tcm_relationship import TCMRelationship
from src.tcm_kg_virtuoso_module.graph_db.virtuoso_connector import VirtuosoConnector
from src.tcm_kg_virtuoso_module.core import config as app_config # 实际配置

class TestRelationshipService(unittest.TestCase):

    def setUp(self):
        self.mock_connector = MagicMock(spec=VirtuosoConnector)
        self.mock_config = MagicMock() # 使用MagicMock模拟配置
        self.mock_config.DEFAULT_GRAPH_URI = "http://test.com/graph"
        self.mock_config.NAMESPACES = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "tcm_prop": "http://example.com/property/tcm#",
            "tcm_entity": "http://example.com/entity/tcm/"
        }
        
        self.relationship_service = RelationshipService(connector=self.mock_connector, config_module=self.mock_config)

    @patch('src.tcm_kg_virtuoso_module.graph_db.sparql_builder.build_insert_triples_sparql')
    def test_add_relationship_success(self, mock_build_insert):
        source_uri = self.mock_config.NAMESPACES["tcm_entity"] + "Herb001"
        predicate_uri = self.mock_config.NAMESPACES["tcm_prop"] + "hasEffect"
        target_uri = self.mock_config.NAMESPACES["tcm_entity"] + "Effect001"
        
        relationship = TCMRelationship(source_uri, predicate_uri, target_uri)
        
        expected_sparql = "INSERT DATA { ... }"
        mock_build_insert.return_value = expected_sparql
        self.mock_connector.execute_update_query.return_value = True

        result = self.relationship_service.add_relationship(relationship)

        self.assertTrue(result)
        mock_build_insert.assert_called_once_with(
            graph_uri=self.mock_config.DEFAULT_GRAPH_URI,
            triples_list=[(source_uri, predicate_uri, target_uri)]
        )
        self.mock_connector.execute_update_query.assert_called_once_with(expected_sparql)

    def test_add_relationship_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "关系中的 '源实体URI' .* 无效"):
            self.relationship_service.add_relationship(TCMRelationship("invalid s", "p", "o"))
        with self.assertRaisesRegex(ValueError, "关系中的 '谓词URI' .* 无效"):
            self.relationship_service.add_relationship(TCMRelationship(self.mock_config.NAMESPACES["tcm_entity"]+"s", "invalid p", "o"))
        # Target URI validation might depend on whether it's a literal or URI
        # Current TCMRelationship model implies target_uri is a URI string.

    def test_get_relationships_for_entity_outgoing(self):
        entity_uri = self.mock_config.NAMESPACES["tcm_entity"] + "Herb003"
        
        db_results = {
            "results": {
                "bindings": [
                    {
                        "s": {"type": "uri", "value": entity_uri},
                        "p": {"type": "uri", "value": self.mock_config.NAMESPACES["tcm_prop"] + "hasTaste"},
                        "o": {"type": "uri", "value": self.mock_config.NAMESPACES["tcm_entity"] + "SweetTaste"}
                    }
                ]
            }
        }
        self.mock_connector.execute_select_query.return_value = db_results

        relationships = self.relationship_service.get_relationships_for_entity(entity_uri, direction="outgoing")

        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0].source_uri, entity_uri)
        self.assertEqual(relationships[0].predicate_uri, self.mock_config.NAMESPACES["tcm_prop"] + "hasTaste")
        self.assertEqual(relationships[0].target_uri, self.mock_config.NAMESPACES["tcm_entity"] + "SweetTaste")
        
        # 验证生成的SPARQL查询是否正确 (简化版检查)
        self.mock_connector.execute_select_query.assert_called_once()
        actual_query = self.mock_connector.execute_select_query.call_args[0][0]
        self.assertIn(f"<{entity_uri}> ?p ?o", actual_query) # 检查出向关系部分
        self.assertNotIn(f"?s ?p <{entity_uri}>", actual_query) # 不应包含入向关系部分 (如果direction="outgoing")


    def test_get_relationships_for_entity_all_directions(self):
        entity_uri = self.mock_config.NAMESPACES["tcm_entity"] + "Herb004"
        
        db_results = { # 模拟返回出向和入向关系
            "results": {
                "bindings": [
                    { # Outgoing
                        "s": {"type": "uri", "value": entity_uri},
                        "p": {"type": "uri", "value": self.mock_config.NAMESPACES["tcm_prop"] + "P1"},
                        "o": {"type": "uri", "value": self.mock_config.NAMESPACES["tcm_entity"] + "O1"}
                    },
                    { # Incoming
                        "s": {"type": "uri", "value": self.mock_config.NAMESPACES["tcm_entity"] + "S2"},
                        "p": {"type": "uri", "value": self.mock_config.NAMESPACES["tcm_prop"] + "P2"},
                        "o": {"type": "uri", "value": entity_uri}
                    }
                ]
            }
        }
        self.mock_connector.execute_select_query.return_value = db_results
        relationships = self.relationship_service.get_relationships_for_entity(entity_uri, direction="all")
        self.assertEqual(len(relationships), 2)
        # 验证生成的SPARQL查询是否正确 (简化版检查)
        actual_query = self.mock_connector.execute_select_query.call_args[0][0]
        self.assertIn(f"<{entity_uri}> ?p ?o", actual_query) 
        self.assertIn(f"?s ?p <{entity_uri}>", actual_query)
        self.assertIn("UNION", actual_query)


    def test_get_relationships_invalid_direction(self):
        with self.assertRaisesRegex(ValueError, "参数 'direction' 的值必须是 .* 之一"):
            self.relationship_service.get_relationships_for_entity("http://example.com/e1", direction="sideways")


    @patch('src.tcm_kg_virtuoso_module.graph_db.sparql_builder.build_delete_triples_sparql')
    def test_delete_relationship_success(self, mock_build_delete):
        source = self.mock_config.NAMESPACES["tcm_entity"] + "s1"
        predicate = self.mock_config.NAMESPACES["tcm_prop"] + "p1"
        target = self.mock_config.NAMESPACES["tcm_entity"] + "o1"
        
        expected_sparql = "DELETE DATA { ... }"
        mock_build_delete.return_value = expected_sparql
        self.mock_connector.execute_update_query.return_value = True

        result = self.relationship_service.delete_relationship(source, predicate, target)

        self.assertTrue(result)
        mock_build_delete.assert_called_once_with(
            graph_uri=self.mock_config.DEFAULT_GRAPH_URI,
            triples_list=[(source, predicate, target)]
        )
        self.mock_connector.execute_update_query.assert_called_once_with(expected_sparql)

    def test_delete_relationship_empty_uri(self):
        with self.assertRaisesRegex(ValueError, "删除关系时 '源实体URI' .*不能为空"):
            self.relationship_service.delete_relationship("", "p", "o")


if __name__ == '__main__':
    unittest.main()
