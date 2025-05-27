# tcm_kg_virtuoso_module/api/v1/bulk_routes.py
from fastapi import APIRouter, Depends, HTTPException, Body, status
from typing import List

from ..schemas import (
    BulkInsertTriplesRequest,
    ResponseMessage,
    TripleSchema # 虽然请求体是BulkInsertTriplesRequest，但其内部使用TripleSchema
)
from ...services.import_export_service import ImportExportService
from ..dependencies import get_import_export_service

router = APIRouter(
    prefix="/v1/bulk", # 此路由组的前缀
    tags=["批量操作 (Bulk Operations)"], # 在OpenAPI文档中分组的标签
    responses={500: {"description": "服务器内部错误 (Internal Server Error)"}}
)

# --- 批量操作路由 ---

@router.post(
    "/triples",
    response_model=ResponseMessage, # 或者一个更详细的响应，比如包含成功/失败数量
    status_code=status.HTTP_200_OK, # 批量操作部分成功也可能返回200，具体看业务定义
    summary="批量插入三元组",
    description="向指定的图或默认图中批量插入提供的三元组列表。"
)
async def bulk_insert_triples_endpoint(
    request_body: BulkInsertTriplesRequest = Body(..., description="包含三元组列表和可选图URI的请求数据"),
    import_export_service: ImportExportService = Depends(get_import_export_service)
):
    """
    批量插入三元组 Endpoint。
    - **request_body**: 包含三元组列表和可选的目标图URI。
    - **import_export_service**: 依赖注入的导入/导出服务实例。
    """
    try:
        # 将 Pydantic模型的 TripleSchema 列表转换为服务层期望的元组列表
        # object_val 可以是数字、布尔值等，服务层的 sparql_builder._format_term 会处理
        # TripleSchema 定义 object_val 为 Union[AnyUrl, str, int, float, bool]，所以可以直接用
        
        precise_triples_to_insert = [
            (str(t.subject), str(t.predicate), t.object_val) # 保持 object_val 的原始 Pydantic 验证后类型
            for t in request_body.triples
        ]


        success = import_export_service.bulk_insert_triples(
            triples=precise_triples_to_insert,
            graph_uri=str(request_body.graph_uri) if request_body.graph_uri else None
            # batch_size 可以由服务层默认处理，或在此处也作为参数接收
        )
        
        if not success:
            # 如果服务层能区分部分成功和完全失败，可以返回不同的状态码或消息
            # 例如，使用 status.HTTP_207_MULTI_STATUS
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # 或者根据具体错误调整
                detail="批量插入三元组操作未能完全成功。"
            )
        
        return ResponseMessage(
            message=f"成功处理 {len(precise_triples_to_insert)} 个三元组的批量插入请求。",
            success=True
        )

    except ValueError as ve: # 例如，如果 graph_uri 格式无效 (虽然Pydantic的AnyUrl会先捕获)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # 记录更详细的错误日志 e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"批量插入三元组时发生内部错误: {type(e).__name__} {e}")

# 备注:
# - `import_from_processed_data` 的对应端点已根据计划暂缓，因为其服务层方法是占位符。
# - 如果未来实现，它可能需要处理文件上传 (fastapi.UploadFile) 或服务器端文件路径。
#   例如:
#   @router.post("/import-processed-file", summary="从处理后的文件导入数据")
#   async def import_data_from_file(
#       data_type: str = Query(..., description="数据类型，如 'tcm_book_paragraphs'"),
#       file: UploadFile = File(..., description="要导入的数据文件"), # 或者 source_path: str
#       import_export_service: ImportExportService = Depends(get_import_export_service)
#   ):
#       # ... 调用服务层方法 ...
#       pass
