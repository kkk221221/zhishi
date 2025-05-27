# tests/api/v1/test_relationship_routes.py
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from tcm_kg_virtuoso_module.main_fastapi_app import app
from tcm_kg_virtuoso_module.api import dependencies
from tcm_kg_virtuoso_module.services.relationship_service import RelationshipService
from tcm_kg_virtuoso_module.models.tcm_relationship import TCMRelationship
from tcm_kg_virtuoso_module.api.schemas import CreateRelationshipSchema, RelationshipSchema, DeleteRelationshipSchema

client = TestClient(app)

mock_relationship_service = MagicMock(spec=RelationshipService)

def override_get_relationship_service():
    return mock_relationship_service

app.dependency_overrides[dependencies.get_relationship_service] = override_get_relationship_service


class TestRelationshipRoutes(unittest.TestCase):

    def setUp(self):
        mock_relationship_service.reset_mock()

    def test_create_relationship_success(self):
        req_data = CreateRelationshipSchema(
            source_uri="http://s.com/s1",
            predicate_uri="http://p.com/p1",
            target_uri="http://o.com/o1"
        )
        mock_relationship_service.add_relationship.return_value = True
        
        response = client.post("/api/v1/relationships/", json=req_data.dict())
        
        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        self.assertEqual(response_data["source_uri"], str(req_data.source_uri))
        self.assertEqual(response_data["predicate_uri"], str(req_data.predicate_uri))
        self.assertEqual(response_data["target_uri"], str(req_data.target_uri))
        
        mock_relationship_service.add_relationship.assert_called_once()
        added_rel_arg = mock_relationship_service.add_relationship.call_args[0][0]
        self.assertIsInstance(added_rel_arg, TCMRelationship)
        self.assertEqual(str(added_rel_arg.source_uri), str(req_data.source_uri))


    def test_get_relationships_for_entity_success(self):
        entity_uri = "http://example.com/entity/herb/H001"
        mock_rels = [
            TCMRelationship("http://s.com/s1", "http://p.com/p1", "http://o.com/o1"),
            TCMRelationship(entity_uri, "http://p.com/p2", "http://o.com/o2")
        ]
        mock_relationship_service.get_relationships_for_entity.return_value = mock_rels
        
        response = client.get(f"/api/v1/relationships/for-entity/{entity_uri}?direction=all")
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data), 2)
        self.assertEqual(response_data[1]["source_uri"], entity_uri)
        mock_relationship_service.get_relationships_for_entity.assert_called_once_with(entity_uri, "all")

    def test_get_relationships_for_entity_not_found_empty_list(self):
        entity_uri = "http://example.com/entity/herb/H002"
        mock_relationship_service.get_relationships_for_entity.return_value = [] # 空列表
        
        response = client.get(f"/api/v1/relationships/for-entity/{entity_uri}")
        self.assertEqual(response.status_code, 200) # 返回空列表，非404
        self.assertEqual(response.json(), [])


    def test_delete_specific_relationship_success(self):
        req_data = DeleteRelationshipSchema(
            source_uri="http://s.com/s_del",
            predicate_uri="http://p.com/p_del",
            target_uri="http://o.com/o_del"
        )
        mock_relationship_service.delete_relationship.return_value = True
        
        response = client.post("/api/v1/relationships/delete", json=req_data.dict())
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("关系已成功删除", response.json()["message"])
        mock_relationship_service.delete_relationship.assert_called_once_with(
            source_uri=str(req_data.source_uri),
            predicate_uri=str(req_data.predicate_uri),
            target_uri=str(req_data.target_uri)
        )

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

if __name__ == '__main__':
    unittest.main()
