# tests/services/test_entity_service.py
import unittest
from unittest.mock import MagicMock, patch, call # call 用于验证多次调用时的参数
from tcm_kg_virtuoso_module.services.entity_service import EntityService
from tcm_kg_virtuoso_module.models.tcm_entity import TCMEntity
from tcm_kg_virtuoso_module.graph_db.virtuoso_connector import VirtuosoConnector
from tcm_kg_virtuoso_module.core import config as app_config # 实际配置

class TestEntityService(unittest.TestCase):

    def setUp(self):
        # 创建 VirtuosoConnector 的 mock 对象
        self.mock_connector = MagicMock(spec=VirtuosoConnector)
        # 模拟配置模块 (如果服务内部直接使用 app_config，则不需要 mock config_module 本身)
        self.mock_config = MagicMock()
        self.mock_config.DEFAULT_GRAPH_URI = "http://test.com/graph"
        self.mock_config.NAMESPACES = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "tcm_ont": "http://example.com/ontology/tcm#",
            "tcm_prop": "http://example.com/property/tcm#",
            "tcm_entity": "http://example.com/entity/tcm/"
        }
        self.rdf_type_uri = self.mock_config.NAMESPACES["rdf"] + "type"

        # 实例化 EntityService，传入 mock 对象
        self.entity_service = EntityService(connector=self.mock_connector, config_module=self.mock_config)

    @patch('tcm_kg_virtuoso_module.graph_db.sparql_builder.build_insert_triples_sparql')
    def test_add_entity_success(self, mock_build_insert):
        # 测试成功添加实体
        test_uri = self.mock_config.NAMESPACES["tcm_entity"] + "Herb001"
        entity = TCMEntity(
            uri=test_uri,
            entity_types=[self.mock_config.NAMESPACES["tcm_ont"] + "Herb"],
            properties={self.mock_config.NAMESPACES["rdfs"] + "label": "人参"}
        )
        
        expected_sparql = "INSERT DATA { GRAPH <http://test.com/graph> { ... } }"
        mock_build_insert.return_value = expected_sparql
        self.mock_connector.execute_update_query.return_value = True # 模拟数据库操作成功

        result = self.entity_service.add_entity(entity)

        self.assertTrue(result)
        # 验证 sparql_builder.build_insert_triples_sparql 被正确调用
        expected_triples = [
            (test_uri, self.rdf_type_uri, self.mock_config.NAMESPACES["tcm_ont"] + "Herb"),
            (test_uri, self.mock_config.NAMESPACES["rdfs"] + "label", "人参")
        ]
        mock_build_insert.assert_called_once_with(
            graph_uri=self.mock_config.DEFAULT_GRAPH_URI,
            triples_list=unittest.mock.ANY # 使用 ANY 因为顺序可能不重要，或者详细比较列表内容
        )
        # 验证实际传入的triples_list内容 (需要更细致的比较)
        actual_triples_arg = mock_build_insert.call_args[1]['triples_list']
        self.assertCountEqual(actual_triples_arg, expected_triples) # 检查元素是否相同，不考虑顺序

        self.mock_connector.execute_update_query.assert_called_once_with(expected_sparql)

    def test_add_entity_invalid_uri(self):
        entity = TCMEntity(uri="invalid uri", entity_types=["type1"])
        with self.assertRaisesRegex(ValueError, "实体URI 'invalid uri' 无效"):
            self.entity_service.add_entity(entity)

    def test_add_entity_invalid_type_uri(self):
        entity = TCMEntity(uri="http://example.com/e1", entity_types=["invalid type uri"])
        with self.assertRaisesRegex(ValueError, "提供的类型URI 'invalid type uri' 无效"):
            self.entity_service.add_entity(entity)
            
    def test_add_entity_invalid_prop_uri(self):
        entity = TCMEntity(uri="http://example.com/e1", properties={"invalid prop uri": "value"})
        with self.assertRaisesRegex(ValueError, "提供的属性URI 'invalid prop uri' 无效"):
            self.entity_service.add_entity(entity)


    @patch('tcm_kg_virtuoso_module.graph_db.sparql_builder.build_select_entity_properties_sparql')
    def test_get_entity_by_uri_found(self, mock_build_select):
        # 测试找到实体的情况
        entity_uri = self.mock_config.NAMESPACES["tcm_entity"] + "Herb002"
        expected_sparql = f"SELECT ?predicate ?object WHERE {{ GRAPH <{self.mock_config.DEFAULT_GRAPH_URI}> {{ <{entity_uri}> ?predicate ?object . }} }}"
        mock_build_select.return_value = expected_sparql
        
        # 模拟数据库返回的数据
        db_results = {
            "results": {
                "bindings": [
                    {"predicate": {"value": self.rdf_type_uri}, "object": {"type": "uri", "value": self.mock_config.NAMESPACES["tcm_ont"] + "Herb"}},
                    {"predicate": {"value": self.mock_config.NAMESPACES["rdfs"] + "label"}, "object": {"type": "literal", "value": "党参"}},
                    {"predicate": {"value": self.mock_config.NAMESPACES["tcm_prop"] + "hasTaste"}, "object": {"type": "uri", "value": self.mock_config.NAMESPACES["tcm_entity"] + "Sweet"}},
                    {"predicate": {"value": self.mock_config.NAMESPACES["tcm_prop"] + "hasTaste"}, "object": {"type": "uri", "value": self.mock_config.NAMESPACES["tcm_entity"] + "Neutral"}},
                    {"predicate": {"value": self.mock_config.NAMESPACES["tcm_prop"] + "value_int"}, "object": {"type": "typed-literal", "value": "100", "datatype": self.mock_config.NAMESPACES["xsd"]+"integer"}},
                    {"predicate": {"value": self.mock_config.NAMESPACES["tcm_prop"] + "value_bool"}, "object": {"type": "typed-literal", "value": "true", "datatype": self.mock_config.NAMESPACES["xsd"]+"boolean"}},

                ]
            }
        }
        self.mock_connector.execute_select_query.return_value = db_results

        retrieved_entity = self.entity_service.get_entity_by_uri(entity_uri)

        self.assertIsNotNone(retrieved_entity)
        self.assertEqual(retrieved_entity.uri, entity_uri)
        self.assertCountEqual(retrieved_entity.entity_types, [self.mock_config.NAMESPACES["tcm_ont"] + "Herb"])
        self.assertEqual(retrieved_entity.properties[self.mock_config.NAMESPACES["rdfs"] + "label"], "党参")
        self.assertCountEqual(retrieved_entity.properties[self.mock_config.NAMESPACES["tcm_prop"] + "hasTaste"], 
                              [self.mock_config.NAMESPACES["tcm_entity"] + "Sweet", self.mock_config.NAMESPACES["tcm_entity"] + "Neutral"])
        self.assertEqual(retrieved_entity.properties[self.mock_config.NAMESPACES["tcm_prop"] + "value_int"], 100)
        self.assertEqual(retrieved_entity.properties[self.mock_config.NAMESPACES["tcm_prop"] + "value_bool"], True)
        
        mock_build_select.assert_called_once_with(graph_uri=self.mock_config.DEFAULT_GRAPH_URI, entity_uri=entity_uri)
        self.mock_connector.execute_select_query.assert_called_once_with(expected_sparql)

    def test_get_entity_by_uri_not_found(self):
        entity_uri = self.mock_config.NAMESPACES["tcm_entity"] + "NonExistentHerb"
        self.mock_connector.execute_select_query.return_value = {"results": {"bindings": []}} # 模拟未找到

        retrieved_entity = self.entity_service.get_entity_by_uri(entity_uri)
        self.assertIsNone(retrieved_entity) # 按照当前实现，找不到时返回 None

    def test_get_entity_by_uri_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "要检索的实体URI 'invalid uri' 无效"):
            self.entity_service.get_entity_by_uri("invalid uri")

    @patch('tcm_kg_virtuoso_module.graph_db.sparql_builder.SPARQL_PREFIXES', "PREFIX ex: <http://example.com/>") # Mock prefixes for query string check
    def test_delete_entity_success(self, mock_prefixes):
        entity_uri = self.mock_config.NAMESPACES["tcm_entity"] + "HerbToDelete"
        self.mock_connector.execute_update_query.return_value = True # 模拟数据库操作成功

        result = self.entity_service.delete_entity(entity_uri)
        self.assertTrue(result)

        # 验证 execute_update_query 被调用了正确的次数和参数 (对于 subject 的删除)
        expected_delete_subject_query = f"""
{mock_prefixes}
DELETE WHERE {{
  GRAPH <{self.mock_config.DEFAULT_GRAPH_URI}> {{
    <{entity_uri}> ?predicate ?object .
  }}
}}
"""
        self.mock_connector.execute_update_query.assert_called_once_with(unittest.mock.ANY)
        actual_query = self.mock_connector.execute_update_query.call_args[0][0]
        # 移除前导/尾随空格和换行符以进行比较
        self.assertEqual(actual_query.strip().replace("\n",""), expected_delete_subject_query.strip().replace("\n",""))


    @patch('tcm_kg_virtuoso_module.graph_db.sparql_builder.SPARQL_PREFIXES', "PREFIX ex: <http://example.com/>")
    def test_delete_entity_cascade_success(self, mock_prefixes):
        entity_uri = self.mock_config.NAMESPACES["tcm_entity"] + "HerbToDeleteCascade"
        self.mock_connector.execute_update_query.return_value = True

        result = self.entity_service.delete_entity(entity_uri, cascade=True)
        self.assertTrue(result)

        expected_delete_subject_query = f"""
{mock_prefixes}
DELETE WHERE {{
  GRAPH <{self.mock_config.DEFAULT_GRAPH_URI}> {{
    <{entity_uri}> ?predicate ?object .
  }}
}}
"""
        expected_delete_object_query = f"""
{mock_prefixes}
DELETE WHERE {{
  GRAPH <{self.mock_config.DEFAULT_GRAPH_URI}> {{
    ?subject ?predicate <{entity_uri}> .
  }}
}}
"""
        # 验证调用次数
        self.assertEqual(self.mock_connector.execute_update_query.call_count, 2)
        # 验证调用参数 (使用 call_args_list)
        calls = self.mock_connector.execute_update_query.call_args_list
        self.assertEqual(calls[0][0][0].strip().replace("\n",""), expected_delete_subject_query.strip().replace("\n",""))
        self.assertEqual(calls[1][0][0].strip().replace("\n",""), expected_delete_object_query.strip().replace("\n",""))


    def test_delete_entity_db_failure(self):
        entity_uri = self.mock_config.NAMESPACES["tcm_entity"] + "HerbToDeleteFail"
        self.mock_connector.execute_update_query.return_value = False # 模拟数据库操作失败
        result = self.entity_service.delete_entity(entity_uri)
        self.assertFalse(result)

    def test_delete_entity_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "要删除的实体URI 'invalid uri' 无效"):
            self.entity_service.delete_entity("invalid uri")

if __name__ == '__main__':
    unittest.main()
