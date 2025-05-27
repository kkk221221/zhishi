# tests/api/v1/test_entity_routes.py
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# 应用入口点和依赖项获取函数
from src.tcm_kg_virtuoso_module.main_fastapi_app import app # 主 FastAPI 应用实例
from src.tcm_kg_virtuoso_module.api import dependencies # 依赖项模块
from src.tcm_kg_virtuoso_module.services.entity_service import EntityService
from src.tcm_kg_virtuoso_module.models.tcm_entity import TCMEntity
from src.tcm_kg_virtuoso_module.api.schemas import EntitySchema, CreateEntitySchema # Pydantic schemas

# 使用 TestClient 来发送HTTP请求到FastAPI应用
client = TestClient(app)

# Mock EntityService
mock_entity_service = MagicMock(spec=EntityService)

# 重写依赖项以使用 mock service
def override_get_entity_service():
    return mock_entity_service

app.dependency_overrides[dependencies.get_entity_service] = override_get_entity_service


class TestEntityRoutes(unittest.TestCase):

    def setUp(self):
        # 在每个测试前重置 mock 对象的状态
        mock_entity_service.reset_mock()

    def test_create_entity_success(self):
        # 准备请求数据
        test_uri_suffix = "TestHerbAPI"
        test_entity_type_key = "tcm_entity" # 假设这是config中定义的键
        test_types = ["http://example.com/ontology/tcm#Herb"]
        test_props = {"http://www.w3.org/2000/01/rdf-schema#label": "API测试草药"}
        
        request_data = CreateEntitySchema(
            uri_suffix=test_uri_suffix,
            entity_type_key_for_uri=test_entity_type_key,
            entity_types=test_types,
            properties=test_props
        )
        
        mock_entity_service.add_entity.return_value = True
        generated_uri_for_mock = f"http://example.com/entity/tcm/{test_uri_suffix}" # 假设的生成结果

        # Corrected TCMEntity instantiation
        mock_created_entity = TCMEntity(
            uri=generated_uri_for_mock, 
            entity_types=[str(t) for t in test_types], 
            properties={str(k): v for k,v in test_props.items()}
        )
        mock_entity_service.get_entity_by_uri.return_value = mock_created_entity
        
        response = client.post("/api/v1/entities/", json=request_data.dict())
        
        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        self.assertEqual(response_data["uri"], generated_uri_for_mock)
        self.assertEqual(response_data["entity_types"], test_types)
        self.assertDictEqual(response_data["properties"], test_props)
        
        mock_entity_service.add_entity.assert_called_once()
        added_entity_arg = mock_entity_service.add_entity.call_args[0][0]
        self.assertIsInstance(added_entity_arg, TCMEntity)
        self.assertEqual(added_entity_arg.uri, generated_uri_for_mock)
        self.assertEqual(added_entity_arg.entity_types, [str(t) for t in test_types]) # Compare with converted list

        mock_entity_service.get_entity_by_uri.assert_called_once_with(generated_uri_for_mock)


    def test_create_entity_missing_suffix(self):
        valid_pydantic_req = CreateEntitySchema(
            uri_suffix=None, 
            entity_type_key_for_uri="tcm_entity",
            entity_types=["http://example.com/ontology/tcm#Herb"],
            properties={"http://www.w3.org/2000/01/rdf-schema#label": "Test"}
        )

        response = client.post("/api/v1/entities/", json=valid_pydantic_req.dict(exclude_none=True)) 
        self.assertEqual(response.status_code, 400)
        self.assertIn("创建实体时必须提供 uri_suffix", response.json()["detail"])


    def test_get_entity_success(self):
        entity_uri_to_get = "http://example.com/entity/tcm/HerbExists"
        mock_db_entity = TCMEntity(
            uri=entity_uri_to_get,
            entity_types=["http://example.com/ontology/tcm#Herb"],
            properties={"http://www.w3.org/2000/01/rdf-schema#label": "存在的草药"}
        )
        mock_entity_service.get_entity_by_uri.return_value = mock_db_entity
        
        response = client.get(f"/api/v1/entities/{entity_uri_to_get}")
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["uri"], entity_uri_to_get)
        self.assertEqual(response_data["properties"]["http://www.w3.org/2000/01/rdf-schema#label"], "存在的草药")
        mock_entity_service.get_entity_by_uri.assert_called_once_with(entity_uri_to_get)

    def test_get_entity_not_found(self):
        entity_uri_not_found = "http://example.com/entity/tcm/HerbNotFound"
        mock_entity_service.get_entity_by_uri.return_value = None
        
        response = client.get(f"/api/v1/entities/{entity_uri_not_found}")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn(f"实体 <{entity_uri_not_found}> 未找到", response.json()["detail"])

    def test_get_entity_invalid_uri_format_in_service(self):
        invalid_uri_for_service = "http://example.com/entity/tcm/Herb Invalid"
        mock_entity_service.get_entity_by_uri.side_effect = ValueError("服务层校验URI格式失败")

        response = client.get(f"/api/v1/entities/{invalid_uri_for_service.replace(' ', '%20')}")
        self.assertEqual(response.status_code, 400)
        self.assertIn("无效的实体URI格式: 服务层校验URI格式失败", response.json()["detail"])


    def test_delete_entity_success(self):
        entity_uri_to_delete = "http://example.com/entity/tcm/HerbToDelete"
        mock_entity_service.delete_entity.return_value = True
        
        response = client.delete(f"/api/v1/entities/{entity_uri_to_delete}?cascade=false")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn(f"实体 <{entity_uri_to_delete}>", response.json()["message"])
        mock_entity_service.delete_entity.assert_called_once_with(entity_uri_to_delete, cascade=False)

    def test_delete_entity_cascade_success(self):
        entity_uri_to_delete_cascade = "http://example.com/entity/tcm/HerbToDeleteCascade"
        mock_entity_service.delete_entity.return_value = True
        
        response = client.delete(f"/api/v1/entities/{entity_uri_to_delete_cascade}?cascade=true")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("及相关数据", response.json()["message"])
        mock_entity_service.delete_entity.assert_called_once_with(entity_uri_to_delete_cascade, cascade=True)


    def test_delete_entity_failure_in_service(self):
        entity_uri_delete_fail = "http://example.com/entity/tcm/HerbDeleteFail"
        mock_entity_service.delete_entity.return_value = False
        
        response = client.delete(f"/api/v1/entities/{entity_uri_delete_fail}")
        
        self.assertEqual(response.status_code, 500)
        self.assertIn(f"删除实体 <{entity_uri_delete_fail}> 操作失败", response.json()["detail"])
        
    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

if __name__ == '__main__':
    unittest.main()
