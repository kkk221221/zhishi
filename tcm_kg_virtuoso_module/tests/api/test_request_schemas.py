import pytest
from pydantic import HttpUrl, ValidationError, Field
from typing import List, Dict, Any, Optional

from tcm_kg_virtuoso_module.api.request_schemas import (
    Attribute, 
    Source, 
    EntityCreate, 
    RelationshipCreate,
    AttributeUpdate, # 新增导入
    AttributeIdentifier, # 新增导入
    CorrectionDetails, # 新增导入
    EntityUpdate # 新增导入
)

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
    with pytest.raises(ValidationError, match="URL scheme should be 'http' or 'https'"):
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


def test_relationship_create_model():
    valid_source_data = {
        "citation": "Relationship Source Citation",
        "originalText": "Relationship original text.",
        "documentIdentifier": "doc_rel_456"
    }
    valid_relationship_data = {
        "subjectUri": "http://example.com/subject/herb1",
        "predicate": "tcm-onto:hasSymptom",
        "objectUri": "http://example.com/object/symptom1",
        "source": valid_source_data
    }

    # Test valid model instantiation
    rel = RelationshipCreate(**valid_relationship_data)
    assert rel.subjectUri == HttpUrl("http://example.com/subject/herb1")
    assert rel.predicate == "tcm-onto:hasSymptom"
    assert rel.objectUri == HttpUrl("http://example.com/object/symptom1")
    assert rel.source.citation == valid_source_data["citation"]

    # Test missing subjectUri
    with pytest.raises(ValidationError) as excinfo:
        data = valid_relationship_data.copy()
        del data["subjectUri"]
        RelationshipCreate(**data)
    assert "subjectUri" in str(excinfo.value)

    # Test missing predicate
    with pytest.raises(ValidationError) as excinfo:
        data = valid_relationship_data.copy()
        del data["predicate"]
        RelationshipCreate(**data)
    assert "predicate" in str(excinfo.value)

    # Test missing objectUri
    with pytest.raises(ValidationError) as excinfo:
        data = valid_relationship_data.copy()
        del data["objectUri"]
        RelationshipCreate(**data)
    assert "objectUri" in str(excinfo.value)

    # Test missing source
    with pytest.raises(ValidationError) as excinfo:
        data = valid_relationship_data.copy()
        del data["source"]
        RelationshipCreate(**data)
    assert "source" in str(excinfo.value)

    # Test invalid subjectUri (not a URL)
    with pytest.raises(ValidationError) as excinfo:
        data = valid_relationship_data.copy()
        data["subjectUri"] = "not-a-url"
        RelationshipCreate(**data)
    assert "subjectUri" in str(excinfo.value)
    error_str = str(excinfo.value)
    assert "Input should be a valid URL" in error_str or "url_parsing" in error_str


    # Test invalid objectUri (not a URL)
    with pytest.raises(ValidationError) as excinfo:
        data = valid_relationship_data.copy()
        data["objectUri"] = "ftp://invalid.url" # HttpUrl expects http or https
        RelationshipCreate(**data)
    assert "objectUri" in str(excinfo.value)
    assert "URL scheme should be 'http' or 'https'" in str(excinfo.value)

    # Test invalid predicate type (not a string)
    with pytest.raises(ValidationError) as excinfo:
        data = valid_relationship_data.copy()
        data["predicate"] = 12345
        RelationshipCreate(**data)
    assert "predicate" in str(excinfo.value)
    assert "Input should be a valid string" in str(excinfo.value)


    # Test invalid source data (e.g., missing 'citation' in source)
    with pytest.raises(ValidationError) as excinfo:
        data = valid_relationship_data.copy()
        invalid_source = valid_source_data.copy()
        del invalid_source["citation"]
        data["source"] = invalid_source
        RelationshipCreate(**data)
    # This will show a validation error within the 'source' field
    assert "source" in str(excinfo.value)
    assert "citation" in str(excinfo.value) # More specific check for missing field in submodel
    assert "Field required" in str(excinfo.value)


# --- 测试新增的实体更新相关模型 ---
# --- Tests for new entity update related models ---

def test_attribute_update_model():
    """测试 AttributeUpdate Pydantic 模型 (测试属性更新模型)"""
    # 基本有效数据 (Basic valid data)
    attr_update = AttributeUpdate(property="tcm-onto:hasDescription", value="新的描述信息")
    assert attr_update.property == "tcm-onto:hasDescription"
    assert attr_update.value == "新的描述信息"
    assert attr_update.datatype is None

    # 包含数据类型 (Including datatype)
    attr_update_dt = AttributeUpdate(property="tcm-onto:hasQuantity", value="10.5", datatype="xsd:decimal")
    assert attr_update_dt.datatype == "xsd:decimal"

    # value 可以是 HttpUrl (value can be HttpUrl)
    attr_update_uri = AttributeUpdate(property="rdfs:seeAlso", value=HttpUrl("http://example.com/resource"))
    assert attr_update_uri.value == HttpUrl("http://example.com/resource")
    
    # value 可以是数字或布尔值 (value can be a number or boolean)
    attr_update_int = AttributeUpdate(property="tcm-onto:order", value=1)
    assert attr_update_int.value == 1
    attr_update_bool = AttributeUpdate(property="tcm-onto:isActive", value=True)
    assert attr_update_bool.value is True

    # 缺少必需的 'property' 字段 (Missing required 'property' field)
    with pytest.raises(ValidationError) as excinfo:
        AttributeUpdate(value="缺少属性")
    assert "property" in str(excinfo.value).lower() # 检查错误信息中是否包含 'property'
                                                 # Check if 'property' is mentioned in the error message

    # 'property' 不是字符串 ('property' is not a string)
    with pytest.raises(ValidationError) as excinfo:
        AttributeUpdate(property=123, value="属性为数字")
    assert "property" in str(excinfo.value).lower()
    assert "string" in str(excinfo.value).lower() # 应该提示 property 需要是字符串
                                                 # Should indicate that property needs to be a string


def test_attribute_identifier_model():
    """测试 AttributeIdentifier Pydantic 模型 (测试属性标识符模型)"""
    # 仅提供 property (Only property provided)
    attr_id_prop_only = AttributeIdentifier(property="tcm-onto:hasObsoleteDescription")
    assert attr_id_prop_only.property == "tcm-onto:hasObsoleteDescription"
    assert attr_id_prop_only.value is None
    assert attr_id_prop_only.datatype is None

    # 提供 property 和 value (Property and value provided)
    attr_id_with_val = AttributeIdentifier(property="tcm-onto:hasKeyword", value="旧关键词")
    assert attr_id_with_val.value == "旧关键词"

    # 提供所有字段 (All fields provided)
    attr_id_full = AttributeIdentifier(property="tcm-onto:hasNumericValue", value="100", datatype="xsd:integer")
    assert attr_id_full.datatype == "xsd:integer"

    # value 可以是 HttpUrl (value can be HttpUrl)
    attr_id_uri = AttributeIdentifier(property="rdfs:seeAlso", value=HttpUrl("http://example.com/old_resource"))
    assert attr_id_uri.value == HttpUrl("http://example.com/old_resource")

    # 缺少必需的 'property' 字段 (Missing required 'property' field)
    with pytest.raises(ValidationError) as excinfo:
        AttributeIdentifier(value="缺少属性标识") # 尝试创建一个没有 property 的 AttributeIdentifier
                                              # Try to create an AttributeIdentifier without a property
    assert "property" in str(excinfo.value).lower()

def test_correction_details_model():
    """测试 CorrectionDetails Pydantic 模型 (测试修正详情模型)"""
    # 有效数据 (Valid data)
    correction = CorrectionDetails(
        targetNamedGraphUri="http://example.com/graph/old_source_1",
        property_to_correct="tcm-onto:hasMistake"
    )
    assert correction.targetNamedGraphUri == HttpUrl("http://example.com/graph/old_source_1")
    assert correction.property_to_correct == "tcm-onto:hasMistake"

    # 缺少 targetNamedGraphUri (Missing targetNamedGraphUri)
    with pytest.raises(ValidationError) as excinfo:
        CorrectionDetails(property_to_correct="tcm-onto:hasError")
    assert "targetnamedgraphuri" in str(excinfo.value).lower() # CORRECTED

    # targetNamedGraphUri 不是有效的URL (targetNamedGraphUri is not a valid URL)
    with pytest.raises(ValidationError) as excinfo:
        CorrectionDetails(targetNamedGraphUri="不是一个URL", property_to_correct="tcm-onto:hasError")
    assert "targetnamedgraphuri" in str(excinfo.value).lower() # CORRECTED
    assert "url" in str(excinfo.value).lower() # 提示URL相关错误
                                             # Hint URL related error

    # 缺少 property_to_correct (Missing property_to_correct)
    with pytest.raises(ValidationError) as excinfo:
        CorrectionDetails(targetNamedGraphUri="http://example.com/graph/g1")
    assert "property_to_correct" in str(excinfo.value).lower()


def test_entity_update_model():
    """测试 EntityUpdate Pydantic 模型 (测试实体更新模型)"""
    valid_source_data = {"citation": "新来源", "originalText": "新文本", "documentIdentifier": "new_doc_1"}

    # 仅包含 source (Only source provided)
    update_minimal = EntityUpdate(source=valid_source_data)
    assert update_minimal.source.citation == "新来源"
    assert update_minimal.attributes_to_add_or_update is None  # 验证默认值为 None
    # Verify default value is None
    assert update_minimal.attributes_to_delete is None
    assert update_minimal.correction_details is None

    # 包含所有可选字段 (Including all optional fields)
    update_full = EntityUpdate(
        attributes_to_add_or_update=[
            {"property": "tcm-onto:newProp", "value": "新值"},
            {"property": "tcm-onto:anotherNewProp", "value": 123, "datatype": "xsd:integer"}
        ],
        attributes_to_delete=[
            {"property": "tcm-onto:oldProp"},
            {"property": "tcm-onto:specificOldProp", "value": "待删除的值"}
        ],
        source=valid_source_data,
        correction_details={
            "targetNamedGraphUri": "http://example.com/graph/g1",
            "property_to_correct": "tcm-onto:propToCorrect"
        }
    )
    assert len(update_full.attributes_to_add_or_update) == 2
    assert update_full.attributes_to_add_or_update[0].value == "新值"
    assert len(update_full.attributes_to_delete) == 2
    assert update_full.attributes_to_delete[1].value == "待删除的值"
    assert update_full.correction_details.property_to_correct == "tcm-onto:propToCorrect"

    # 测试 `attributes_to_add_or_update` 列表为空的情况 (Test case with empty list for `attributes_to_add_or_update`)
    update_empty_add = EntityUpdate(attributes_to_add_or_update=[], source=valid_source_data)
    assert update_empty_add.attributes_to_add_or_update == []

    # 缺少必需的 'source' (Missing required 'source')
    with pytest.raises(ValidationError) as excinfo:
        EntityUpdate(attributes_to_add_or_update=[{"property": "p", "value": "v"}])
    assert "source" in str(excinfo.value).lower()

    # 'attributes_to_add_or_update' 中包含无效的 AttributeUpdate (Invalid AttributeUpdate in 'attributes_to_add_or_update')
    with pytest.raises(ValidationError) as excinfo:
        EntityUpdate(attributes_to_add_or_update=[{"value_typo": "错误的值"}],
                     source=valid_source_data)  # 'value_typo' 而不是 'value'，且缺少 'property'
        # 'value_typo' instead of 'value', and missing 'property'
    assert "attributes_to_add_or_update" in str(excinfo.value).lower()  # 错误发生在列表的元素中
    # Error occurs in the elements of the list
    assert "property" in str(excinfo.value).lower()  # 具体的错误是 AttributeUpdate 缺少 property
    # The specific error is AttributeUpdate missing property

    # 'attributes_to_delete' 中包含无效的 AttributeIdentifier (Invalid AttributeIdentifier in 'attributes_to_delete')
    with pytest.raises(ValidationError) as excinfo:
        EntityUpdate(attributes_to_delete=[{"value_only": "仅有值"}], source=valid_source_data)  # 缺少 'property'
        # Missing 'property'
    assert "attributes_to_delete" in str(excinfo.value).lower()
    assert "property" in str(excinfo.value).lower()

    # 'correction_details' 中包含无效的 CorrectionDetails (Invalid CorrectionDetails in 'correction_details')
    with pytest.raises(ValidationError) as excinfo:
        EntityUpdate(correction_details={"targetNamedGraphUri_typo": "错误的URI"}, source=valid_source_data)  # 字段名错误
        # Incorrect field name
    assert "correction_details" in str(excinfo.value).lower()
    assert "targetnamedgraphuri" in str(excinfo.value).lower()  # CORRECTED # CorrectionDetails 缺少 targetNamedGraphUri
    # CorrectionDetails missing targetNamedGraphUri
    assert "property_to_correct" in str(excinfo.value).lower()  # CorrectionDetails 缺少 property_to_correct
    # CorrectionDetails missing property_to_correct
