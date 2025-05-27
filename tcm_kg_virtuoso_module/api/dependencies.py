# tcm_kg_virtuoso_module/api/dependencies.py
# 定义 FastAPI 依赖项，用于提供服务实例

from functools import lru_cache # 用于缓存服务实例，提高效率

from tcm_kg_virtuoso_module.core import config as app_config
from tcm_kg_virtuoso_module.graph_db.virtuoso_connector import VirtuosoConnector
from tcm_kg_virtuoso_module.services.entity_service import EntityService
from tcm_kg_virtuoso_module.services.relationship_service import RelationshipService
from tcm_kg_virtuoso_module.services.import_export_service import ImportExportService
# from tcm_kg_virtuoso_module.services.ontology_service import OntologyService # 本体服务暂时可选

# 使用 lru_cache 来确保在单个应用生命周期/请求处理中，服务实例只被创建一次。
# 注意: 对于有状态的服务或需要每个请求不同实例的场景，不应使用 lru_cache。
# 对于这里的服务，它们通常是无状态的（状态由数据库管理），可以共享。

@lru_cache()
def get_app_config():
    """获取应用配置模块的依赖项。"""
    return app_config

@lru_cache()
def get_virtuoso_connector(config = get_app_config()) -> VirtuosoConnector:
    """
    获取 VirtuosoConnector 的依赖项实例。
    使用配置模块中的参数进行初始化。
    """
    # print("DEBUG: Creating VirtuosoConnector instance") # 用于调试实例化次数
    return VirtuosoConnector(
        endpoint_url=config.VIRTUOSO_URL,
        username=config.VIRTUOSO_USER,
        password=config.VIRTUOSO_PASSWORD,
        default_graph=config.DEFAULT_GRAPH_URI
    )

@lru_cache()
def get_entity_service(
    connector: VirtuosoConnector = get_virtuoso_connector(), # FastAPI 会自动解析此依赖
    config = get_app_config()
) -> EntityService:
    """获取 EntityService 的依赖项实例。"""
    # print("DEBUG: Creating EntityService instance")
    return EntityService(connector=connector, config_module=config)

@lru_cache()
def get_relationship_service(
    connector: VirtuosoConnector = get_virtuoso_connector(),
    config = get_app_config()
) -> RelationshipService:
    """获取 RelationshipService 的依赖项实例。"""
    # print("DEBUG: Creating RelationshipService instance")
    return RelationshipService(connector=connector, config_module=config)

@lru_cache()
def get_import_export_service(
    connector: VirtuosoConnector = get_virtuoso_connector(),
    entity_service: EntityService = get_entity_service(),
    relationship_service: RelationshipService = get_relationship_service(),
    config = get_app_config()
) -> ImportExportService:
    """获取 ImportExportService 的依赖项实例。"""
    # print("DEBUG: Creating ImportExportService instance")
    return ImportExportService(
        connector=connector,
        entity_service=entity_service,
        relationship_service=relationship_service,
        config_module=config
    )

# 如果 OntologyService 被激活并使用:
# @lru_cache()
# def get_ontology_service(
#     connector: VirtuosoConnector = Depends(get_virtuoso_connector),
#     config = Depends(get_app_config)
# ) -> OntologyService:
#     """获取 OntologyService 的依赖项实例。"""
#     return OntologyService(connector=connector, config_module=config)

# 使用示例 (在 FastAPI 路由函数中):
# from fastapi import APIRouter, Depends
# from .dependencies import get_entity_service
# from ..services.entity_service import EntityService
#
# router = APIRouter()
#
# @router.get("/some-entity/{uri}")
# async def read_entity(uri: str, service: EntityService = Depends(get_entity_service)):
#     entity = service.get_entity_by_uri(uri)
#     # ...
#     return entity
