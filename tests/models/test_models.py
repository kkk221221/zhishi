# tests/models/test_models.py
import unittest
from dataclasses import is_dataclass
from src.tcm_kg_virtuoso_module.models.tcm_entity import TCMEntity
from src.tcm_kg_virtuoso_module.models.tcm_relationship import TCMRelationship

class TestModels(unittest.TestCase):

    def test_tcm_entity_creation(self):
        # 测试 TCMEntity 对象的成功创建
        uri = "http://example.com/entity/herb001"
        types = ["tcm_ont:Herb", "owl:NamedIndividual"]
        properties = {"rdfs:label": "人参", "tcm_prop:taste": "甘"}
        
        entity = TCMEntity(uri=uri, entity_types=types, properties=properties)
        
        self.assertTrue(is_dataclass(entity))
        self.assertEqual(entity.uri, uri)
        self.assertEqual(entity.entity_types, types)
        self.assertEqual(entity.properties, properties)

    def test_tcm_entity_defaults(self):
        # 测试 TCMEntity 对象的默认值
        uri = "http://example.com/entity/point002"
        entity = TCMEntity(uri=uri) # 使用默认的 entity_types 和 properties
        
        self.assertEqual(entity.uri, uri)
        self.assertEqual(entity.entity_types, []) # 默认为空列表
        self.assertEqual(entity.properties, {})   # 默认为空字典

    def test_tcm_entity_uri_not_empty(self):
        # 测试当 URI 为空时是否引发 ValueError
        with self.assertRaisesRegex(ValueError, "实体URI .*不能为空"):
            TCMEntity(uri="", entity_types=["tcm_ont:Herb"], properties={})

    def test_tcm_relationship_creation(self):
        # 测试 TCMRelationship 对象的成功创建
        source_uri = "http://example.com/entity/herb001"
        predicate_uri = "tcm_prop:hasEffect"
        target_uri = "http://example.com/entity/effect001"
        properties = {"source_doc": "本草纲目"}
        
        relationship = TCMRelationship(
            source_uri=source_uri,
            predicate_uri=predicate_uri,
            target_uri=target_uri,
            properties=properties
        )
        
        self.assertTrue(is_dataclass(relationship))
        self.assertEqual(relationship.source_uri, source_uri)
        self.assertEqual(relationship.predicate_uri, predicate_uri)
        self.assertEqual(relationship.target_uri, target_uri)
        self.assertEqual(relationship.properties, properties)

    def test_tcm_relationship_defaults(self):
        # 测试 TCMRelationship 对象的默认值 (properties)
        source_uri = "http://example.com/entity/herb002"
        predicate_uri = "rdf:type"
        target_uri = "owl:NamedIndividual"
        
        relationship = TCMRelationship(
            source_uri=source_uri,
            predicate_uri=predicate_uri,
            target_uri=target_uri
        )
        self.assertEqual(relationship.properties, {}) # 默认为空字典

    def test_tcm_relationship_missing_uris(self):
        # 测试当必要的 URI 为空时是否引发 ValueError
        with self.assertRaisesRegex(ValueError, "源实体URI .*不能为空"):
            TCMRelationship(source_uri="", predicate_uri="p", target_uri="t")
        
        with self.assertRaisesRegex(ValueError, "谓词URI .*不能为空"):
            TCMRelationship(source_uri="s", predicate_uri="", target_uri="t")
            
        with self.assertRaisesRegex(ValueError, "目标URI .*不能为空"):
            TCMRelationship(source_uri="s", predicate_uri="p", target_uri="")

if __name__ == '__main__':
    unittest.main()
