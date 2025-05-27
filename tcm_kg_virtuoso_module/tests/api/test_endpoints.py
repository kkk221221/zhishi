# tcm_kg_virtuoso_module/tests/api/test_endpoints.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from tcm_kg_virtuoso_module.main import app # 导入FastAPI应用实例
from tcm_kg_virtuoso_module.api.request_schemas import EntityCreate, Attribute, Source # 导入请求结构

# 使用FastAPI的TestClient进行测试
# Use FastAPI's TestClient for testing
client = TestClient(app)

# 1. 测试成功创建实体 (Happy Path)
# 1. Test successful entity creation (Happy Path)
def test_create_entity_success():
    # 准备请求体数据
    # Prepare request body data
    entity_payload = {
        "type": "Herb",
        "label": "人参", # Ginseng
        "attributes": [
            {"property": "tcm-onto:hasTaste", "value": "甘"}, # Sweet
            {"property": "tcm-onto:alternativeName", "value": ["高丽参", "西洋参"]} # Korean Ginseng, American Ginseng
        ],
        "source": {
            "citation": "神农本草经", # Shennong Bencao Jing
            "originalText": "人参，味甘，微寒。", # Ginseng, taste sweet, slightly cold.
            "documentIdentifier": "SNBCJ_Chap1_Herb1"
        }
    }

    # 模拟 core.graph_operations.add_entity 函数
    # Mock the core.graph_operations.add_entity function
    # 让它返回一个预期的实体URI
    # Make it return an expected entity URI
    mock_entity_uri = "http://tcm.example.org/resource/Herb_Ginseng_123"
    
    with patch("tcm_kg_virtuoso_module.api.endpoints.add_entity") as mock_add_entity:
        mock_add_entity.return_value = mock_entity_uri
        
        # 发送POST请求
        # Send POST request
        response = client.post("/api/v1/tcm/graph/entities", json=entity_payload)
        
        # 断言状态码为201 Created
        # Assert status code is 201 Created
        assert response.status_code == 201
        # 断言响应体包含实体URI
        # Assert response body contains the entity URI
        assert response.json() == {"entity_uri": mock_entity_uri}
        
        # 验证add_entity被正确调用
        # Verify add_entity was called correctly
        # 注意：这里需要精确匹配传递给add_entity的转换后数据结构
        # Note: This requires precise matching of the transformed data structure passed to add_entity
        mock_add_entity.assert_called_once()
        called_args, called_kwargs = mock_add_entity.call_args
        
        actual_entity_data = called_args[0] # add_entity的第一个位置参数是entity_data
                                           # The first positional argument of add_entity is entity_data
        
        assert actual_entity_data["entity_type_name"] == entity_payload["type"]
        assert actual_entity_data["entity_label"] == entity_payload["label"]
        assert len(actual_entity_data["attributes_list"]) == 2
        assert actual_entity_data["attributes_list"][0]["property"] == entity_payload["attributes"][0]["property"]
        # transform_attribute_value 会将值转换为字符串或字符串列表
        # transform_attribute_value will convert values to string or list of strings
        assert actual_entity_data["attributes_list"][0]["value"] == str(entity_payload["attributes"][0]["value"]) 
        assert actual_entity_data["attributes_list"][1]["value"] == [str(v) for v in entity_payload["attributes"][1]["value"]]


        expected_source_details = {
            "citation": entity_payload["source"]["citation"],
            "original_text": entity_payload["source"]["originalText"],
            "document_identifier": entity_payload["source"]["documentIdentifier"],
            "source_type": "APIDataCreation", # 默认值
                                              # Default value
            "source_section": entity_payload["type"], # 默认值
                                                     # Default value
            "source_subsection": entity_payload["label"] # 默认值
                                                        # Default value
        }
        assert actual_entity_data["source_details"] == expected_source_details

# 2. 测试无效请求数据 (例如，缺失字段) - 应返回422
# 2. Test invalid request data (e.g., missing fields) - should return 422
def test_create_entity_invalid_payload_missing_field():
    invalid_payload = {
        # "type": "Herb", # 类型字段缺失 Type field is missing
        "label": "无效药材", # Invalid herb
        "attributes": [],
        "source": {
            "citation": "测试文献", "originalText": "测试文本", "documentIdentifier": "test_doc_1" # Test literature, Test text
        }
    }
    response = client.post("/api/v1/tcm/graph/entities", json=invalid_payload)
    assert response.status_code == 422 # FastAPI的请求体验证错误
                                       # FastAPI's request body validation error

# 3. 测试无效请求数据 (例如，属性格式错误) - 应返回422
# 3. Test invalid request data (e.g., incorrect attribute format) - should return 422
def test_create_entity_invalid_attribute_format():
    payload_invalid_attr = {
        "type": "Herb",
        "label": "测试药材", # Test herb
        "attributes": [
            {"prop": "tcm-onto:hasTaste", "val": "苦"} # 属性键名错误，应为 "property" 和 "value"
                                                     # Incorrect attribute key names, should be "property" and "value"
        ],
        "source": {"citation": "N/A", "originalText": "N/A", "documentIdentifier": "N/A"}
    }
    response = client.post("/api/v1/tcm/graph/entities", json=payload_invalid_attr)
    assert response.status_code == 422

# 4. 测试核心逻辑 add_entity 抛出 ValueError (例如，内部数据问题) - 应返回400
# 4. Test core logic add_entity throws ValueError (e.g., internal data issue) - should return 400
def test_create_entity_core_logic_value_error():
    entity_payload = {
        "type": "Formula",
        "label": "测试方剂", # Test formula
        "attributes": [],
        "source": {"citation": "N/A", "originalText": "N/A", "documentIdentifier": "N/A"}
    }
    
    # 模拟 add_entity 抛出 ValueError
    # Mock add_entity to throw ValueError
    with patch("tcm_kg_virtuoso_module.api.endpoints.add_entity") as mock_add_entity:
        mock_add_entity.side_effect = ValueError("核心逻辑错误：无效的实体类型") # Core logic error: Invalid entity type
        
        response = client.post("/api/v1/tcm/graph/entities", json=entity_payload)
        
        assert response.status_code == 400
        assert "核心逻辑错误：无效的实体类型" in response.json()["detail"] # Core logic error: Invalid entity type

# 5. 测试核心逻辑 add_entity 抛出其他Exception (例如，数据库连接问题) - 应返回500
# 5. Test core logic add_entity throws other Exception (e.g., database connection issue) - should return 500
def test_create_entity_core_logic_generic_exception():
    entity_payload = {
        "type": "Syndrome",
        "label": "测试证候", # Test syndrome
        "attributes": [],
        "source": {"citation": "N/A", "originalText": "N/A", "documentIdentifier": "N/A"}
    }
    
    # 模拟 add_entity 抛出通用 Exception
    # Mock add_entity to throw a generic Exception
    with patch("tcm_kg_virtuoso_module.api.endpoints.add_entity") as mock_add_entity:
        mock_add_entity.side_effect = Exception("数据库连接超时") # Database connection timeout
        
        response = client.post("/api/v1/tcm/graph/entities", json=entity_payload)
        
        assert response.status_code == 500
        assert "创建实体时发生意外错误" in response.json()["detail"] # An unexpected error occurred while creating the entity.

# 6. 测试具有HttpUrl类型属性值的实体创建
# 6. Test entity creation with HttpUrl type attribute value
def test_create_entity_with_http_url_attribute():
    entity_payload = {
        "type": "Herb",
        "label": "枸杞", # Goji Berry
        "attributes": [
            {"property": "rdfs:seeAlso", "value": "http://example.com/goji"}
        ],
        "source": {
            "citation": "本草纲目", "originalText": "枸杞，甘，平。", "documentIdentifier": "BCGM_Goji" # Compendium of Materia Medica, Goji, sweet, neutral.
        }
    }
    mock_entity_uri = "http://tcm.example.org/resource/Herb_Goji_456"
    
    with patch("tcm_kg_virtuoso_module.api.endpoints.add_entity") as mock_add_entity:
        mock_add_entity.return_value = mock_entity_uri
        
        response = client.post("/api/v1/tcm/graph/entities", json=entity_payload)
        
        assert response.status_code == 201
        assert response.json() == {"entity_uri": mock_entity_uri}
        
        mock_add_entity.assert_called_once()
        called_args, _ = mock_add_entity.call_args
        actual_entity_data = called_args[0]
        
        assert actual_entity_data["attributes_list"][0]["property"] == "rdfs:seeAlso"
        # transform_attribute_value 会将 HttpUrl 转换为字符串
        # transform_attribute_value will convert HttpUrl to string
        assert actual_entity_data["attributes_list"][0]["value"] == "http://example.com/goji"

# 在文件顶部，确保 TestClient 是从 fastapi.testclient 导入的
# At the top of the file, ensure TestClient is imported from fastapi.testclient
# from fastapi.testclient import TestClient

# 确保 app 是从你的主应用模块导入的
# Ensure app is imported from your main application module
# from tcm_kg_virtuoso_module.main import app

# 还需要导入 unittest.mock 中的 patch
# Also need to import patch from unittest.mock
# from unittest.mock import patch
