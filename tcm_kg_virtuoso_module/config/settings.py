# tcm_kg_virtuoso_module/config/settings.py
import os
from functools import lru_cache
from pydantic_settings import BaseSettings # 使用 pydantic-settings
from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager

# 默认本体URI和前缀定义 (与之前步骤一致)
# Default ontology URI and prefix definitions (consistent with previous steps)
ONTOLOGY_BASE_URI = "http://tcm.example.org/ontology/"
ENTITY_BASE_URI = "http://tcm.example.org/resource/"
SOURCE_BASE_URI = "http://tcm.example.org/source/"
DEFAULT_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "dcterms": "http://purl.org/dc/terms/",
    "tcm-onto": ONTOLOGY_BASE_URI,
    # 根据需要添加更多前缀
    # Add more prefixes as needed
}

class Settings(BaseSettings):
    virtuoso_host: str = "localhost"
    virtuoso_port: int = 1111
    virtuoso_user: str = "dba"
    virtuoso_password: str = "dba"
    virtuoso_graph_uri: str = "http://tcm.example.org/graph" # 默认图URI示例


    class Config:
        env_file = ".env" # 允许从 .env 文件加载配置
                          # Allow loading configuration from .env file
        env_file_encoding = 'utf-8'

@lru_cache() # 缓存设置实例以提高性能
             # Cache settings instance for performance
def get_settings() -> Settings:
    return Settings()

# 用于FastAPI依赖注入的连接管理器获取函数
# Connection manager getter function for FastAPI dependency injection
def get_virtuoso_connection_manager(): # Removed -> VirtuosoConnectionManager type hint for generator
    current_settings = get_settings() # get_settings is cached
    manager = VirtuosoConnectionManager(
        host=current_settings.virtuoso_host,
        port=current_settings.virtuoso_port,
        user=current_settings.virtuoso_user,
        password=current_settings.virtuoso_password,
        default_graph_uri=current_settings.virtuoso_graph_uri
    )
    try:
        print("正在尝试连接依赖关系中的管理器。。。") # Diagnostic print
        manager.connect() # Connect here
        print("管理器以依赖关系连接。") # Diagnostic print
        yield manager     # Yield the connected manager
    except Exception as e:
        print(f"Error during connection in dependency: {e}") # Diagnostic print for connection error
        # Optionally, re-raise or handle as appropriate for your app's error strategy
        raise
    finally:
        print("Disconnecting manager in dependency finally block...") # Diagnostic print
        manager.disconnect() # Disconnect when the request is done
        print("Manager disconnected in dependency.") # Diagnostic print
# 如果需要，可以在这里添加更多的配置，比如JWT密钥、数据库URL等
# More configurations can be added here if needed, such as JWT keys, database URLs, etc.
