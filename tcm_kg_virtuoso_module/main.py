# tcm_kg_virtuoso_module/main.py
from fastapi import FastAPI
from tcm_kg_virtuoso_module.api import endpoints as api_endpoints # api.endpoints模块的导入
from tcm_kg_virtuoso_module.config.settings import get_settings # 导入设置，虽然此处不直接使用，但通常好的实践是初始化它或让其可访问
                                                                # Import settings, although not directly used here, it's often good practice to initialize or make it accessible

# 初始化 FastAPI 应用实例
# Initialize FastAPI application instance
app = FastAPI(
    title="TCM Knowledge Graph API", # API 标题
    description="用于与中医药知识图谱交互的API。", # API 描述
    version="0.1.0", # API 版本
)

# 在应用启动和关闭时可以添加事件处理器 (可选)
# Event handlers can be added for application startup and shutdown (optional)
@app.on_event("startup")
async def startup_event():
    # 例如：初始化数据库连接池、加载机器学习模型等
    print("应用程序启动...") # Chinese message
    get_settings() # 确保设置在启动时被加载和缓存
    print("Registered routes:")
    for route in app.routes:
        print(f"Path: {route.path}, Name: {route.name}, Methods: {getattr(route, 'methods', None)}")

@app.on_event("shutdown")
async def shutdown_event():
    # 例如：关闭数据库连接、清理资源等
    # For example: close database connections, clean up resources, etc.
    print("应用程序关闭...") # Chinese message

# 包含 API 路由
# Include API router
# 建议为版本化的API使用前缀
# It's recommended to use a prefix for versioned APIs
app.include_router(api_endpoints.router, prefix="/api/v1/tcm/graph") # 将端点路由器包含进来，并设置统一前缀

# 可以添加一个根路径端点用于健康检查或基本信息
# A root path endpoint can be added for health checks or basic information
@app.get("/", summary="根路径", description="API的根路径，可用于健康检查。") # Chinese summary/description
async def read_root():
    return {"message": "欢迎使用中医药知识图谱API"} # Chinese message

# 如果直接运行此文件 (例如使用 uvicorn main:app --reload)，这将是入口点
# If this file is run directly (e.g., using uvicorn main:app --reload), this will be the entry point
if __name__ == "__main__":
    import uvicorn
    # 此处的 host 和 port 仅用于直接运行main.py进行开发时
    # The host and port here are only for direct execution of main.py during development
    # 生产环境中通常由Uvicorn/Gunicorn等ASGI服务器在命令行指定
    # In a production environment, it is usually specified by an ASGI server like Uvicorn/Gunicorn on the command line
    uvicorn.run(app, host="0.0.0.0", port=8000)
