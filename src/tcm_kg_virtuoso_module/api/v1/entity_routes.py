# tcm_kg_virtuoso_module/api/v1/entity_routes.py
from fastapi import APIRouter, Depends, HTTPException, Path, Body, status
from typing import List, Optional

from ..schemas import (
    EntitySchema, 
    CreateEntitySchema, 
    ResponseMessage,
    # UpdateEntitySchema # 暂不使用 UpdateEntitySchema
)
from ...services.entity_service import EntityService
from ..dependencies import get_entity_service, get_app_config # 引入依赖项获取函数
from ...core.config import NAMESPACES # 直接从core.config导入，或通过get_app_config依赖
from ...utils.uri_utils import generate_entity_uri as generate_uri_from_util # 重命名以避免与变量冲突
from ...models.tcm_entity import TCMEntity # Import TCMEntity for creating instance

router = APIRouter(
    prefix="/v1/entities", # 此路由组的前缀
    tags=["实体管理 (Entities)"], # 在OpenAPI文档中分组的标签
    responses={404: {"description": "未找到 (Not found)"}} # 可以为整个路由组定义通用响应
)

# --- 实体操作路由 ---

@router.post(
    "/",
    response_model=EntitySchema,
    status_code=status.HTTP_201_CREATED,
    summary="创建新实体",
    description="根据提供的类型和属性创建一个新的知识图谱实体。URI将由服务端根据`uri_suffix`和`entity_type_key_for_uri`生成。"
)
async def create_entity(
    create_request: CreateEntitySchema = Body(..., description="创建实体所需的数据"),
    entity_service: EntityService = Depends(get_entity_service),
    # app_config_instance = Depends(get_app_config) # 如果需要直接访问配置
):
    """
    创建新实体 Endpoint。
    - **create_request**: 包含实体类型、属性以及可选的URI后缀和用于生成URI的类型键。
    - **entity_service**: 依赖注入的实体服务实例。
    """
    try:
        if not create_request.uri_suffix:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="创建实体时必须提供 uri_suffix (用于生成URI的名称或ID部分)。"
            )

        generated_uri = generate_uri_from_util(
            entity_type_key=create_request.entity_type_key_for_uri,
            entity_name_or_id=create_request.uri_suffix
        )

        # Convert Pydantic AnyUrl types to strings for TCMEntity dataclass
        entity_types_str = [str(et) for et in create_request.entity_types]
        properties_str_keys = {str(k): v for k, v in create_request.properties.items()}

        entity_to_create = TCMEntity(
            uri=generated_uri,
            entity_types=entity_types_str,
            properties=properties_str_keys
        )
        
        success = entity_service.add_entity(entity_to_create)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="添加实体到数据库失败。"
            )
        
        created_entity_data = entity_service.get_entity_by_uri(generated_uri)
        if not created_entity_data:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="实体已创建但无法立即检索。"
            )
        return EntitySchema.from_orm(created_entity_data)

    except ValueError as ve: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建实体时发生内部错误: {type(e).__name__} {e}")


@router.get(
    "/{entity_uri:path}", 
    response_model=EntitySchema,
    summary="获取实体信息",
    description="根据提供的完整URI检索单个实体的详细信息，包括其类型和所有属性。"
)
async def get_entity(
    entity_uri: str = Path(..., description="要检索的实体的完整URI (例如: http://example.com/entity/tcm/Herb001 或 tcm_entity:Herb001)", example="http://example.com/entity/tcm/Herb001"),
    entity_service: EntityService = Depends(get_entity_service)
):
    try:
        entity = entity_service.get_entity_by_uri(entity_uri) 
    except ValueError as ve: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的实体URI格式: {ve}")
    
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"实体 <{entity_uri}> 未找到。")
    
    return EntitySchema.from_orm(entity)


@router.delete(
    "/{entity_uri:path}",
    response_model=ResponseMessage,
    summary="删除实体",
    description="根据提供的完整URI删除一个实体及其所有直接属性。可选的级联删除参数可以控制是否删除与该实体相关的其他关系。"
)
async def delete_entity_by_uri(
    entity_uri: str = Path(..., description="要删除的实体的完整URI", example="http://example.com/entity/tcm/Herb001"),
    cascade: bool = False, 
    entity_service: EntityService = Depends(get_entity_service)
):
    try:
        success = entity_service.delete_entity(entity_uri, cascade=cascade)
    except ValueError as ve: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"删除实体 <{entity_uri}> 操作失败。"
        )

    return ResponseMessage(message=f"实体 <{entity_uri}> {'及相关数据' if cascade else ''} 已成功删除或不存在。", success=True)


# 备注: PUT (更新) /entities/{uri} 路由已根据计划暂缓实现。
# @router.put("/{entity_uri:path}", response_model=EntitySchema, summary="更新实体")
# async def update_entity_by_uri(
#     entity_uri: str = Path(..., description="要更新的实体的URI"),
#     update_data: UpdateEntitySchema = Body(..., description="要更新的实体数据"),
#     entity_service: EntityService = Depends(get_entity_service)
# ):
#     raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="更新实体功能尚未实现。")
