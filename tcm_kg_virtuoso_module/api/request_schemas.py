# api/request_schemas.py
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Any, Optional

class Attribute(BaseModel):
    property: str
    value: Any # Can be str, List[str], or HttpUrl for links

class Source(BaseModel):
    citation: str # 引文信息
    originalText: str # 原始文本
    documentIdentifier: str # 文档标识符

class EntityCreate(BaseModel):
    type: str # 实体类型
    label: str # 实体标签
    attributes: List[Attribute] # 实体属性列表
    source: Source # 实体来源信息

class RelationshipCreate(BaseModel):
    subjectUri: HttpUrl # 主体URI
    predicate: str  # 谓词CURIE, 例如 "tcm-onto:hasSymptom"
    objectUri: HttpUrl # 객체 URI
    source: Source # 关系来源信息

# --- 新增用于实体更新的模型 ---
# --- New models for entity update ---

class AttributeUpdate(BaseModel):
    property: str  # 属性的CURIE或完整URI (Property's CURIE or full URI)
    value: Any  # 属性值，可以是字面量或另一个实体的URI (HttpUrl)。具体类型检查在后续逻辑中处理。
                # (Attribute value, can be a literal or URI of another entity (HttpUrl). Specific type checks handled in subsequent logic.)
    datatype: Optional[str] = None  # 如果value是字面量且需要特定数据类型，则指定 (例如 "xsd:string", "xsd:integer")
                                   # (If value is a literal and needs a specific datatype, specify here (e.g., "xsd:string", "xsd:integer"))
    # 中文注释：用于指定要添加或更新的属性及其新值。
    # 如果属性已存在，其旧值将被替换（Scenario 1），或者在特定命名图中被修正（Scenario 2）。
    # (Chinese comment: Used to specify the attribute to be added or updated and its new value.
    # If the attribute already exists, its old value will be replaced (Scenario 1), or corrected in a specific named graph (Scenario 2).)

class AttributeIdentifier(BaseModel):
    property: str  # 要删除属性的CURIE或完整URI (CURIE or full URI of the attribute to be deleted)
    value: Optional[Any] = None  # 可选，如果要删除特定属性-值对中的值。具体类型匹配在后续逻辑中处理。
                                # (Optional, if deleting a value in a specific property-value pair. Specific type matching handled in subsequent logic.)
    datatype: Optional[str] = None  # 可选，如果value是字面量且需要匹配特定数据类型
                                   # (Optional, if value is a literal and needs to match a specific datatype)
    # 中文注释：用于指定要删除的属性。
    # 如果只提供property，则删除所有具有该属性的三元组。
    # 如果同时提供property和value，则仅删除匹配的特定三元组。
    # (Chinese comment: Used to specify the attribute to be deleted.
    # If only 'property' is provided, all triples with this property will be deleted.
    # If both 'property' and 'value' are provided, only the specific matching triple will be deleted.)

class CorrectionDetails(BaseModel):
    targetNamedGraphUri: HttpUrl  # 需要修正的三元组所在的命名图URI (Named graph URI where the triple to be corrected resides)
    property_to_correct: str  # 在目标命名图中需要修正其值的属性的CURIE或完整URI
                             # (CURIE or full URI of the property whose value needs to be corrected in the target named graph)
    # 中文注释：用于指定在特定原始来源图中进行修正操作的细节。
    # (Chinese comment: Used to specify details for correction operations within a specific original source graph.)

class EntityUpdate(BaseModel):
    attributes_to_add_or_update: Optional[List[AttributeUpdate]] = Field(default=None) # 要添加或更新的属性列表
                                                                                      # (List of attributes to add or update)
    attributes_to_delete: Optional[List[AttributeIdentifier]] = Field(default=None)    # 要删除的属性列表
                                                                                      # (List of attributes to delete)
    source: Source  # 适用于此请求中所有 "attributes_to_add_or_update" 操作的新来源信息，或用于Scenario 2的来源元数据更新
                    # (New source information applicable to all "attributes_to_add_or_update" operations in this request, or for source metadata update in Scenario 2)
    correction_details: Optional[CorrectionDetails] = Field(default=None) # 修正操作的详细信息
                                                                         # (Details for correction operation)
    # 中文注释：用于更新实体的请求体结构。
    # 它允许添加/更新属性、删除属性，并指定操作的来源。
    # correction_details用于在特定来源上下文中修正断言。
    # (Chinese comment: Request body structure for updating an entity.
    # It allows adding/updating attributes, deleting attributes, and specifying the source of the operation.
    # 'correction_details' is used to correct assertions in a specific source context.)
