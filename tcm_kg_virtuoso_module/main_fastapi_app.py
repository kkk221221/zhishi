# tcm_kg_virtuoso_module/main_fastapi_app.py
# 主 FastAPI 应用入口文件

from fastapi import FastAPI

# 导入API路由模块
# 使用相对导入路径，假设main_fastapi_app.py在tcm_kg_virtuoso_module包内
from .api.v1 import entity_routes, relationship_routes, bulk_routes
# from .api import dependencies # dependencies.py 主要被路由模块使用，主应用文件通常不需要直接导入它

app = FastAPI(
    title="中医知识图谱API (TCM Knowledge Graph API)",
    description="用于操作和查询中医知识图谱的API接口。",
    version="0.1.0",
    # 可以添加更多OpenAPI元数据
    # contact={"name": "开发者", "email": "dev@example.com"},
    # license_info={"name": "Apache 2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0.html"},
    openapi_tags=[ # 可选：为标签添加描述信息，在文档中显示
        {"name": "根 (Root)", "description": "API的基本信息和健康检查。"},
        {"name": "实体管理 (Entities)", "description": "管理知识图谱中的实体，如草药、症状、方剂等。"},
        {"name": "关系管理 (Relationships)", "description": "管理实体间的关系。"},
        {"name": "批量操作 (Bulk Operations)", "description": "执行批量数据导入等操作。"},
    ]
)

@app.on_event("startup")
async def startup_event():
    # 应用启动时可以执行的初始化操作
    # 例如，检查数据库连接，加载缓存等
    # from .api.dependencies import get_virtuoso_connector # 示例
    # connector = get_virtuoso_connector()
    # print("应用启动：尝试连接到 Virtuoso...")
    # test_query_success = connector.execute_select_query("ASK { ?s ?p ?o }") is not None
    # if test_query_success:
    #     print("Virtuoso 连接测试成功。")
    # else:
    #     print("警告: Virtuoso 连接测试失败或未配置。API可能无法正常工作。")
    print("FastAPI 应用已启动。")
    print(f"API文档请访问: http://localhost:8000/docs 或 http://localhost:8000/redoc")


@app.get("/", summary="API根节点", description="返回API的基本信息。", tags=["根 (Root)"])
async def read_root():
    return {
        "message": "欢迎使用中医知识图谱API! Welcome to the TCM Knowledge Graph API!",
        "version": app.version,
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

# 注册V1版本的API路由
# 所有 /api/v1/* 的路由将由这些子路由器处理
common_api_prefix = "/api" # 可以将所有API路由统一到一个基础路径下，例如 /api
app.include_router(entity_routes.router, prefix=common_api_prefix)
app.include_router(relationship_routes.router, prefix=common_api_prefix)
app.include_router(bulk_routes.router, prefix=common_api_prefix)

# 如果有其他版本的API，例如 /v2/，可以类似地添加:
# from .api.v2 import some_other_routes
# app.include_router(some_other_routes.router, prefix="/api/v2", tags=["V2 Operations"])


if __name__ == "__main__":
    import uvicorn
    # 正确的启动方式通常是在项目根目录运行: 
    # uvicorn tcm_kg_virtuoso_module.main_fastapi_app:app --reload --host 0.0.0.0 --port 8000
    # 或者如果此文件被移到项目根目录并改名为 main_kg_app.py:
    # uvicorn main_kg_app:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run("tcm_kg_virtuoso_module.main_fastapi_app:app", host="0.0.0.0", port=8000, reload=True)
