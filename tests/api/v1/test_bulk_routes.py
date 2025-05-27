# tests/api/v1/test_bulk_routes.py
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.tcm_kg_virtuoso_module.main_fastapi_app import app
from src.tcm_kg_virtuoso_module.api import dependencies
from src.tcm_kg_virtuoso_module.services.import_export_service import ImportExportService
from src.tcm_kg_virtuoso_module.api.schemas import BulkInsertTriplesRequest, TripleSchema

client = TestClient(app)

mock_import_export_service = MagicMock(spec=ImportExportService)

def override_get_import_export_service():
    return mock_import_export_service

app.dependency_overrides[dependencies.get_import_export_service] = override_get_import_export_service

class TestBulkRoutes(unittest.TestCase):

    def setUp(self):
        mock_import_export_service.reset_mock()

    def test_bulk_insert_triples_success(self):
        triples_data = [
            TripleSchema(subject="http://s.com/s1_bulk", predicate="http://p.com/p1_bulk", object_val="http://o.com/o1_bulk"),
            TripleSchema(subject="http://s.com/s2_bulk", predicate="http://p.com/p2_bulk", object_val="Literal Value Bulk")
        ]
        request_payload = BulkInsertTriplesRequest(triples=triples_data, graph_uri="http://g.com/graph_bulk")
        
        mock_import_export_service.bulk_insert_triples.return_value = True
        
        response = client.post("/api/v1/bulk/triples", json=request_payload.dict())
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertIn("成功处理 2 个三元组的批量插入请求", response_data["message"])
        
        mock_import_export_service.bulk_insert_triples.assert_called_once()
        # 验证传递给服务层的数据
        args, kwargs = mock_import_export_service.bulk_insert_triples.call_args
        self.assertEqual(len(kwargs["triples"]), 2)
        self.assertEqual(kwargs["triples"][0][0], str(triples_data[0].subject)) # 主语是AnyUrl，转为str
        self.assertEqual(kwargs["triples"][1][2], triples_data[1].object_val) # 对象是Union，保持原样
        self.assertEqual(kwargs["graph_uri"], str(request_payload.graph_uri))


    def test_bulk_insert_triples_service_failure(self):
        triples_data = [
            TripleSchema(subject="http://s.com/s_fail", predicate="http://p.com/p_fail", object_val="val_fail")
        ]
        request_payload = BulkInsertTriplesRequest(triples=triples_data)
        mock_import_export_service.bulk_insert_triples.return_value = False # 模拟服务层失败
        
        response = client.post("/api/v1/bulk/triples", json=request_payload.dict())
        
        self.assertEqual(response.status_code, 500)
        self.assertIn("批量插入三元组操作未能完全成功", response.json()["detail"])

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

if __name__ == '__main__':
    unittest.main()
