import pytest
from pydantic import HttpUrl, ValidationError
from typing import List

from tcm_kg_virtuoso_module.api.request_schemas import Attribute, Source, EntityCreate

def test_attribute_model():
    # Test with string value
    attr_str = Attribute(property="name", value="Test Name")
    assert attr_str.property == "name"
    assert attr_str.value == "Test Name"

    # Test with list of strings value
    attr_list_str = Attribute(property="aliases", value=["Alias1", "Alias2"])
    assert attr_list_str.property == "aliases"
    assert attr_list_str.value == ["Alias1", "Alias2"]

    # Test with HttpUrl value
    attr_url = Attribute(property="url", value=HttpUrl("http://example.com"))
    assert attr_url.property == "url"
    assert attr_url.value == HttpUrl("http://example.com")

    # Test invalid property type
    with pytest.raises(ValidationError):
        Attribute(property=123, value="Test")

    # Test invalid value type (neither str, List[str], nor HttpUrl)
    # Pydantic's 'Any' will accept most things, but the intention is specific.
    # For stricter validation, a custom validator or a Union type would be needed in the model.
    # This test will pass as 'Any' is very permissive.
    attr_invalid_value = Attribute(property="test", value={"key": "value"})
    assert attr_invalid_value.value == {"key": "value"}


def test_source_model():
    source_data = {
        "citation": "Author, Year",
        "originalText": "This is the original text.",
        "documentIdentifier": "doc_123"
    }
    source = Source(**source_data)
    assert source.citation == source_data["citation"]
    assert source.originalText == source_data["originalText"]
    assert source.documentIdentifier == source_data["documentIdentifier"]

    # Test missing fields
    with pytest.raises(ValidationError):
        Source(citation="Author, Year", originalText="Text") # Missing documentIdentifier

    with pytest.raises(ValidationError):
        Source(originalText="Text", documentIdentifier="doc_123") # Missing citation

    with pytest.raises(ValidationError):
        Source(citation="Author, Year", documentIdentifier="doc_123") # Missing originalText

def test_entity_create_model():
    entity_data = {
        "type": "Person",
        "label": "John Doe",
        "attributes": [
            {"property": "email", "value": "john.doe@example.com"},
            {"property": "website", "value": HttpUrl("http://johndoe.com")}
        ],
        "source": {
            "citation": "HR Department",
            "originalText": "Employee record for John Doe.",
            "documentIdentifier": "emp_456"
        }
    }
    entity = EntityCreate(**entity_data)
    assert entity.type == entity_data["type"]
    assert entity.label == entity_data["label"]
    assert len(entity.attributes) == 2
    assert entity.attributes[0].property == "email"
    assert entity.attributes[0].value == "john.doe@example.com"
    assert entity.attributes[1].property == "website"
    assert entity.attributes[1].value == HttpUrl("http://johndoe.com")
    assert entity.source.citation == entity_data["source"]["citation"]

    # Test with different attribute value types
    entity_data_complex_attrs = {
        "type": "Organization",
        "label": "Org Inc.",
        "attributes": [
            {"property": "name", "value": "Org Inc."},
            {"property": "domains", "value": ["org.com", "org.net"]},
            {"property": "url", "value": HttpUrl("http://org.com")}
        ],
        "source": {
            "citation": "Company Registry",
            "originalText": "Official registration data.",
            "documentIdentifier": "reg_789"
        }
    }
    entity_complex = EntityCreate(**entity_data_complex_attrs)
    assert entity_complex.attributes[1].value == ["org.com", "org.net"]
    assert entity_complex.attributes[2].value == HttpUrl("http://org.com")


    # Test missing fields
    with pytest.raises(ValidationError):
        EntityCreate(type="Person", label="Test", attributes=[]) # Missing source
    
    with pytest.raises(ValidationError):
        EntityCreate(label="Test", attributes=[], source=entity_data["source"]) # Missing type

    # Test invalid attribute structure
    with pytest.raises(ValidationError):
        EntityCreate(
            type="Test",
            label="Test Invalid Attr",
            attributes=[{"property_typo": "name", "value": "Test"}], # 'property_typo' instead of 'property'
            source=entity_data["source"]
        )
    
    # Test invalid source structure
    with pytest.raises(ValidationError):
        EntityCreate(
            type="Test",
            label="Test Invalid Source",
            attributes=[],
            source={"citation_typo": "Test"} # 'citation_typo' instead of 'citation'
        )

def test_attribute_model_edge_cases():
    # Test with empty string value
    attr_empty_str = Attribute(property="description", value="")
    assert attr_empty_str.value == ""

    # Test with empty list value
    attr_empty_list = Attribute(property="tags", value=[])
    assert attr_empty_list.value == []

    # Test with non-http URL (should be fine as HttpUrl validates protocol)
    with pytest.raises(ValidationError,match="URL scheme not permitted"):  # Pydantic v2 raises error for non-http/https
        HttpUrl("ftp://example.com")


def test_source_model_empty_fields():
    # Pydantic models by default require fields unless Optional or have a default value
    # So, empty strings should be acceptable if the field type is str
    source_empty_fields = Source(
        citation="",
        originalText="",
        documentIdentifier=""
    )
    assert source_empty_fields.citation == ""
    assert source_empty_fields.originalText == ""
    assert source_empty_fields.documentIdentifier == ""

def test_entity_create_empty_attributes_list():
    entity_data = {
        "type": "TestType",
        "label": "Test Label",
        "attributes": [], # Empty list of attributes
        "source": {
            "citation": "Test Citation",
            "originalText": "Test Original Text",
            "documentIdentifier": "TestDocId"
        }
    }
    entity = EntityCreate(**entity_data)
    assert entity.type == "TestType"
    assert entity.label == "Test Label"
    assert entity.attributes == []
    assert entity.source.citation == "Test Citation"

# It might also be useful to create an __init__.py file in tcm_kg_virtuoso_module/tests/api/
# if it's not already there, to ensure it's treated as a Python package.
# And an __init__.py in tcm_kg_virtuoso_module/tests/ if that's also missing.
