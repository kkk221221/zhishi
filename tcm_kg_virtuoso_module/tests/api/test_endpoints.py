# tcm_kg_virtuoso_module/tests/api/test_endpoints.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
from urllib.parse import quote # 用于编码实体URI
import json # 用于比较复杂嵌套结构的JSON

from tcm_kg_virtuoso_module.main import app # 导入FastAPI应用实例
from tcm_kg_virtuoso_module.api.request_schemas import ( # 更新导入以包含 EntityUpdate
    EntityCreate, 
    Attribute, 
    Source, 
    RelationshipCreate,
    EntityUpdate 
)

# 使用FastAPI的TestClient进行测试
# Use FastAPI's TestClient for testing
client = TestClient(app)

# 辅助函数，用于创建 EntityUpdate 请求的payload
# Helper function to create payload for EntityUpdate requests
def create_entity_update_payload(
    attributes_to_add_or_update=None,
    attributes_to_delete=None,
    source=None,
    correction_details=None
):
    payload = {}
    if attributes_to_add_or_update is not None:
        payload["attributes_to_add_or_update"] = attributes_to_add_or_update
    if attributes_to_delete is not None:
        payload["attributes_to_delete"] = attributes_to_delete
    
    # source 是必需的
    # source is required
    payload["source"] = source if source else {
        "citation": "Test Source Citation",
        "originalText": "Test original text.",
        "documentIdentifier": "test_doc_id_update"
    }
    if correction_details is not None:
        payload["correction_details"] = correction_details
    return payload

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

# --- Tests for /api/v1/tcm/graph/relationships ---

def test_create_relationship_success():
    # Prepare request body data
    relationship_payload = {
        "subjectUri": "http://example.com/subject/ent1",
        "predicate": "tcm-onto:hasIndication",
        "objectUri": "http://example.com/object/disease1",
        "source": {
            "citation": "Clinical Study XYZ",
            "originalText": "Herb A showed efficacy for Disease X.",
            "documentIdentifier": "CS_XYZ_2023"
        }
    }

    # Mock core.graph_operations.add_relationship
    # The endpoint imports add_relationship from .core.graph_operations
    with patch("tcm_kg_virtuoso_module.api.endpoints.add_relationship") as mock_add_relationship:
        # Send POST request
        response = client.post("/api/v1/tcm/graph/relationships", json=relationship_payload)
        
        # Assert status code is 201 Created
        assert response.status_code == 201
        # Assert response body
        assert response.json() == {"message": "Relationship added successfully"}
        
        # Verify add_relationship was called correctly
        mock_add_relationship.assert_called_once()
        called_args, called_kwargs = mock_add_relationship.call_args
        
        actual_relationship_data = called_args[0] # add_relationship's first positional arg is relationship_data
        
        assert actual_relationship_data["subject_uri"] == relationship_payload["subjectUri"]
        assert actual_relationship_data["predicate"] == relationship_payload["predicate"]
        assert actual_relationship_data["object_uri"] == relationship_payload["objectUri"]
        
        expected_source_details = {
            "citation": relationship_payload["source"]["citation"],
            "original_text": relationship_payload["source"]["originalText"],
            "document_identifier": relationship_payload["source"]["documentIdentifier"],
            "source_type": "APIRelationshipCreation", # Default value from endpoint logic
            "source_section": "Relationship",          # Default value from endpoint logic
            "source_subsection": relationship_payload["predicate"] # Default value from endpoint logic
        }
        assert actual_relationship_data["source_details"] == expected_source_details
        # conn_manager is passed as a keyword argument by Depends
        assert "conn_manager" in called_kwargs 

def test_create_relationship_invalid_payload_missing_field():
    invalid_payload = {
        "subjectUri": "http://example.com/subject/ent1",
        # "predicate": "tcm-onto:hasIndication", # Predicate is missing
        "objectUri": "http://example.com/object/disease1",
        "source": {
            "citation": "Test Citation", 
            "originalText": "Test Text", 
            "documentIdentifier": "test_doc_rel_1"
        }
    }
    response = client.post("/api/v1/tcm/graph/relationships", json=invalid_payload)
    assert response.status_code == 422 # FastAPI's request body validation error

def test_create_relationship_invalid_payload_bad_uri():
    payload_invalid_uri = {
        "subjectUri": "not-a-valid-uri", # Invalid URI
        "predicate": "tcm-onto:relatedTo",
        "objectUri": "http://example.com/object/valid",
        "source": {
            "citation": "N/A", "originalText": "N/A", "documentIdentifier": "N/A"
        }
    }
    response = client.post("/api/v1/tcm/graph/relationships", json=payload_invalid_uri)
    assert response.status_code == 422

def test_create_relationship_core_logic_value_error():
    relationship_payload = {
        "subjectUri": "http://example.com/subject/entValid1",
        "predicate": "tcm-onto:causes",
        "objectUri": "http://example.com/object/eventValid1",
        "source": {"citation": "N/A", "originalText": "N/A", "documentIdentifier": "N/A"}
    }
    
    with patch("tcm_kg_virtuoso_module.api.endpoints.add_relationship") as mock_add_relationship:
        mock_add_relationship.side_effect = ValueError("Core logic error: Invalid predicate for these entities.")
        
        response = client.post("/api/v1/tcm/graph/relationships", json=relationship_payload)
        
        assert response.status_code == 400
        assert "Core logic error: Invalid predicate for these entities." in response.json()["detail"]

def test_create_relationship_core_logic_generic_exception():
    relationship_payload = {
        "subjectUri": "http://example.com/subject/entFail1",
        "predicate": "tcm-onto:interactsWith",
        "objectUri": "http://example.com/object/drugFail1",
        "source": {"citation": "N/A", "originalText": "N/A", "documentIdentifier": "N/A"}
    }
    
    with patch("tcm_kg_virtuoso_module.api.endpoints.add_relationship") as mock_add_relationship:
        mock_add_relationship.side_effect = Exception("Database transaction failed unexpectedly.")
        
        response = client.post("/api/v1/tcm/graph/relationships", json=relationship_payload)
        
        assert response.status_code == 500
        assert "创建关系时发生意外错误。" in response.json()["detail"] # "An unexpected error occurred while creating the relationship."

# --- 测试更新实体API端点 ---
# --- Tests for Update Entity API Endpoint ---

# test_update_entity_success_full_payload 函数已被移除，因为它已被 test_update_entity_success_full_payload_custom_assert 替代和修正。
# The test_update_entity_success_full_payload function has been removed as it was replaced and corrected by test_update_entity_success_full_payload_custom_assert.

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_minimal_payload(mock_core_update_entity):
    """测试成功更新实体 - 仅包含必需的 source 字段 (Test successful entity update - minimal payload with only required source field)"""
    entity_uri = "http://example.com/entity/minimal_update"
    entity_uri_encoded = quote(entity_uri, safe='')
    
    payload = create_entity_update_payload( # 使用辅助函数创建仅包含 source 的 payload
                                          # Use helper to create payload with only source
        source={"citation": "Minimal citation", "originalText": "Minimal text", "documentIdentifier": "min_doc"}
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once_with(
        entity_uri=entity_uri,
        attributes_to_add_or_update=None,
        attributes_to_delete=None,
        source_info=payload["source"],
        correction_details_info=None,
        conn_manager=ANY # 验证 conn_manager 是否被传递，但不关心其具体值
                         # Verify conn_manager was passed, but don't care about its specific value
    )

def test_update_entity_invalid_payload_missing_source():
    """测试无效请求体 - 缺少必需的 source 字段 (Test invalid payload - missing required source field)"""
    entity_uri_encoded = quote("http://example.com/entity/any_ent", safe='')
    payload = { # 手动构造一个没有 source 的 payload
              # Manually construct a payload without source
        "attributes_to_add_or_update": [{"property": "p", "value": "v"}]
    }
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422 # FastAPI 请求体验证错误
                                       # FastAPI request body validation error
    assert "source" in response.text.lower() # 确保错误信息提到 source
                                           # Ensure error message mentions source

def test_update_entity_invalid_payload_bad_uri_in_correction():
    """测试无效请求体 - correction_details 中的 targetNamedGraphUri 不是有效URL (Test invalid payload - targetNamedGraphUri in correction_details is not a valid URL)"""
    entity_uri_encoded = quote("http://example.com/entity/bad_uri_corr", safe='')
    payload = create_entity_update_payload(
        correction_details={
            "targetNamedGraphUri": "这不是一个有效的URL", # Invalid URL
            "property_to_correct": "tcm-onto:someProp"
        }
    )
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422
    assert "targetNamedGraphUri" in response.text.lower() # 确保错误信息提到 targetNamedGraphUri
                                                        # Ensure error message mentions targetNamedGraphUri

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_value_error(mock_core_update_entity):
    """测试核心逻辑抛出 ValueError (例如，不一致的数据) - 应返回400 (Test core logic throws ValueError - should return 400)"""
    entity_uri_encoded = quote("http://example.com/entity/value_error_case", safe='')
    payload = create_entity_update_payload() # 使用默认有效payload
                                             # Use default valid payload
    
    # 模拟核心 update_entity 函数抛出 ValueError
    # Mock core update_entity function to throw ValueError
    error_message = "核心逻辑错误：例如，修正的属性在列表中找不到。"
    mock_core_update_entity.side_effect = ValueError(error_message)
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 400
    assert error_message in response.json()["detail"]

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_generic_exception(mock_core_update_entity):
    """测试核心逻辑抛出通用 Exception (例如，数据库连接问题) - 应返回500 (Test core logic throws generic Exception - should return 500)"""
    entity_uri_encoded = quote("http://example.com/entity/server_error_case", safe='')
    payload = create_entity_update_payload()
    
    # 模拟核心 update_entity 函数抛出通用 Exception
    # Mock core update_entity function to throw generic Exception
    mock_core_update_entity.side_effect = Exception("模拟的数据库连接超时") # Simulated database connection timeout
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 500
    assert "更新实体时发生意外错误。" in response.json()["detail"] # "An unexpected error occurred while updating the entity."

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_success_full_payload_custom_assert(mock_core_update_entity):
    """测试成功更新实体 - 包含所有可能的字段 (使用自定义断言)"""
    entity_uri = "http://example.com/entity/herb_to_update_custom"
    entity_uri_encoded = quote(entity_uri, safe='')

    payload = create_entity_update_payload(
        attributes_to_add_or_update=[
            {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
            {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # HttpUrl Pydantic 模型会在请求时自动转换为字符串
                                                                                # HttpUrl Pydantic model automatically converts to string on request
        ],
        attributes_to_delete=[
            {"property": "tcm-onto:oldProperty", "value": "旧的值"},
            {"property": "tcm-onto:anotherOldProperty"}
        ],
        source={
            "citation": "Update Source 2023 Custom",
            "originalText": "Entity was updated based on new findings custom.",
            "documentIdentifier": "update_doc_001_custom"
        },
        correction_details={
            "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # HttpUrl Pydantic 模型
            "property_to_correct": "tcm-onto:description"
        }
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once()
    called_kwargs = mock_core_update_entity.call_args.kwargs

    assert called_kwargs["entity_uri"] == entity_uri
    
    expected_add_update = [
        {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
        {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # 期望字符串
    ]
    assert len(called_kwargs["attributes_to_add_or_update"]) == len(expected_add_update)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_add_or_update"], expected_add_update):
        assert actual_item == expected_item

    expected_delete = [
        {"property": "tcm-onto:oldProperty", "value": "旧的值", "datatype": None},
        {"property": "tcm-onto:anotherOldProperty", "value": None, "datatype": None}
    ]
    assert len(called_kwargs["attributes_to_delete"]) == len(expected_delete)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_delete"], expected_delete):
        assert actual_item == expected_item
        
    assert called_kwargs["source_info"] == payload["source"]
    
    expected_correction_details = {
        "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # 期望字符串
        "property_to_correct": "tcm-onto:description"
    }
    assert called_kwargs["correction_details_info"] == expected_correction_details

# --- 测试更新实体API端点 ---
# --- Tests for Update Entity API Endpoint ---

# test_update_entity_success_full_payload 函数已被移除，因为它已被 test_update_entity_success_full_payload_custom_assert 替代和修正。
# The test_update_entity_success_full_payload function has been removed as it was replaced and corrected by test_update_entity_success_full_payload_custom_assert.

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_minimal_payload(mock_core_update_entity):
    """测试成功更新实体 - 仅包含必需的 source 字段 (Test successful entity update - minimal payload with only required source field)"""
    entity_uri = "http://example.com/entity/minimal_update"
    entity_uri_encoded = quote(entity_uri, safe='')
    
    payload = create_entity_update_payload( # 使用辅助函数创建仅包含 source 的 payload
                                          # Use helper to create payload with only source
        source={"citation": "Minimal citation", "originalText": "Minimal text", "documentIdentifier": "min_doc"}
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once_with(
        entity_uri=entity_uri,
        attributes_to_add_or_update=None,
        attributes_to_delete=None,
        source_info=payload["source"],
        correction_details_info=None,
        conn_manager=ANY # 验证 conn_manager 是否被传递，但不关心其具体值
                         # Verify conn_manager was passed, but don't care about its specific value
    )

def test_update_entity_invalid_payload_missing_source():
    """测试无效请求体 - 缺少必需的 source 字段 (Test invalid payload - missing required source field)"""
    entity_uri_encoded = quote("http://example.com/entity/any_ent", safe='')
    payload = { # 手动构造一个没有 source 的 payload
              # Manually construct a payload without source
        "attributes_to_add_or_update": [{"property": "p", "value": "v"}]
    }
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422 # FastAPI 请求体验证错误
                                       # FastAPI request body validation error
    assert "source" in response.text.lower() # 确保错误信息提到 source
                                           # Ensure error message mentions source

def test_update_entity_invalid_payload_bad_uri_in_correction():
    """测试无效请求体 - correction_details 中的 targetNamedGraphUri 不是有效URL (Test invalid payload - targetNamedGraphUri in correction_details is not a valid URL)"""
    entity_uri_encoded = quote("http://example.com/entity/bad_uri_corr", safe='')
    payload = create_entity_update_payload(
        correction_details={
            "targetNamedGraphUri": "这不是一个有效的URL", # Invalid URL
            "property_to_correct": "tcm-onto:someProp"
        }
    )
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422
    assert "targetNamedGraphUri" in response.text.lower() # 确保错误信息提到 targetNamedGraphUri
                                                        # Ensure error message mentions targetNamedGraphUri

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_value_error(mock_core_update_entity):
    """测试核心逻辑抛出 ValueError (例如，不一致的数据) - 应返回400 (Test core logic throws ValueError - should return 400)"""
    entity_uri_encoded = quote("http://example.com/entity/value_error_case", safe='')
    payload = create_entity_update_payload() # 使用默认有效payload
                                             # Use default valid payload
    
    # 模拟核心 update_entity 函数抛出 ValueError
    # Mock core update_entity function to throw ValueError
    error_message = "核心逻辑错误：例如，修正的属性在列表中找不到。"
    mock_core_update_entity.side_effect = ValueError(error_message)
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 400
    assert error_message in response.json()["detail"]

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_generic_exception(mock_core_update_entity):
    """测试核心逻辑抛出通用 Exception (例如，数据库连接问题) - 应返回500 (Test core logic throws generic Exception - should return 500)"""
    entity_uri_encoded = quote("http://example.com/entity/server_error_case", safe='')
    payload = create_entity_update_payload()
    
    # 模拟核心 update_entity 函数抛出通用 Exception
    # Mock core update_entity function to throw generic Exception
    mock_core_update_entity.side_effect = Exception("模拟的数据库连接超时") # Simulated database connection timeout
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 500
    assert "更新实体时发生意外错误。" in response.json()["detail"] # "An unexpected error occurred while updating the entity."

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_success_full_payload_custom_assert(mock_core_update_entity):
    """测试成功更新实体 - 包含所有可能的字段 (使用自定义断言)"""
    entity_uri = "http://example.com/entity/herb_to_update_custom"
    entity_uri_encoded = quote(entity_uri, safe='')

    payload = create_entity_update_payload(
        attributes_to_add_or_update=[
            {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
            {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # HttpUrl Pydantic 模型会在请求时自动转换为字符串
                                                                                # HttpUrl Pydantic model automatically converts to string on request
        ],
        attributes_to_delete=[
            {"property": "tcm-onto:oldProperty", "value": "旧的值"},
            {"property": "tcm-onto:anotherOldProperty"}
        ],
        source={
            "citation": "Update Source 2023 Custom",
            "originalText": "Entity was updated based on new findings custom.",
            "documentIdentifier": "update_doc_001_custom"
        },
        correction_details={
            "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # HttpUrl Pydantic 模型
            "property_to_correct": "tcm-onto:description"
        }
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once()
    called_kwargs = mock_core_update_entity.call_args.kwargs

    assert called_kwargs["entity_uri"] == entity_uri
    
    expected_add_update = [
        {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
        {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # 期望字符串
    ]
    assert len(called_kwargs["attributes_to_add_or_update"]) == len(expected_add_update)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_add_or_update"], expected_add_update):
        assert actual_item == expected_item

    expected_delete = [
        {"property": "tcm-onto:oldProperty", "value": "旧的值", "datatype": None},
        {"property": "tcm-onto:anotherOldProperty", "value": None, "datatype": None}
    ]
    assert len(called_kwargs["attributes_to_delete"]) == len(expected_delete)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_delete"], expected_delete):
        assert actual_item == expected_item
        
    assert called_kwargs["source_info"] == payload["source"]
    
    expected_correction_details = {
        "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # 期望字符串
        "property_to_correct": "tcm-onto:description"
    }
    assert called_kwargs["correction_details_info"] == expected_correction_details

# --- 测试更新实体API端点 ---
# --- Tests for Update Entity API Endpoint ---

# test_update_entity_success_full_payload 函数已被移除，因为它已被 test_update_entity_success_full_payload_custom_assert 替代和修正。
# The test_update_entity_success_full_payload function has been removed as it was replaced and corrected by test_update_entity_success_full_payload_custom_assert.

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_minimal_payload(mock_core_update_entity):
    """测试成功更新实体 - 仅包含必需的 source 字段 (Test successful entity update - minimal payload with only required source field)"""
    entity_uri = "http://example.com/entity/minimal_update"
    entity_uri_encoded = quote(entity_uri, safe='')
    
    payload = create_entity_update_payload( # 使用辅助函数创建仅包含 source 的 payload
                                          # Use helper to create payload with only source
        source={"citation": "Minimal citation", "originalText": "Minimal text", "documentIdentifier": "min_doc"}
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once_with(
        entity_uri=entity_uri,
        attributes_to_add_or_update=None,
        attributes_to_delete=None,
        source_info=payload["source"],
        correction_details_info=None,
        conn_manager=ANY # 验证 conn_manager 是否被传递，但不关心其具体值
                         # Verify conn_manager was passed, but don't care about its specific value
    )

def test_update_entity_invalid_payload_missing_source():
    """测试无效请求体 - 缺少必需的 source 字段 (Test invalid payload - missing required source field)"""
    entity_uri_encoded = quote("http://example.com/entity/any_ent", safe='')
    payload = { # 手动构造一个没有 source 的 payload
              # Manually construct a payload without source
        "attributes_to_add_or_update": [{"property": "p", "value": "v"}]
    }
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422 # FastAPI 请求体验证错误
                                       # FastAPI request body validation error
    assert "source" in response.text.lower() # 确保错误信息提到 source
                                           # Ensure error message mentions source

def test_update_entity_invalid_payload_bad_uri_in_correction():
    """测试无效请求体 - correction_details 中的 targetNamedGraphUri 不是有效URL (Test invalid payload - targetNamedGraphUri in correction_details is not a valid URL)"""
    entity_uri_encoded = quote("http://example.com/entity/bad_uri_corr", safe='')
    payload = create_entity_update_payload(
        correction_details={
            "targetNamedGraphUri": "这不是一个有效的URL", # Invalid URL
            "property_to_correct": "tcm-onto:someProp"
        }
    )
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422
    assert "targetNamedGraphUri" in response.text.lower() # 确保错误信息提到 targetNamedGraphUri
                                                        # Ensure error message mentions targetNamedGraphUri

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_value_error(mock_core_update_entity):
    """测试核心逻辑抛出 ValueError (例如，不一致的数据) - 应返回400 (Test core logic throws ValueError - should return 400)"""
    entity_uri_encoded = quote("http://example.com/entity/value_error_case", safe='')
    payload = create_entity_update_payload() # 使用默认有效payload
                                             # Use default valid payload
    
    # 模拟核心 update_entity 函数抛出 ValueError
    # Mock core update_entity function to throw ValueError
    error_message = "核心逻辑错误：例如，修正的属性在列表中找不到。"
    mock_core_update_entity.side_effect = ValueError(error_message)
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 400
    assert error_message in response.json()["detail"]

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_generic_exception(mock_core_update_entity):
    """测试核心逻辑抛出通用 Exception (例如，数据库连接问题) - 应返回500 (Test core logic throws generic Exception - should return 500)"""
    entity_uri_encoded = quote("http://example.com/entity/server_error_case", safe='')
    payload = create_entity_update_payload()
    
    # 模拟核心 update_entity 函数抛出通用 Exception
    # Mock core update_entity function to throw generic Exception
    mock_core_update_entity.side_effect = Exception("模拟的数据库连接超时") # Simulated database connection timeout
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 500
    assert "更新实体时发生意外错误。" in response.json()["detail"] # "An unexpected error occurred while updating the entity."

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_success_full_payload_custom_assert(mock_core_update_entity):
    """测试成功更新实体 - 包含所有可能的字段 (使用自定义断言)"""
    entity_uri = "http://example.com/entity/herb_to_update_custom"
    entity_uri_encoded = quote(entity_uri, safe='')

    payload = create_entity_update_payload(
        attributes_to_add_or_update=[
            {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
            {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # HttpUrl Pydantic 模型会在请求时自动转换为字符串
                                                                                # HttpUrl Pydantic model automatically converts to string on request
        ],
        attributes_to_delete=[
            {"property": "tcm-onto:oldProperty", "value": "旧的值"},
            {"property": "tcm-onto:anotherOldProperty"}
        ],
        source={
            "citation": "Update Source 2023 Custom",
            "originalText": "Entity was updated based on new findings custom.",
            "documentIdentifier": "update_doc_001_custom"
        },
        correction_details={
            "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # HttpUrl Pydantic 模型
            "property_to_correct": "tcm-onto:description"
        }
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once()
    called_kwargs = mock_core_update_entity.call_args.kwargs

    assert called_kwargs["entity_uri"] == entity_uri
    
    expected_add_update = [
        {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
        {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # 期望字符串
    ]
    assert len(called_kwargs["attributes_to_add_or_update"]) == len(expected_add_update)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_add_or_update"], expected_add_update):
        assert actual_item == expected_item

    expected_delete = [
        {"property": "tcm-onto:oldProperty", "value": "旧的值", "datatype": None},
        {"property": "tcm-onto:anotherOldProperty", "value": None, "datatype": None}
    ]
    assert len(called_kwargs["attributes_to_delete"]) == len(expected_delete)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_delete"], expected_delete):
        assert actual_item == expected_item
        
    assert called_kwargs["source_info"] == payload["source"]
    
    expected_correction_details = {
        "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # 期望字符串
        "property_to_correct": "tcm-onto:description"
    }
    assert called_kwargs["correction_details_info"] == expected_correction_details

# --- 测试更新实体API端点 ---
# --- Tests for Update Entity API Endpoint ---

# test_update_entity_success_full_payload 函数已被移除，由下面的 _custom_assert 版本替代
# The test_update_entity_success_full_payload function has been removed, replaced by the _custom_assert version below.

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_minimal_payload(mock_core_update_entity):
    """测试成功更新实体 - 仅包含必需的 source 字段 (Test successful entity update - minimal payload with only required source field)"""
    entity_uri = "http://example.com/entity/minimal_update"
    entity_uri_encoded = quote(entity_uri, safe='')
    
    payload = create_entity_update_payload( # 使用辅助函数创建仅包含 source 的 payload
                                          # Use helper to create payload with only source
        source={"citation": "Minimal citation", "originalText": "Minimal text", "documentIdentifier": "min_doc"}
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once_with(
        entity_uri=entity_uri,
        attributes_to_add_or_update=None,
        attributes_to_delete=None,
        source_info=payload["source"],
        correction_details_info=None,
        conn_manager=ANY # 验证 conn_manager 是否被传递，但不关心其具体值
                         # Verify conn_manager was passed, but don't care about its specific value
    )

def test_update_entity_invalid_payload_missing_source():
    """测试无效请求体 - 缺少必需的 source 字段 (Test invalid payload - missing required source field)"""
    entity_uri_encoded = quote("http://example.com/entity/any_ent", safe='')
    payload = { # 手动构造一个没有 source 的 payload
              # Manually construct a payload without source
        "attributes_to_add_or_update": [{"property": "p", "value": "v"}]
    }
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422 # FastAPI 请求体验证错误
                                       # FastAPI request body validation error
    assert "source" in response.text.lower() # 确保错误信息提到 source
                                           # Ensure error message mentions source

def test_update_entity_invalid_payload_bad_uri_in_correction():
    """测试无效请求体 - correction_details 中的 targetNamedGraphUri 不是有效URL (Test invalid payload - targetNamedGraphUri in correction_details is not a valid URL)"""
    entity_uri_encoded = quote("http://example.com/entity/bad_uri_corr", safe='')
    payload = create_entity_update_payload(
        correction_details={
            "targetNamedGraphUri": "这不是一个有效的URL", # Invalid URL
            "property_to_correct": "tcm-onto:someProp"
        }
    )
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422
    assert "targetNamedGraphUri" in response.text.lower() # 确保错误信息提到 targetNamedGraphUri
                                                        # Ensure error message mentions targetNamedGraphUri

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_value_error(mock_core_update_entity):
    """测试核心逻辑抛出 ValueError (例如，不一致的数据) - 应返回400 (Test core logic throws ValueError - should return 400)"""
    entity_uri_encoded = quote("http://example.com/entity/value_error_case", safe='')
    payload = create_entity_update_payload() # 使用默认有效payload
                                             # Use default valid payload
    
    # 模拟核心 update_entity 函数抛出 ValueError
    # Mock core update_entity function to throw ValueError
    error_message = "核心逻辑错误：例如，修正的属性在列表中找不到。"
    mock_core_update_entity.side_effect = ValueError(error_message)
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 400
    assert error_message in response.json()["detail"]

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_generic_exception(mock_core_update_entity):
    """测试核心逻辑抛出通用 Exception (例如，数据库连接问题) - 应返回500 (Test core logic throws generic Exception - should return 500)"""
    entity_uri_encoded = quote("http://example.com/entity/server_error_case", safe='')
    payload = create_entity_update_payload()
    
    # 模拟核心 update_entity 函数抛出通用 Exception
    # Mock core update_entity function to throw generic Exception
    mock_core_update_entity.side_effect = Exception("模拟的数据库连接超时") # Simulated database connection timeout
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 500
    assert "更新实体时发生意外错误。" in response.json()["detail"] # "An unexpected error occurred while updating the entity."

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_success_full_payload_custom_assert(mock_core_update_entity):
    """测试成功更新实体 - 包含所有可能的字段 (使用自定义断言)"""
    entity_uri = "http://example.com/entity/herb_to_update_custom"
    entity_uri_encoded = quote(entity_uri, safe='')

    payload = create_entity_update_payload(
        attributes_to_add_or_update=[
            {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
            {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # HttpUrl Pydantic 模型会在请求时自动转换为字符串
                                                                                # HttpUrl Pydantic model automatically converts to string on request
        ],
        attributes_to_delete=[
            {"property": "tcm-onto:oldProperty", "value": "旧的值"},
            {"property": "tcm-onto:anotherOldProperty"}
        ],
        source={
            "citation": "Update Source 2023 Custom",
            "originalText": "Entity was updated based on new findings custom.",
            "documentIdentifier": "update_doc_001_custom"
        },
        correction_details={
            "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # HttpUrl Pydantic 模型
            "property_to_correct": "tcm-onto:description"
        }
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once()
    called_kwargs = mock_core_update_entity.call_args.kwargs

    assert called_kwargs["entity_uri"] == entity_uri
    
    expected_add_update = [
        {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
        {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # 期望字符串
    ]
    assert len(called_kwargs["attributes_to_add_or_update"]) == len(expected_add_update)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_add_or_update"], expected_add_update):
        assert actual_item == expected_item

    expected_delete = [
        {"property": "tcm-onto:oldProperty", "value": "旧的值", "datatype": None},
        {"property": "tcm-onto:anotherOldProperty", "value": None, "datatype": None}
    ]
    assert len(called_kwargs["attributes_to_delete"]) == len(expected_delete)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_delete"], expected_delete):
        assert actual_item == expected_item
        
    assert called_kwargs["source_info"] == payload["source"]
    
    expected_correction_details = {
        "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # 期望字符串
        "property_to_correct": "tcm-onto:description"
    }
    assert called_kwargs["correction_details_info"] == expected_correction_details

# --- 测试更新实体API端点 ---
# --- Tests for Update Entity API Endpoint ---

# test_update_entity_success_full_payload 函数已被移除，由下面的 _custom_assert 版本替代
# The test_update_entity_success_full_payload function has been removed, replaced by the _custom_assert version below.

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_minimal_payload(mock_core_update_entity):
    """测试成功更新实体 - 仅包含必需的 source 字段 (Test successful entity update - minimal payload with only required source field)"""
    entity_uri = "http://example.com/entity/minimal_update"
    entity_uri_encoded = quote(entity_uri, safe='')
    
    payload = create_entity_update_payload( # 使用辅助函数创建仅包含 source 的 payload
                                          # Use helper to create payload with only source
        source={"citation": "Minimal citation", "originalText": "Minimal text", "documentIdentifier": "min_doc"}
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once_with(
        entity_uri=entity_uri,
        attributes_to_add_or_update=None,
        attributes_to_delete=None,
        source_info=payload["source"],
        correction_details_info=None,
        conn_manager=ANY # 验证 conn_manager 是否被传递，但不关心其具体值
                         # Verify conn_manager was passed, but don't care about its specific value
    )

def test_update_entity_invalid_payload_missing_source():
    """测试无效请求体 - 缺少必需的 source 字段 (Test invalid payload - missing required source field)"""
    entity_uri_encoded = quote("http://example.com/entity/any_ent", safe='')
    payload = { # 手动构造一个没有 source 的 payload
              # Manually construct a payload without source
        "attributes_to_add_or_update": [{"property": "p", "value": "v"}]
    }
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422 # FastAPI 请求体验证错误
                                       # FastAPI request body validation error
    assert "source" in response.text.lower() # 确保错误信息提到 source
                                           # Ensure error message mentions source

def test_update_entity_invalid_payload_bad_uri_in_correction():
    """测试无效请求体 - correction_details 中的 targetNamedGraphUri 不是有效URL (Test invalid payload - targetNamedGraphUri in correction_details is not a valid URL)"""
    entity_uri_encoded = quote("http://example.com/entity/bad_uri_corr", safe='')
    payload = create_entity_update_payload(
        correction_details={
            "targetNamedGraphUri": "这不是一个有效的URL", # Invalid URL
            "property_to_correct": "tcm-onto:someProp"
        }
    )
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422
    assert "targetNamedGraphUri" in response.text.lower() # 确保错误信息提到 targetNamedGraphUri
                                                        # Ensure error message mentions targetNamedGraphUri

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_value_error(mock_core_update_entity):
    """测试核心逻辑抛出 ValueError (例如，不一致的数据) - 应返回400 (Test core logic throws ValueError - should return 400)"""
    entity_uri_encoded = quote("http://example.com/entity/value_error_case", safe='')
    payload = create_entity_update_payload() # 使用默认有效payload
                                             # Use default valid payload
    
    # 模拟核心 update_entity 函数抛出 ValueError
    # Mock core update_entity function to throw ValueError
    error_message = "核心逻辑错误：例如，修正的属性在列表中找不到。"
    mock_core_update_entity.side_effect = ValueError(error_message)
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 400
    assert error_message in response.json()["detail"]

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_generic_exception(mock_core_update_entity):
    """测试核心逻辑抛出通用 Exception (例如，数据库连接问题) - 应返回500 (Test core logic throws generic Exception - should return 500)"""
    entity_uri_encoded = quote("http://example.com/entity/server_error_case", safe='')
    payload = create_entity_update_payload()
    
    # 模拟核心 update_entity 函数抛出通用 Exception
    # Mock core update_entity function to throw generic Exception
    mock_core_update_entity.side_effect = Exception("模拟的数据库连接超时") # Simulated database connection timeout
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 500
    assert "更新实体时发生意外错误。" in response.json()["detail"] # "An unexpected error occurred while updating the entity."

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_success_full_payload_custom_assert(mock_core_update_entity):
    """测试成功更新实体 - 包含所有可能的字段 (使用自定义断言)"""
    entity_uri = "http://example.com/entity/herb_to_update_custom"
    entity_uri_encoded = quote(entity_uri, safe='')

    payload = create_entity_update_payload(
        attributes_to_add_or_update=[
            {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
            {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # HttpUrl Pydantic 模型会在请求时自动转换为字符串
                                                                                # HttpUrl Pydantic model automatically converts to string on request
        ],
        attributes_to_delete=[
            {"property": "tcm-onto:oldProperty", "value": "旧的值"},
            {"property": "tcm-onto:anotherOldProperty"}
        ],
        source={
            "citation": "Update Source 2023 Custom",
            "originalText": "Entity was updated based on new findings custom.",
            "documentIdentifier": "update_doc_001_custom"
        },
        correction_details={
            "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # HttpUrl Pydantic 模型
            "property_to_correct": "tcm-onto:description"
        }
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once()
    called_kwargs = mock_core_update_entity.call_args.kwargs

    assert called_kwargs["entity_uri"] == entity_uri
    
    expected_add_update = [
        {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
        {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # 期望字符串
    ]
    assert len(called_kwargs["attributes_to_add_or_update"]) == len(expected_add_update)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_add_or_update"], expected_add_update):
        assert actual_item == expected_item

    expected_delete = [
        {"property": "tcm-onto:oldProperty", "value": "旧的值", "datatype": None},
        {"property": "tcm-onto:anotherOldProperty", "value": None, "datatype": None}
    ]
    assert len(called_kwargs["attributes_to_delete"]) == len(expected_delete)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_delete"], expected_delete):
        assert actual_item == expected_item
        
    assert called_kwargs["source_info"] == payload["source"]
    
    expected_correction_details = {
        "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # 期望字符串
        "property_to_correct": "tcm-onto:description"
    }
    assert called_kwargs["correction_details_info"] == expected_correction_details

# --- 测试更新实体API端点 ---
# --- Tests for Update Entity API Endpoint ---

# test_update_entity_success_full_payload 函数已被移除，由下面的 _custom_assert 版本替代
# The test_update_entity_success_full_payload function has been removed, replaced by the _custom_assert version below.

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_minimal_payload(mock_core_update_entity):
    """测试成功更新实体 - 仅包含必需的 source 字段 (Test successful entity update - minimal payload with only required source field)"""
    entity_uri = "http://example.com/entity/minimal_update"
    entity_uri_encoded = quote(entity_uri, safe='')
    
    payload = create_entity_update_payload( # 使用辅助函数创建仅包含 source 的 payload
                                          # Use helper to create payload with only source
        source={"citation": "Minimal citation", "originalText": "Minimal text", "documentIdentifier": "min_doc"}
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once_with(
        entity_uri=entity_uri,
        attributes_to_add_or_update=None,
        attributes_to_delete=None,
        source_info=payload["source"],
        correction_details_info=None,
        conn_manager=ANY # 验证 conn_manager 是否被传递，但不关心其具体值
                         # Verify conn_manager was passed, but don't care about its specific value
    )

def test_update_entity_invalid_payload_missing_source():
    """测试无效请求体 - 缺少必需的 source 字段 (Test invalid payload - missing required source field)"""
    entity_uri_encoded = quote("http://example.com/entity/any_ent", safe='')
    payload = { # 手动构造一个没有 source 的 payload
              # Manually construct a payload without source
        "attributes_to_add_or_update": [{"property": "p", "value": "v"}]
    }
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422 # FastAPI 请求体验证错误
                                       # FastAPI request body validation error
    assert "source" in response.text.lower() # 确保错误信息提到 source
                                           # Ensure error message mentions source

def test_update_entity_invalid_payload_bad_uri_in_correction():
    """测试无效请求体 - correction_details 中的 targetNamedGraphUri 不是有效URL (Test invalid payload - targetNamedGraphUri in correction_details is not a valid URL)"""
    entity_uri_encoded = quote("http://example.com/entity/bad_uri_corr", safe='')
    payload = create_entity_update_payload(
        correction_details={
            "targetNamedGraphUri": "这不是一个有效的URL", # Invalid URL
            "property_to_correct": "tcm-onto:someProp"
        }
    )
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422
    assert "targetNamedGraphUri" in response.text.lower() # 确保错误信息提到 targetNamedGraphUri
                                                        # Ensure error message mentions targetNamedGraphUri

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_value_error(mock_core_update_entity):
    """测试核心逻辑抛出 ValueError (例如，不一致的数据) - 应返回400 (Test core logic throws ValueError - should return 400)"""
    entity_uri_encoded = quote("http://example.com/entity/value_error_case", safe='')
    payload = create_entity_update_payload() # 使用默认有效payload
                                             # Use default valid payload
    
    # 模拟核心 update_entity 函数抛出 ValueError
    # Mock core update_entity function to throw ValueError
    error_message = "核心逻辑错误：例如，修正的属性在列表中找不到。"
    mock_core_update_entity.side_effect = ValueError(error_message)
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 400
    assert error_message in response.json()["detail"]

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_generic_exception(mock_core_update_entity):
    """测试核心逻辑抛出通用 Exception (例如，数据库连接问题) - 应返回500 (Test core logic throws generic Exception - should return 500)"""
    entity_uri_encoded = quote("http://example.com/entity/server_error_case", safe='')
    payload = create_entity_update_payload()
    
    # 模拟核心 update_entity 函数抛出通用 Exception
    # Mock core update_entity function to throw generic Exception
    mock_core_update_entity.side_effect = Exception("模拟的数据库连接超时") # Simulated database connection timeout
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 500
    assert "更新实体时发生意外错误。" in response.json()["detail"] # "An unexpected error occurred while updating the entity."

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_success_full_payload_custom_assert(mock_core_update_entity):
    """测试成功更新实体 - 包含所有可能的字段 (使用自定义断言)"""
    entity_uri = "http://example.com/entity/herb_to_update_custom"
    entity_uri_encoded = quote(entity_uri, safe='')

    payload = create_entity_update_payload(
        attributes_to_add_or_update=[
            {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
            {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # HttpUrl Pydantic 模型会在请求时自动转换为字符串
                                                                                # HttpUrl Pydantic model automatically converts to string on request
        ],
        attributes_to_delete=[
            {"property": "tcm-onto:oldProperty", "value": "旧的值"},
            {"property": "tcm-onto:anotherOldProperty"}
        ],
        source={
            "citation": "Update Source 2023 Custom",
            "originalText": "Entity was updated based on new findings custom.",
            "documentIdentifier": "update_doc_001_custom"
        },
        correction_details={
            "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # HttpUrl Pydantic 模型
            "property_to_correct": "tcm-onto:description"
        }
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once()
    called_kwargs = mock_core_update_entity.call_args.kwargs

    assert called_kwargs["entity_uri"] == entity_uri
    
    expected_add_update = [
        {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
        {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # 期望字符串
    ]
    assert len(called_kwargs["attributes_to_add_or_update"]) == len(expected_add_update)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_add_or_update"], expected_add_update):
        assert actual_item == expected_item

    expected_delete = [
        {"property": "tcm-onto:oldProperty", "value": "旧的值", "datatype": None},
        {"property": "tcm-onto:anotherOldProperty", "value": None, "datatype": None}
    ]
    assert len(called_kwargs["attributes_to_delete"]) == len(expected_delete)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_delete"], expected_delete):
        assert actual_item == expected_item
        
    assert called_kwargs["source_info"] == payload["source"]
    
    expected_correction_details = {
        "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom", # 期望字符串
        "property_to_correct": "tcm-onto:description"
    }
    assert called_kwargs["correction_details_info"] == expected_correction_details

# --- 测试更新实体API端点 ---
# --- Tests for Update Entity API Endpoint ---

# test_update_entity_success_full_payload 函数已被移除，由下面的 _custom_assert 版本替代
# The test_update_entity_success_full_payload function has been removed, replaced by the _custom_assert version below.
# 所有对该函数的引用和其内容都应被删除。
# All references to this function and its content should be removed.

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_minimal_payload(mock_core_update_entity):
    """测试成功更新实体 - 仅包含必需的 source 字段 (Test successful entity update - minimal payload with only required source field)"""
    entity_uri = "http://example.com/entity/minimal_update"
    entity_uri_encoded = quote(entity_uri, safe='')
    
    payload = create_entity_update_payload( # 使用辅助函数创建仅包含 source 的 payload
                                          # Use helper to create payload with only source
        source={"citation": "Minimal citation", "originalText": "Minimal text", "documentIdentifier": "min_doc"}
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once_with(
        entity_uri=entity_uri,
        attributes_to_add_or_update=None,
        attributes_to_delete=None,
        source_info=payload["source"],
        correction_details_info=None,
        conn_manager=ANY # 验证 conn_manager 是否被传递，但不关心其具体值
                         # Verify conn_manager was passed, but don't care about its specific value
    )

def test_update_entity_invalid_payload_missing_source():
    """测试无效请求体 - 缺少必需的 source 字段 (Test invalid payload - missing required source field)"""
    entity_uri_encoded = quote("http://example.com/entity/any_ent", safe='')
    payload = { # 手动构造一个没有 source 的 payload
              # Manually construct a payload without source
        "attributes_to_add_or_update": [{"property": "p", "value": "v"}]
    }
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422 # FastAPI 请求体验证错误
                                       # FastAPI request body validation error
    assert "source" in response.text.lower() # 确保错误信息提到 source
                                           # Ensure error message mentions source

def test_update_entity_invalid_payload_bad_uri_in_correction():
    """测试无效请求体 - correction_details 中的 targetNamedGraphUri 不是有效URL (Test invalid payload - targetNamedGraphUri in correction_details is not a valid URL)"""
    entity_uri_encoded = quote("http://example.com/entity/bad_uri_corr", safe='')
    payload = create_entity_update_payload(
        correction_details={
            "targetNamedGraphUri": "这不是一个有效的URL", # Invalid URL
            "property_to_correct": "tcm-onto:someProp"
        }
    )
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422
    assert "targetNamedGraphUri" in response.text.lower() # 确保错误信息提到 targetNamedGraphUri
                                                        # Ensure error message mentions targetNamedGraphUri

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_value_error(mock_core_update_entity):
    """测试核心逻辑抛出 ValueError (例如，不一致的数据) - 应返回400 (Test core logic throws ValueError - should return 400)"""
    entity_uri_encoded = quote("http://example.com/entity/value_error_case", safe='')
    payload = create_entity_update_payload() # 使用默认有效payload
                                             # Use default valid payload
    
    # 模拟核心 update_entity 函数抛出 ValueError
    # Mock core update_entity function to throw ValueError
    error_message = "核心逻辑错误：例如，修正的属性在列表中找不到。"
    mock_core_update_entity.side_effect = ValueError(error_message)
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 400
    assert error_message in response.json()["detail"]

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_generic_exception(mock_core_update_entity):
    """测试核心逻辑抛出通用 Exception (例如，数据库连接问题) - 应返回500 (Test core logic throws generic Exception - should return 500)"""
    entity_uri_encoded = quote("http://example.com/entity/server_error_case", safe='')
    payload = create_entity_update_payload()
    
    # 模拟核心 update_entity 函数抛出通用 Exception
    # Mock core update_entity function to throw generic Exception
    mock_core_update_entity.side_effect = Exception("模拟的数据库连接超时") # Simulated database connection timeout
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 500
    assert "更新实体时发生意外错误。" in response.json()["detail"] # "An unexpected error occurred while updating the entity."

# 添加一个自定义的比较函数，用于比较包含浮点数的复杂嵌套列表/字典。
# Add a custom comparison function for complex nested lists/dicts containing floats.
# unittest.TestCase.assertListEqual 和 assertDictEqual 对于这种比较不够鲁棒。
# unittest.TestCase.assertListEqual and assertDictEqual are not robust enough for this.
# pytest 提供了 approx 用于浮点数比较，但这里我们需要一个通用的结构比较。
# pytest provides approx for float comparison, but here we need a general structure comparison.
# 为简单起见，这里的测试不涉及浮点数，所以标准的比较应该足够。
# For simplicity, the tests here do not involve floats, so standard comparison should suffice.
# 如果未来需要，可以考虑使用 pytest-json 指南或自定义递归比较。
# If needed in the future, consider using pytest-json guidelines or custom recursive comparison.
# 目前，对于 HttpUrl 转换后的字符串和其它字面量，标准比较是可行的。
# Currently, for strings converted from HttpUrl and other literals, standard comparison is feasible.
# 上面的 test_update_entity_success_full_payload 使用了 self.assertListEqual 和 self.assertDictEqual，
# 这需要将 TestDataFormatter 类改为继承自 unittest.TestCase，或者将这些测试移至 TestDataFormatter 类中。
# The above test_update_entity_success_full_payload uses self.assertListEqual and self.assertDictEqual,
# which requires changing the TestDataFormatter class to inherit from unittest.TestCase,
# or moving these tests into the TestDataFormatter class.
# 由于这些是API端点测试，通常不使用 unittest.TestCase。我们将手动比较列表/字典。
# Since these are API endpoint tests, unittest.TestCase is usually not used. We will compare lists/dicts manually.
# 修正：上面的测试用例不应使用 self.assertListEqual，因为它们不是 unittest.TestCase 的一部分。
# Correction: The test cases above should not use self.assertListEqual as they are not part of unittest.TestCase.
# 将使用简单的 == 进行比较，或对列表中的每个字典进行迭代和比较。
# Will use simple == for comparison, or iterate and compare each dictionary in the list.

# 重新实现 test_update_entity_success_full_payload 中的断言部分以避免 unittest.TestCase 方法
# Re-implement the assertion part in test_update_entity_success_full_payload to avoid unittest.TestCase methods
@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_success_full_payload_custom_assert(mock_core_update_entity):
    """测试成功更新实体 - 包含所有可能的字段 (使用自定义断言)"""
    entity_uri = "http://example.com/entity/herb_to_update_custom"
    entity_uri_encoded = quote(entity_uri, safe='')

    payload = create_entity_update_payload(
        attributes_to_add_or_update=[
            {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
            {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"}
        ],
        attributes_to_delete=[
            {"property": "tcm-onto:oldProperty", "value": "旧的值"},
            {"property": "tcm-onto:anotherOldProperty"}
        ],
        source={
            "citation": "Update Source 2023 Custom",
            "originalText": "Entity was updated based on new findings custom.",
            "documentIdentifier": "update_doc_001_custom"
        },
        correction_details={
            "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom",
            "property_to_correct": "tcm-onto:description"
        }
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once()
    # called_kwargs = mock_core_update_entity.call_args[1] # 修正：call_args 是 (args, kwargs)
    called_kwargs = mock_core_update_entity.call_args.kwargs


    assert called_kwargs["entity_uri"] == entity_uri
    
    expected_add_update = [
        {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
        {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"}
    ]
    # 手动比较列表中的字典 (Manually compare dictionaries in the list)
    assert len(called_kwargs["attributes_to_add_or_update"]) == len(expected_add_update)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_add_or_update"], expected_add_update):
        assert actual_item == expected_item

    expected_delete = [
        {"property": "tcm-onto:oldProperty", "value": "旧的值", "datatype": None},
        {"property": "tcm-onto:anotherOldProperty", "value": None, "datatype": None}
    ]
    assert len(called_kwargs["attributes_to_delete"]) == len(expected_delete)
    for actual_item, expected_item in zip(called_kwargs["attributes_to_delete"], expected_delete):
        assert actual_item == expected_item
        
    assert called_kwargs["source_info"] == payload["source"]
    
    expected_correction_details = {
        "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom",
        "property_to_correct": "tcm-onto:description"
    }
    assert called_kwargs["correction_details_info"] == expected_correction_details

# --- 测试更新实体API端点 ---
# --- Tests for Update Entity API Endpoint ---

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity") # 模拟核心业务逻辑函数
                                                          # Mock the core business logic function
def test_update_entity_success_full_payload(mock_core_update_entity):
    """测试成功更新实体 - 包含所有可能的字段 (Test successful entity update - full payload)"""
    entity_uri = "http://example.com/entity/herb_to_update"
    entity_uri_encoded = quote(entity_uri, safe='') # URL编码实体URI
                                                    # URL-encode the entity URI

    payload = create_entity_update_payload(
        attributes_to_add_or_update=[
            {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
            {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"}
        ],
        attributes_to_delete=[
            {"property": "tcm-onto:oldProperty", "value": "旧的值"},
            {"property": "tcm-onto:anotherOldProperty"}
        ],
        source={
            "citation": "Update Source 2023",
            "originalText": "Entity was updated based on new findings.",
            "documentIdentifier": "update_doc_001"
        },
        correction_details={
            "targetNamedGraphUri": "http://example.com/graph/original_data_graph",
            "property_to_correct": "tcm-onto:description" # 假设 description 是被修正的
                                                          # Assume description is being corrected
        }
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)

    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"} # "Entity updated successfully"

    # 验证核心 update_entity 函数是否被正确调用
    # Verify that the core update_entity function was called correctly
    mock_core_update_entity.assert_called_once()
    call_args = mock_core_update_entity.call_args[1] # 使用关键字参数进行断言
                                                    # Use keyword arguments for assertion

    assert call_args["entity_uri"] == entity_uri
    
    # 验证 attributes_to_add_or_update 的转换
    # Verify transformation of attributes_to_add_or_update
    expected_add_update = [
        {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
        {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"} # HttpUrl 转为 str
    ]
    assert call_args["attributes_to_add_or_update"] == expected_add_update


    # 验证 attributes_to_delete 的转换
    # Verify transformation of attributes_to_delete
    expected_delete = [
        {"property": "tcm-onto:oldProperty", "value": "旧的值", "datatype": None},
        {"property": "tcm-onto:anotherOldProperty", "value": None, "datatype": None}
    ]
    assert call_args["attributes_to_delete"] == expected_delete

    # 验证 source_info
    # Verify source_info
    expected_source_info = payload["source"]
    assert call_args["source_info"] == expected_source_info

    # 验证 correction_details_info
    # Verify correction_details_info
    expected_correction_details = {
        "targetNamedGraphUri": "http://example.com/graph/original_data_graph", # HttpUrl 转为 str
        "property_to_correct": "tcm-onto:description"
    }
    assert call_args["correction_details_info"] == expected_correction_details

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_minimal_payload(mock_core_update_entity):
    """测试成功更新实体 - 仅包含必需的 source 字段 (Test successful entity update - minimal payload with only required source field)"""
    entity_uri = "http://example.com/entity/minimal_update"
    entity_uri_encoded = quote(entity_uri, safe='')
    
    payload = create_entity_update_payload( # 使用辅助函数创建仅包含 source 的 payload
                                          # Use helper to create payload with only source
        source={"citation": "Minimal citation", "originalText": "Minimal text", "documentIdentifier": "min_doc"}
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once_with(
        entity_uri=entity_uri,
        attributes_to_add_or_update=None,
        attributes_to_delete=None,
        source_info=payload["source"],
        correction_details_info=None,
        conn_manager=ANY # 验证 conn_manager 是否被传递，但不关心其具体值
                         # Verify conn_manager was passed, but don't care about its specific value
    )

def test_update_entity_invalid_payload_missing_source():
    """测试无效请求体 - 缺少必需的 source 字段 (Test invalid payload - missing required source field)"""
    entity_uri_encoded = quote("http://example.com/entity/any_ent", safe='')
    payload = { # 手动构造一个没有 source 的 payload
              # Manually construct a payload without source
        "attributes_to_add_or_update": [{"property": "p", "value": "v"}]
    }
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422 # FastAPI 请求体验证错误
                                       # FastAPI request body validation error
    assert "source" in response.text.lower() # 确保错误信息提到 source
                                           # Ensure error message mentions source

def test_update_entity_invalid_payload_bad_uri_in_correction():
    """测试无效请求体 - correction_details 中的 targetNamedGraphUri 不是有效URL (Test invalid payload - targetNamedGraphUri in correction_details is not a valid URL)"""
    entity_uri_encoded = quote("http://example.com/entity/bad_uri_corr", safe='')
    payload = create_entity_update_payload(
        correction_details={
            "targetNamedGraphUri": "这不是一个有效的URL", # Invalid URL
            "property_to_correct": "tcm-onto:someProp"
        }
    )
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 422
    assert "targetNamedGraphUri" in response.text.lower() # 确保错误信息提到 targetNamedGraphUri
                                                        # Ensure error message mentions targetNamedGraphUri

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_value_error(mock_core_update_entity):
    """测试核心逻辑抛出 ValueError (例如，不一致的数据) - 应返回400 (Test core logic throws ValueError - should return 400)"""
    entity_uri_encoded = quote("http://example.com/entity/value_error_case", safe='')
    payload = create_entity_update_payload() # 使用默认有效payload
                                             # Use default valid payload
    
    # 模拟核心 update_entity 函数抛出 ValueError
    # Mock core update_entity function to throw ValueError
    error_message = "核心逻辑错误：例如，修正的属性在列表中找不到。"
    mock_core_update_entity.side_effect = ValueError(error_message)
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 400
    assert error_message in response.json()["detail"]

@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_core_logic_generic_exception(mock_core_update_entity):
    """测试核心逻辑抛出通用 Exception (例如，数据库连接问题) - 应返回500 (Test core logic throws generic Exception - should return 500)"""
    entity_uri_encoded = quote("http://example.com/entity/server_error_case", safe='')
    payload = create_entity_update_payload()
    
    # 模拟核心 update_entity 函数抛出通用 Exception
    # Mock core update_entity function to throw generic Exception
    mock_core_update_entity.side_effect = Exception("模拟的数据库连接超时") # Simulated database connection timeout
    
    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 500
    assert "更新实体时发生意外错误。" in response.json()["detail"] # "An unexpected error occurred while updating the entity."

# 添加一个自定义的比较函数，用于比较包含浮点数的复杂嵌套列表/字典。
# Add a custom comparison function for complex nested lists/dicts containing floats.
# unittest.TestCase.assertListEqual 和 assertDictEqual 对于这种比较不够鲁棒。
# unittest.TestCase.assertListEqual and assertDictEqual are not robust enough for this.
# pytest 提供了 approx 用于浮点数比较，但这里我们需要一个通用的结构比较。
# pytest provides approx for float comparison, but here we need a general structure comparison.
# 为简单起见，这里的测试不涉及浮点数，所以标准的比较应该足够。
# For simplicity, the tests here do not involve floats, so standard comparison should suffice.
# 如果未来需要，可以考虑使用 pytest-json 指南或自定义递归比较。
# If needed in the future, consider using pytest-json guidelines or custom recursive comparison.
# 目前，对于 HttpUrl 转换后的字符串和其它字面量，标准比较是可行的。
# Currently, for strings converted from HttpUrl and other literals, standard comparison is feasible.
# 上面的 test_update_entity_success_full_payload 使用了 self.assertListEqual 和 self.assertDictEqual，
# 这需要将 TestDataFormatter 类改为继承自 unittest.TestCase，或者将这些测试移至 TestDataFormatter 类中。
# The above test_update_entity_success_full_payload uses self.assertListEqual and self.assertDictEqual,
# which requires changing the TestDataFormatter class to inherit from unittest.TestCase,
# or moving these tests into the TestDataFormatter class.
# 由于这些是API端点测试，通常不使用 unittest.TestCase。我们将手动比较列表/字典。
# Since these are API endpoint tests, unittest.TestCase is usually not used. We will compare lists/dicts manually.
# 修正：上面的测试用例不应使用 self.assertListEqual，因为它们不是 unittest.TestCase 的一部分。
# Correction: The test cases above should not use self.assertListEqual as they are not part of unittest.TestCase.
# 将使用简单的 == 进行比较，或对列表中的每个字典进行迭代和比较。
# Will use simple == for comparison, or iterate and compare each dictionary in the list.

# 重新实现 test_update_entity_success_full_payload 中的断言部分以避免 unittest.TestCase 方法
# Re-implement the assertion part in test_update_entity_success_full_payload to avoid unittest.TestCase methods
@patch("tcm_kg_virtuoso_module.api.endpoints.update_entity")
def test_update_entity_success_full_payload_custom_assert(mock_core_update_entity):
    """测试成功更新实体 - 包含所有可能的字段 (使用自定义断言)"""
    entity_uri = "http://example.com/entity/herb_to_update_custom"
    entity_uri_encoded = quote(entity_uri, safe='')

    payload = create_entity_update_payload(
        attributes_to_add_or_update=[
            {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
            {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"}
        ],
        attributes_to_delete=[
            {"property": "tcm-onto:oldProperty", "value": "旧的值"},
            {"property": "tcm-onto:anotherOldProperty"}
        ],
        source={
            "citation": "Update Source 2023 Custom",
            "originalText": "Entity was updated based on new findings custom.",
            "documentIdentifier": "update_doc_001_custom"
        },
        correction_details={
            "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom",
            "property_to_correct": "tcm-onto:description"
        }
    )

    response = client.put(f"/api/v1/tcm/graph/entities/{entity_uri_encoded}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "实体已成功更新"}

    mock_core_update_entity.assert_called_once()
    call_args = mock_core_update_entity.call_args[1]

    assert call_args["entity_uri"] == entity_uri
    
    expected_add_update = [
        {"property": "tcm-onto:description", "value": "新的描述", "datatype": "xsd:string"},
        {"property": "rdfs:seeAlso", "value": "http://example.com/new_link"}
    ]
    # 手动比较列表中的字典 (Manually compare dictionaries in the list)
    assert len(call_args["attributes_to_add_or_update"]) == len(expected_add_update)
    for actual_item, expected_item in zip(call_args["attributes_to_add_or_update"], expected_add_update):
        assert actual_item == expected_item

    expected_delete = [
        {"property": "tcm-onto:oldProperty", "value": "旧的值", "datatype": None},
        {"property": "tcm-onto:anotherOldProperty", "value": None, "datatype": None}
    ]
    assert len(call_args["attributes_to_delete"]) == len(expected_delete)
    for actual_item, expected_item in zip(call_args["attributes_to_delete"], expected_delete):
        assert actual_item == expected_item
        
    assert call_args["source_info"] == payload["source"]
    
    expected_correction_details = {
        "targetNamedGraphUri": "http://example.com/graph/original_data_graph_custom",
        "property_to_correct": "tcm-onto:description"
    }
    assert call_args["correction_details_info"] == expected_correction_details
