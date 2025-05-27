# tcm_kg_virtuoso_module/api/schemas.py
from pydantic import BaseModel, Field, AnyUrl # AnyUrl for URI validation by Pydantic
from typing import List, Dict, Any, Optional, Union

# --- 通用模式 ---
class ResponseMessage(BaseModel):
    """通用消息响应模型"""
    message: str
    detail: Optional[str] = None
    success: bool = True # 默认为操作成功

# --- 实体相关模式 ---
class EntityPropertiesSchema(BaseModel):
    """
    实体属性的灵活表示。
    属性值可以是单个值或值列表。
    实际应用中，更具体的类型校验可能需要通过自定义校验器或更细化的模型实现。
    """
    # 使用 Dict[AnyUrl, Union[Any, List[Any]]] 来表示属性字典
    # 键是属性的URI (使用 AnyUrl 进行 Pydantic 级别的初步校验)
    # 值可以是单个值或值列表
    properties: Dict[AnyUrl, Union[Any, List[Any]]] = Field(default_factory=dict, description="实体的属性字典，键为属性URI，值为单个值或值列表")

    class Config:
        title = "实体属性" # OpenAPI文档中的标题
        # anystr_strip_whitespace = True # 可选：自动去除字符串两端空白

class EntitySchema(BaseModel):
    """实体数据显示的基础模型"""
    uri: AnyUrl = Field(description="实体的唯一标识符 (URI)")
    entity_types: List[AnyUrl] = Field(default_factory=list, description="实体类型列表 (URI)")
    properties: Dict[AnyUrl, Union[Any, List[Any]]] = Field(default_factory=dict, description="实体的属性字典")
    
    class Config:
        title = "实体响应"
        orm_mode = True # 如果直接从ORM对象转换 (例如，如果TCMEntity是Pydantic模型或兼容的)

class CreateEntitySchema(BaseModel):
    """创建新实体的请求体模型"""
    # URI通常在服务端生成，但允许客户端提供一个后缀或完整URI（如果业务逻辑允许）
    uri_suffix: Optional[str] = Field(None, description="用于生成URI的后缀 (如果服务端生成URI)")
    entity_type_key_for_uri: Optional[str] = Field("tcm_entity", description="在config.NAMESPACES中用于生成URI的实体类型键名")
    
    entity_types: List[AnyUrl] = Field(..., description="实体类型列表 (URI)，至少需要一个类型。") # ... 表示此字段为必需
    properties: Dict[AnyUrl, Union[Any, List[Any]]] = Field(default_factory=dict, description="实体的属性字典")

    class Config:
        title = "创建实体请求"

class UpdateEntitySchema(BaseModel):
    """更新实体信息的请求体模型 (暂定，具体字段根据服务层实现调整)"""
    properties_to_add: Optional[Dict[AnyUrl, Union[Any, List[Any]]]] = Field(None, description="要添加或更新的属性")
    # properties_to_delete: Optional[List[AnyUrl]] = Field(None, description="要删除的属性的URI列表") # 或者更复杂的结构，如指定属性和值
    types_to_add: Optional[List[AnyUrl]] = Field(None, description="要添加的实体类型")
    types_to_remove: Optional[List[AnyUrl]] = Field(None, description="要移除的实体类型")

    class Config:
        title = "更新实体请求"


# --- 关系相关模式 ---
class RelationshipSchema(BaseModel):
    """关系数据显示的基础模型"""
    source_uri: AnyUrl = Field(description="源实体的URI")
    predicate_uri: AnyUrl = Field(description="谓词的URI")
    target_uri: Union[AnyUrl, str] = Field(description="目标实体的URI或字面量值") # 目标可以是URI或字面量
    properties: Optional[Dict[AnyUrl, Any]] = Field(None, description="关系自身的属性 (如果支持)")

    class Config:
        title = "关系响应"
        orm_mode = True

class CreateRelationshipSchema(BaseModel):
    """创建新关系的请求体模型"""
    source_uri: AnyUrl = Field(..., description="源实体的URI")
    predicate_uri: AnyUrl = Field(..., description="谓词的URI")
    target_uri: Union[AnyUrl, str] = Field(..., description="目标实体的URI或字面量值")
    properties: Optional[Dict[AnyUrl, Any]] = Field(None, description="关系自身的属性 (如果支持)")

    class Config:
        title = "创建关系请求"

class DeleteRelationshipSchema(BaseModel):
    """删除特定关系的请求体模型"""
    source_uri: AnyUrl = Field(..., description="源实体的URI")
    predicate_uri: AnyUrl = Field(..., description="谓词的URI")
    target_uri: Union[AnyUrl, str] = Field(..., description="目标实体的URI或字面量值")

    class Config:
        title = "删除关系请求"


# --- 批量操作相关模式 ---
class TripleSchema(BaseModel):
    """单个三元组的数据模型"""
    subject: AnyUrl = Field(description="三元组的主语 (URI)")
    predicate: AnyUrl = Field(description="三元组的谓语 (URI)")
    object_val: Union[AnyUrl, str, int, float, bool] = Field(description="三元组的宾语 (URI或字面量)") # 使用 object_val 避免与Python关键字冲突

    class Config:
        title = "三元组"

class BulkInsertTriplesRequest(BaseModel):
    """批量插入三元组的请求体模型"""
    triples: List[TripleSchema] = Field(..., description="要插入的三元组列表")
    graph_uri: Optional[AnyUrl] = Field(None, description="目标图的URI (如果为空，则使用默认图)")

    class Config:
        title = "批量插入三元组请求"

# 示例 (用于理解，非实际API模型)
if __name__ == '__main__':
    # 实体示例
    entity_data = {
        "uri": "http://example.com/entity/herb/Ginseng",
        "entity_types": ["http://example.com/ontology/tcm#Herb"],
        "properties": {
            "http://www.w3.org/2000/01/rdf-schema#label": "人参",
            "http://example.com/ontology/tcm#hasTaste": ["http://example.com/entity/taste/Sweet", "http://example.com/entity/taste/Bitter"]
        }
    }
    entity_obj = EntitySchema(**entity_data)
    print("实体示例:", entity_obj.json(indent=2, ensure_ascii=False))

    # 创建实体请求示例
    create_entity_req = {
        "uri_suffix": "MyNewHerb",
        "entity_type_key_for_uri": "tcm_entity",
        "entity_types": ["http://example.com/ontology/tcm#Herb"],
        "properties": {"http://www.w3.org/2000/01/rdf-schema#label": "我的新草药"}
    }
    create_entity_obj = CreateEntitySchema(**create_entity_req)
    print("\n创建实体请求示例:", create_entity_obj.json(indent=2, ensure_ascii=False))

    # 关系示例
    relationship_data = {
        "source_uri": "http://example.com/entity/herb/Ginseng",
        "predicate_uri": "http://example.com/ontology/tcm#hasEffect",
        "target_uri": "http://example.com/entity/effect/TonifyQi"
    }
    relationship_obj = RelationshipSchema(**relationship_data)
    print("\n关系示例:", relationship_obj.json(indent=2, ensure_ascii=False))

    # 批量插入三元组示例
    bulk_req_data = {
        "triples": [
            {"subject": "http://example.com/s1", "predicate": "http://example.com/p1", "object_val": "http://example.com/o1"},
            {"subject": "http://example.com/s1", "predicate": "http://example.com/p2", "object_val": "这是一个字面量值"},
            {"subject": "http://example.com/s2", "predicate": "http://example.com/p3", "object_val": 123},
        ],
        "graph_uri": "http://example.com/myGraph"
    }
    bulk_req_obj = BulkInsertTriplesRequest(**bulk_req_data)
    print("\n批量插入请求示例:", bulk_req_obj.json(indent=2, ensure_ascii=False))
