# tcm_kg_virtuoso_module/api/v1/relationship_routes.py
from fastapi import APIRouter, Depends, HTTPException, Path, Body, Query, status
from typing import List, Optional

from ..schemas import (
    RelationshipSchema,
    CreateRelationshipSchema,
    DeleteRelationshipSchema, # Using CreateRelationshipSchema for delete body for now, or a specific one
    ResponseMessage
)
from ...services.relationship_service import RelationshipService
from ..dependencies import get_relationship_service
from ...models.tcm_relationship import TCMRelationship # For creating TCMRelationship instances

router = APIRouter(
    prefix="/v1/relationships", # 此路由组的前缀
    tags=["关系管理 (Relationships)"], # 在OpenAPI文档中分组的标签
    responses={404: {"description": "未找到 (Not found)"}}
)

# --- 关系操作路由 ---

@router.post(
    "/",
    response_model=RelationshipSchema,
    status_code=status.HTTP_201_CREATED,
    summary="创建新关系",
    description="在两个实体之间或一个实体与一个字面量之间创建一个新的关系 (三元组)。"
)
async def create_relationship(
    create_request: CreateRelationshipSchema = Body(..., description="创建关系所需的数据"),
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """
    创建新关系 Endpoint。
    - **create_request**: 包含源URI、谓词URI和目标URI/字面量。
    - **relationship_service**: 依赖注入的关系服务实例。
    """
    try:
        # 将 Pydantic schema 转换为服务层期望的 TCMRelationship 模型
        # 注意: Pydantic 的 AnyUrl 类型在验证后仍然是字符串，可以直接使用
        relationship_to_create = TCMRelationship(
            source_uri=str(create_request.source_uri),
            predicate_uri=str(create_request.predicate_uri),
            target_uri=str(create_request.target_uri), # target_uri可以是URI或字面量字符串
            properties=create_request.properties # 虽然服务层目前不处理，但模型允许传递
        )
        
        success = relationship_service.add_relationship(relationship_to_create)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="添加关系到数据库失败。"
            )
        
        # 返回创建后的关系数据
        # Pydantic模型可以直接从请求数据创建，因为服务层add_relationship不修改它
        return RelationshipSchema(**create_request.dict())

    except ValueError as ve: # 来自服务层或URI校验的错误
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # 记录更详细的错误日志 e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建关系时发生内部错误: {type(e).__name__} {e}")


@router.get(
    "/for-entity/{entity_uri:path}",
    response_model=List[RelationshipSchema],
    summary="获取实体的关系",
    description="根据提供的实体URI，检索其所有相关的入向和/或出向关系。"
)
async def get_relationships_for_entity_uri(
    entity_uri: str = Path(..., description="要查询其关系的实体的完整URI", example="http://example.com/entity/tcm/Herb001"),
    direction: str = Query("all", description="查询方向: 'outgoing' (出向), 'incoming' (入向), 'all' (全部)", pattern="^(outgoing|incoming|all)$"),
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """
    获取实体关系 Endpoint。
    - **entity_uri**: 实体的URI。
    - **direction**: 查询方向 ("outgoing", "incoming", "all")。
    - **relationship_service**: 关系服务实例。
    """
    try:
        relationships_models = relationship_service.get_relationships_for_entity(entity_uri, direction)
    except ValueError as ve: # URI格式或direction参数无效
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    
    if not relationships_models:
        # 返回空列表是正常的，不一定是404，除非明确要求URI必须存在
        return [] 
        # 如果需要确保 entity_uri 本身存在，则需要先调用 entity_service.get_entity_by_uri
        # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到与实体 <{entity_uri}> 相关的关系，或实体不存在。")
    
    # 将 TCMRelationship 模型列表转换为 RelationshipSchema 列表用于响应
    return [RelationshipSchema.from_orm(rel) for rel in relationships_models]


@router.post(
    "/delete", # 使用POST是因为DELETE通常不建议有请求体，但删除特定三元组需要多个标识符
    response_model=ResponseMessage,
    summary="删除特定关系",
    description="根据提供的源URI、谓词URI和目标URI/字面量，删除一个特定的关系三元组。"
)
async def delete_specific_relationship(
    delete_request: DeleteRelationshipSchema = Body(..., description="要删除的关系的标识信息"),
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """
    删除特定关系 Endpoint。
    - **delete_request**: 包含要删除关系的源、谓词和目标。
    - **relationship_service**: 关系服务实例。
    """
    try:
        success = relationship_service.delete_relationship(
            source_uri=str(delete_request.source_uri),
            predicate_uri=str(delete_request.predicate_uri),
            target_uri=str(delete_request.target_uri) # 目标可以是URI或字面量
        )
    except ValueError as ve: # URI格式无效等
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    if not success:
        # 类似于实体删除，这里的失败可能是因为关系不存在或数据库错误
        # 为了简单，统一返回操作失败
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # 或者 404 如果能确定是关系不存在
            detail="删除关系操作失败或指定的关系未找到。"
        )
    
    return ResponseMessage(message="关系已成功删除或原本不存在。", success=True)
