# tcm_kg_virtuoso_module/api/endpoints.py
from fastapi import APIRouter, Depends, HTTPException, status, Path
from pydantic import HttpUrl
from typing import List, Any, Dict, Union, Optional # Union 已添加, Optional 新增
from urllib.parse import unquote

from tcm_kg_virtuoso_module.api.request_schemas import (
    EntityCreate, 
    Attribute as AttributeSchema, 
    RelationshipCreate,
    EntityUpdate # 新增导入
)
from tcm_kg_virtuoso_module.core.graph_operations import add_entity, add_relationship, update_entity # update_entity 新增导入
from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager
from tcm_kg_virtuoso_module.config.settings import get_virtuoso_connection_manager # 假设此函数后续会定义

# 为这些端点定义一个路由器
router = APIRouter()

# 辅助函数：转换 EntityUpdate Pydantic 模型中的属性值
# Helper function: Transform attribute values in EntityUpdate Pydantic model
def _transform_update_attribute_value(value: Any) -> Any:
    """
    转换 EntityUpdate 模型中属性的 'value' 字段。
    如果值为 HttpUrl，则转换为字符串。
    其他类型按原样传递，核心层将处理字面量的具体格式化。
    """
    if isinstance(value, HttpUrl):
        return str(value)
    # 对于其他类型 (str, int, bool, List[str], List[HttpUrl] 等),
    # 核心层的 format_literal 或 format_uri 会处理。
    # 如果是列表，也直接传递，核心层应能处理。
    if isinstance(value, list):
        return [_transform_update_attribute_value(item) for item in value]
    return value

def transform_attribute_value(value: Any) -> Union[str, List[str]]:
    """将Pydantic模型中的属性值转换为add_entity所期望的格式。"""
    if isinstance(value, HttpUrl):
        return str(value)
    # 如果值已经是字符串列表或单个字符串，则格式正确。
    # add_entity 及后续的 prepare_entity_sparql_insert 可以处理 List[str] 或 str。
    # 我们需要确保如果它是一个列表，其元素是字符串。
    if isinstance(value, list):
        return [str(item) for item in value]
    return str(value) # 默认为字符串转换

@router.post(
    "/entities", # 保持路径为英文，符合API路径命名常规

    status_code=status.HTTP_201_CREATED,
    summary="在知识图谱中创建一个新实体", # 摘要使用中文
    response_description="新创建实体的URI。", # 响应描述使用中文
)

async def create_entity_endpoint(
    entity_data: EntityCreate,
    conn_manager: VirtuosoConnectionManager = Depends(get_virtuoso_connection_manager),
):
    print("--- create_entity_endpoint CALLED ---")
    """
    用于在知识图谱中创建新实体的端点。
    它使用 `EntityCreate` 模式进行请求体验证，并调用
    `tcm_kg_virtuoso_module.core.graph_operations` 中的 `add_entity` 函数。
    """
    try:
        # 将 EntityCreate 属性转换为 add_entity 所期望的格式
        attributes_list_for_core = []
        for attr_schema in entity_data.attributes:
            attributes_list_for_core.append({
                "property": attr_schema.property,
                "value": transform_attribute_value(attr_schema.value),
            })

        # 将 EntityCreate.source 转换为 source_details 字典
        # 这些键必须与 core.source_manager.create_source_metadata 的参数匹配
        source_details_for_core = {
            "citation": entity_data.source.citation,
            "original_text": entity_data.source.originalText, # schema中的originalText对应这里的original_text
            "document_identifier": entity_data.source.documentIdentifier,
            # --- EntityCreate.source 中缺失参数的默认值 ---
            "source_type": "APIDataCreation", # 示例默认值
            "source_section": entity_data.type, # 示例：使用实体类型作为章节
            "source_subsection": entity_data.label, # 示例：使用实体标签作为子章节
            # 此端点默认不提供 *uri_args
        }
        
        # 准备 add_entity 的主 entity_data 字典
        core_entity_data = {
            "entity_type_name": entity_data.type,
            "entity_label": entity_data.label,
            "attributes_list": attributes_list_for_core,
            "source_details": source_details_for_core,
            "entity_id_args": None,  # 目前不从此基本API收集这些信息
        }

        new_entity_uri = add_entity(entity_data=core_entity_data, conn_manager=conn_manager)
        
        # 返回新创建实体的URI
        # 如果需要更多细节，后续可以增强响应模型。
        return {"entity_uri": new_entity_uri}

    except ValueError as ve:
        # 来自 add_entity 的 ValueError (例如，缺失键，类型错误) 应为 400
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # 捕获实体创建过程中的其他意外错误
        # 在实际应用中应在此处记录异常
        print(f"实体创建过程中发生意外错误: {e}") # 用于调试
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建实体时发生意外错误。"
        )

@router.post(
    "/relationships",
    status_code=status.HTTP_201_CREATED,
    summary="在知识图谱中添加一个新的关系",
    response_description="确认关系已添加的消息。",
)
async def create_relationship_endpoint(
    relationship_data: RelationshipCreate,
    conn_manager: VirtuosoConnectionManager = Depends(get_virtuoso_connection_manager),
):
    """
    用于在知识图谱中的实体之间添加新关系的端点。
    它使用 `RelationshipCreate` 模式进行请求体验证，并调用
    `tcm_kg_virtuoso_module.core.graph_operations` 中的 `add_relationship` 函数。
    """
    try:
        # 准备 add_relationship 的 source_details 字典
        # 这些键必须与 core.source_manager.create_source_metadata 的参数匹配
        source_details_for_core = {
            "citation": relationship_data.source.citation,
            "original_text": relationship_data.source.originalText,
            "document_identifier": relationship_data.source.documentIdentifier,
            # --- RelationshipCreate.source 中缺失参数的默认值 ---
            "source_type": "APIRelationshipCreation", # 示例默认值
            "source_section": "Relationship", # 示例：固定值
            "source_subsection": relationship_data.predicate, # 示例：使用关系谓词作为子章节
            # 此端点默认不提供 *uri_args
        }

        # 准备 add_relationship 的主 core_relationship_data 字典
        core_relationship_data = {
            "subject_uri": str(relationship_data.subjectUri),
            "predicate": relationship_data.predicate,
            "object_uri": str(relationship_data.objectUri),
            "source_details": source_details_for_core,
        }

        add_relationship(relationship_data=core_relationship_data, conn_manager=conn_manager)
        
        return {"message": "Relationship added successfully"}

    except ValueError as ve:
        # 来自 add_relationship 的 ValueError (例如，缺失键，类型错误) 应为 400
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # 捕获关系创建过程中的其他意外错误
        # 在实际应用中应在此处记录异常
        print(f"关系创建过程中发生意外错误: {e}") # 用于调试
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建关系时发生意外错误。"
        )

@router.put(
    "/entities/{entity_uri_encoded}",
    status_code=status.HTTP_200_OK, # 根据指示，成功时返回200 OK并带消息
    summary="更新知识图谱中的现有实体",
    response_description="确认实体已更新的消息。",
)
async def update_entity_endpoint(
    entity_update_payload: EntityUpdate,
    entity_uri_encoded: str = Path(..., title="URL编码的实体URI", description="要更新的目标实体的完整URI，经过URL编码。"),
    conn_manager: VirtuosoConnectionManager = Depends(get_virtuoso_connection_manager),
):
    """
    用于更新知识图谱中现有实体属性的端点。
    它使用 `EntityUpdate` 模式进行请求体验证，并调用
    `tcm_kg_virtuoso_module.core.graph_operations` 中的 `update_entity` 函数。
    """
    try:
        entity_uri = unquote(entity_uri_encoded)

        # 1. 准备 attributes_to_add_or_update
        prepared_attrs_to_add_or_update: Optional[List[Dict[str, Any]]] = None
        if entity_update_payload.attributes_to_add_or_update:
            prepared_attrs_to_add_or_update = []
            for attr_model in entity_update_payload.attributes_to_add_or_update:
                processed_value = _transform_update_attribute_value(attr_model.value)
                prepared_attrs_to_add_or_update.append({
                    "property": attr_model.property,
                    "value": processed_value,
                    "datatype": attr_model.datatype
                })
        
        # 2. 准备 attributes_to_delete
        prepared_attrs_to_delete: Optional[List[Dict[str, Any]]] = None
        if entity_update_payload.attributes_to_delete:
            prepared_attrs_to_delete = []
            for attr_identifier_model in entity_update_payload.attributes_to_delete:
                processed_value = None
                if attr_identifier_model.value is not None: # value 是 Optional[Any]
                    processed_value = _transform_update_attribute_value(attr_identifier_model.value)
                
                prepared_attrs_to_delete.append({
                    "property": attr_identifier_model.property,
                    "value": processed_value, # 可能为 None
                    "datatype": attr_identifier_model.datatype
                })

        # 3. 准备 source_info
        # EntityUpdate.source 是必需的，所以 entity_update_payload.source 总会存在
        prepared_source_info: Dict[str, str] = {
            "citation": entity_update_payload.source.citation,
            "original_text": entity_update_payload.source.originalText,
            "document_identifier": entity_update_payload.source.documentIdentifier,
            # 默认值可以由核心层或数据格式化层根据操作类型（例如，修正vs替换）决定或进一步专门化。
            # 此处我们传递原始的API来源信息，核心层可以使用它来生成新的来源图或更新现有来源图的元数据。
            # 为了与 create_entity_endpoint 的 source_details 保持某种程度的一致性，可以添加一些默认值，
            # 但 update 操作的 source_type 可能不同。
            # 核心层的 update_entity 函数现在负责处理 source_info 的具体应用。
            # 例如，对于 supersede 操作，它将用于 create_source_metadata。
            # 对于 correction 操作，它将用于更新目标图的元数据（例如添加 tcm-onto:correctionNote）。
            # 根据 update_entity 函数的参数，它期望一个简单的字典。
        }
        # 可以在这里添加默认的 source_type 等，如果核心逻辑不处理这些：
        # prepared_source_info["source_type"] = "APIEntityUpdate" 
        # prepared_source_info["source_section"] = "EntityUpdate"
        # prepared_source_info["source_subsection"] = entity_uri # 或者其他合适的


        # 4. 准备 correction_details_info
        prepared_correction_details: Optional[Dict[str, Any]] = None
        if entity_update_payload.correction_details:
            prepared_correction_details = {
                "targetNamedGraphUri": str(entity_update_payload.correction_details.targetNamedGraphUri),
                "property_to_correct": entity_update_payload.correction_details.property_to_correct
            }
            
        # 5. 调用核心逻辑
        update_entity(
            entity_uri=entity_uri,
            attributes_to_add_or_update=prepared_attrs_to_add_or_update,
            attributes_to_delete=prepared_attrs_to_delete,
            source_info=prepared_source_info, # 始终传递，因为它是 EntityUpdate 中的必需字段
            correction_details_info=prepared_correction_details,
            conn_manager=conn_manager
        )
        
        return {"message": "实体已成功更新"}

    except ValueError as ve:
        # 来自 update_entity 的 ValueError (例如，数据不一致，缺失必要信息) 应为 400
        # 或来自 unquote, HttpUrl 转换等的潜在错误
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # 捕获实体更新过程中的其他意外错误
        # 在实际应用中应在此处记录异常
        print(f"实体更新过程中发生意外错误 (URI: {entity_uri_encoded}): {e}") # 用于调试
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新实体时发生意外错误。"
        )
