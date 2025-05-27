import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from tcm_kg_virtuoso_module.main import app 
from tcm_kg_virtuoso_module.api.request_schemas import EntityCreate, SourceModel

client = TestClient(app)

@pytest.fixture
def valid_entity_payload():
    return {
        "entity_type_name": "Herb",
        "label": "Ginseng",
        "properties": {"tcm-onto:hasTaste": "Sweet"},
        "source_details": {
            "citation": "Bencao Gangmu, Vol. 1",
            "original_text": "人参，味甘，大补元气。",
            "document_identifier": "BencaoGangmu_Vol1",
            "source_type": "ClassicalBook",
            "source_section": "Herbs",
            "source_subsection": "Ginseng",
            "uri_args": ["extra", "args"]
        },
        "entity_id_args": ["RenShen", "001"]
    }

def test_create_entity_success(valid_entity_payload):
    expected_uri = "http://tcm.example.org/entity/Herb_Ginseng_RenShen_001"
    
    with patch("tcm_kg_virtuoso_module.api.endpoints.add_entity") as mock_add_entity:
        mock_add_entity.return_value = expected_uri
        
        response = client.post("/api/v1/tcm/graph/entities", json=valid_entity_payload)
        
        assert response.status_code == 201
        response_json = response.json()
        assert response_json["uri"] == expected_uri
        assert response_json["message"] == "Entity created successfully"
        
        expected_call_payload = {
            "entity_type_name": valid_entity_payload["entity_type_name"],
            "entity_label": valid_entity_payload["label"],
            "entity_properties": valid_entity_payload["properties"],
            "source_details": valid_entity_payload["source_details"],
            "entity_id_args": valid_entity_payload["entity_id_args"]
        }
        mock_add_entity.assert_called_once()
        args, kwargs = mock_add_entity.call_args
        assert args[0] == expected_call_payload

def test_create_entity_validation_error(valid_entity_payload):
    invalid_payload = valid_entity_payload.copy()
    del invalid_payload["label"] 
    
    response = client.post("/api/v1/tcm/graph/entities", json=invalid_payload)
    
    assert response.status_code == 422 
    response_json = response.json()
    assert "detail" in response_json
    assert any(err["loc"] == ["body", "label"] and err["type"] == "missing" for err in response_json["detail"])

def test_create_entity_value_error_from_add_entity(valid_entity_payload):
    error_message = "Validation failed in add_entity"
    with patch("tcm_kg_virtuoso_module.api.endpoints.add_entity") as mock_add_entity:
        mock_add_entity.side_effect = ValueError(error_message)
        
        response = client.post("/api/v1/tcm/graph/entities", json=valid_entity_payload)
        
        assert response.status_code == 400
        assert response.json()["detail"] == error_message

def test_create_entity_generic_error_from_add_entity(valid_entity_payload):
    error_message = "Database connection failed"
    with patch("tcm_kg_virtuoso_module.api.endpoints.add_entity") as mock_add_entity:
        mock_add_entity.side_effect = Exception(error_message) 
        
        response = client.post("/api/v1/tcm/graph/entities", json=valid_entity_payload)
        
        assert response.status_code == 500
        assert response.json()["detail"] == "An internal error occurred: Exception"
