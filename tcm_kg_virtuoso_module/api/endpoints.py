# tcm_kg_virtuoso_module/api/endpoints.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import HttpUrl
from typing import List, Any, Dict, Union # Union 已添加

from tcm_kg_virtuoso_module.api.request_schemas import EntityCreate, Attribute as AttributeSchema
from tcm_kg_virtuoso_module.core.graph_operations import add_entity
from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager
from tcm_kg_virtuoso_module.config.settings import get_virtuoso_connection_manager # 假设此函数后续会定义

# 为这些端点定义一个路由器
router = APIRouter()

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
    "/api/v1/tcm/graph/entities", # 保持路径为英文，符合API路径命名常规
    status_code=status.HTTP_201_CREATED,
    summary="在知识图谱中创建一个新实体", # 摘要使用中文
    response_description="新创建实体的URI。", # 响应描述使用中文
)
async def create_entity_endpoint(
    entity_data: EntityCreate,
    conn_manager: VirtuosoConnectionManager = Depends(get_virtuoso_connection_manager),
):
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
