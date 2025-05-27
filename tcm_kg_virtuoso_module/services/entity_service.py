# tcm_kg_virtuoso_module/services/entity_service.py
from typing import Optional, List, Dict, Any, Tuple
from tcm_kg_virtuoso_module.models.tcm_entity import TCMEntity
from tcm_kg_virtuoso_module.graph_db.virtuoso_connector import VirtuosoConnector
from tcm_kg_virtuoso_module.graph_db import sparql_builder
from tcm_kg_virtuoso_module.core import config as app_config # 使用 app_config 避免与方法参数名冲突
from tcm_kg_virtuoso_module.utils.uri_utils import validate_uri_format, generate_entity_uri # 假设未来可能用到 generate_entity_uri

class EntityService:
    """
    实体服务类
    封装对知识图谱中实体的核心操作逻辑，例如添加、查询、删除实体。
    """

    def __init__(self, connector: VirtuosoConnector, config_module=app_config):
        """
        初始化实体服务。

        参数:
            connector (VirtuosoConnector): 用于与Virtuoso数据库交互的连接器实例。
            config_module (module): 项目的配置模块 (默认为 tcm_kg_virtuoso_module.core.config)。
        """
        if not isinstance(connector, VirtuosoConnector):
            raise TypeError("传入的 connector 不是 VirtuosoConnector 类型")
        self.connector = connector
        self.config = config_module
        self.default_graph = self.config.DEFAULT_GRAPH_URI
        self.rdf_type_uri = self.config.NAMESPACES.get("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#") + "type"


    def add_entity(self, entity: TCMEntity) -> bool:
        """
        向知识图谱中添加一个新的实体及其属性和类型。

        参数:
            entity (TCMEntity): 要添加的实体对象，包含URI、类型和属性。

        返回:
            bool: 如果实体成功添加则返回True，否则返回False。
        """
        if not isinstance(entity, TCMEntity):
            raise TypeError("输入参数 entity 必须是 TCMEntity 类型。")
        if not entity.uri or not validate_uri_format(entity.uri):
            # print(f"错误: 实体URI '{entity.uri}' 无效。") # 实际应用中可能使用日志
            raise ValueError(f"实体URI '{entity.uri}' 无效。")

        triples_to_insert = []

        # 1. 添加实体类型声明 (rdf:type)
        if not entity.entity_types:
            # print(f"警告: 实体 {entity.uri} 没有指定 entity_types。") # 实际应用中可能使用日志
            # 根据业务规则，可以考虑是否添加一个默认类型，或者直接报错
            # raise ValueError(f"实体 {entity.uri} 必须至少有一个类型。")
            pass # 允许无类型实体，或在其他地方处理默认类型

        for entity_type_uri in entity.entity_types:
            if not validate_uri_format(entity_type_uri):
                # print(f"错误: 实体类型URI '{entity_type_uri}' 无效。")
                raise ValueError(f"为实体 {entity.uri} 提供的类型URI '{entity_type_uri}' 无效。")
            triples_to_insert.append((entity.uri, self.rdf_type_uri, entity_type_uri))

        # 2. 添加实体属性
        for prop_uri, values in entity.properties.items():
            if not validate_uri_format(prop_uri):
                # print(f"错误: 属性URI '{prop_uri}' 无效。")
                raise ValueError(f"为实体 {entity.uri} 提供的属性URI '{prop_uri}' 无效。")
            
            value_list = values if isinstance(values, list) else [values]
            for value in value_list:
                # 注意: _format_term 会自动判断对象是URI还是字面量。
                # 如果属性值本身是一个复杂对象（例如另一个TCMEntity或字典代表的匿名节点），
                # 则需要更复杂的逻辑来处理，这里假设属性值是简单的URI字符串或字面量。
                if isinstance(value, dict) and 'uri' in value: # 假设字典代表一个关联实体URI
                     triples_to_insert.append((entity.uri, prop_uri, value['uri']))
                elif isinstance(value, TCMEntity): # 如果属性值是另一个TCMEntity实例
                     triples_to_insert.append((entity.uri, prop_uri, value.uri))
                else: # URI字符串或字面量
                    triples_to_insert.append((entity.uri, prop_uri, value))
        
        if not triples_to_insert:
            # print(f"信息: 实体 {entity.uri} 没有可插入的三元组数据 (无类型且无属性)。")
            return True # 或者根据业务逻辑返回False或抛出异常

        insert_query = sparql_builder.build_insert_triples_sparql(
            graph_uri=self.default_graph,
            triples_list=triples_to_insert
        )
        
        return self.connector.execute_update_query(insert_query)

    def get_entity_by_uri(self, entity_uri: str) -> Optional[TCMEntity]:
        """
        根据URI从知识图谱中检索实体及其所有属性和类型。

        参数:
            entity_uri (str): 要检索的实体的URI。

        返回:
            Optional[TCMEntity]: 如果找到实体，则返回TCMEntity对象，否则返回None。
        """
        if not entity_uri or not validate_uri_format(entity_uri):
            # print(f"错误: 实体URI '{entity_uri}' 无效。")
            raise ValueError(f"要检索的实体URI '{entity_uri}' 无效。")

        query = sparql_builder.build_select_entity_properties_sparql(
            graph_uri=self.default_graph,
            entity_uri=entity_uri
        )
        
        results = self.connector.execute_select_query(query)
        
        if results is None or not results.get("results", {}).get("bindings"):
            return None

        properties: Dict[str, Any] = {}
        entity_types: List[str] = []

        for binding in results["results"]["bindings"]:
            predicate = binding["predicate"]["value"]
            obj = binding["object"] # 对象本身，包含类型和值

            value: Any
            if obj["type"] == "uri":
                value = obj["value"]
            elif obj["type"] == "literal" or obj["type"] == "typed-literal":
                value = obj["value"]
                # 对于类型化字面量，可以尝试转换 Python 类型
                if "datatype" in obj:
                    datatype = obj["datatype"]
                    if datatype == self.config.NAMESPACES.get("xsd", "") + "integer":
                        try: value = int(value)
                        except ValueError: pass
                    elif datatype == self.config.NAMESPACES.get("xsd", "") + "float" or                          datatype == self.config.NAMESPACES.get("xsd", "") + "double" or                          datatype == self.config.NAMESPACES.get("xsd", "") + "decimal":
                        try: value = float(value)
                        except ValueError: pass
                    elif datatype == self.config.NAMESPACES.get("xsd", "") + "boolean":
                        value = value.lower() == "true"
                    # 可以根据需要添加更多xsd类型的处理
            else: # 例如 bnode (匿名节点)，这里简单处理为字符串值
                value = obj["value"]


            if predicate == self.rdf_type_uri:
                if value not in entity_types: # 确保类型不重复
                    entity_types.append(str(value))
            else:
                if predicate in properties:
                    current_prop_value = properties[predicate]
                    if isinstance(current_prop_value, list):
                        if value not in current_prop_value: # 避免重复值
                             current_prop_value.append(value)
                    elif current_prop_value != value: # 如果原先不是列表且新值不同
                        properties[predicate] = [current_prop_value, value]
                else:
                    properties[predicate] = value
        
        if not entity_types and not properties: # 如果查询有结果但解析后为空，说明可能URI存在但无类型和属性
            # 这取决于图谱数据，可能是一个仅被引用的URI
            # print(f"警告: 实体 {entity_uri} 存在但未找到类型或属性信息。")
            # 返回一个只有URI的实体对象，或根据业务逻辑返回None
            return TCMEntity(uri=entity_uri)


        return TCMEntity(uri=entity_uri, entity_types=entity_types, properties=properties)

    def delete_entity(self, entity_uri: str, cascade: bool = False) -> bool:
        """
        从知识图谱中删除一个实体及其所有直接属性。
        注意：此方法目前主要删除以该实体为主题 (subject) 的三元组。
        级联删除 (cascade=True) 意味着删除与该实体相关的所有关系 (即该实体作为客体 object 的三元组)。
        级联删除的完整实现较为复杂，此处暂时简化。

        参数:
            entity_uri (str): 要删除的实体的URI。
            cascade (bool): 是否执行级联删除。默认为False。
                           当前简化实现：如果为True，会额外尝试删除该实体作为object的三元组。

        返回:
            bool: 如果删除操作成功（至少尝试执行了查询）则返回True，否则返回False。
                  注意: SPARQL DELETE通常不返回实际删除了多少三元组。
        """
        if not entity_uri or not validate_uri_format(entity_uri):
            # print(f"错误: 实体URI '{entity_uri}' 无效。")
            raise ValueError(f"要删除的实体URI '{entity_uri}' 无效。")

        success = True

        # 1. 删除以 entity_uri 为主语 (subject) 的所有三元组
        # 这会删除实体的所有属性和类型声明
        # 使用 SPARQL UPDATE DELETE WHERE { <entity_uri> ?p ?o }
        # sparql_builder 可以增加一个 build_delete_where_subject_sparql(graph_uri, subject_uri)
        # 为简化，暂时手动构建或使用 build_delete_triples_sparql (但这需要知道所有 p, o)
        # 更通用的删除语句：
        delete_subject_query = f"""
{sparql_builder.SPARQL_PREFIXES}
DELETE WHERE {{
  GRAPH <{self.default_graph}> {{
    <{entity_uri}> ?predicate ?object .
  }}
}}
"""
        if not self.connector.execute_update_query(delete_subject_query):
            success = False # 记录一次失败

        # 2. (简化级联) 如果 cascade 为 True，删除以 entity_uri 为宾语 (object) 的所有三元组
        if cascade:
            delete_object_query = f"""
{sparql_builder.SPARQL_PREFIXES}
DELETE WHERE {{
  GRAPH <{self.default_graph}> {{
    ?subject ?predicate <{entity_uri}> .
  }}
}}
"""
            if not self.connector.execute_update_query(delete_object_query):
                success = False # 记录一次失败
        
        return success

    # update_entity_properties 方法可以后续添加，其实现可能涉及:
    # 1. 查询现有属性
    # 2. 计算需要删除的属性 (旧的有，新的没有)
    # 3. 计算需要添加的属性 (新的有，旧的没有或值不同)
    # 4. 构建 SPARQL DELETE 和 INSERT 语句，可能在同一个事务中执行 (如果连接器支持)


if __name__ == '__main__':
    # 此部分仅为基本演示，实际测试需要 mock VirtuosoConnector 或连接到真实数据库
    print("EntityService 演示 (需要配置并连接到Virtuoso)")
    
    # 假设已配置好 .env 文件
    try:
        connector_instance = VirtuosoConnector() # 使用默认配置
        entity_service = EntityService(connector=connector_instance)
        print("EntityService 初始化成功。")

        # 示例实体数据
        test_uri = generate_entity_uri("tcm_entity", "TestHerb001_ServiceDemo") # 使用uri_utils生成
        test_entity = TCMEntity(
            uri=test_uri,
            entity_types=[app_config.NAMESPACES["tcm_ont"] + "Herb", app_config.NAMESPACES["owl"] + "NamedIndividual"],
            properties={
                app_config.NAMESPACES["rdfs"] + "label": "测试草药_服务",
                app_config.NAMESPACES["tcm_prop"] + "hasTaste": "甘",
                app_config.NAMESPACES["tcm_prop"] + "sourceBook": {"uri": app_config.NAMESPACES["tcm_entity"] + "Book1"}
            }
        )

        # 1. 添加实体
        print(f"\n尝试添加实体: {test_entity.uri}")
        add_success = entity_service.add_entity(test_entity)
        print(f"添加实体结果: {'成功' if add_success else '失败'}")

        if add_success:
            # 2. 获取实体
            print(f"\n尝试获取实体: {test_entity.uri}")
            retrieved_entity = entity_service.get_entity_by_uri(test_entity.uri)
            if retrieved_entity:
                print(f"获取到的实体: URI='{retrieved_entity.uri}', Types={retrieved_entity.entity_types}")
                for prop, val in retrieved_entity.properties.items():
                    print(f"  属性: {prop} = {val}")
            else:
                print(f"未能获取到实体 {test_entity.uri}")

            # 3. 删除实体
            print(f"\n尝试删除实体: {test_entity.uri}")
            delete_success = entity_service.delete_entity(test_entity.uri, cascade=True) # 测试级联删除
            print(f"删除实体结果: {'成功' if delete_success else '失败'}")

            # 验证删除
            print(f"\n再次尝试获取已删除的实体: {test_entity.uri}")
            deleted_entity_check = entity_service.get_entity_by_uri(test_entity.uri)
            if deleted_entity_check:
                print(f"错误: 实体 {test_entity.uri} 似乎未被成功删除。")
            else:
                print(f"实体 {test_entity.uri} 已成功删除或未找到。")

    except Exception as e:
        print(f"EntityService 演示过程中发生错误: {e}")
        print("请确保 Virtuoso 服务正在运行，并且 .env 文件已正确配置。")
        print("同时，相关 Python 库 (SPARQLWrapper, python-dotenv) 需要已安装。")
