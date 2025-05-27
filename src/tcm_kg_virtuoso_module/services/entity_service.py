# tcm_kg_virtuoso_module/services/entity_service.py
from typing import Optional, List, Dict, Any, Tuple
from ..models.tcm_entity import TCMEntity
from ..graph_db.virtuoso_connector import VirtuosoConnector
from ..graph_db import sparql_builder
from ..core import config as app_config # 使用 app_config 避免与方法参数名冲突
from ..utils.uri_utils import validate_uri_format, generate_entity_uri # 假设未来可能用到 generate_entity_uri
# Import the new TypedDicts from their new location
from ..graph_db.sparql_types import SparqlQuerySolution, SparqlSelectResults, SparqlBinding, SparqlBindingValue
# Ensure Literal is imported if it's used elsewhere, or if type hints in this file still need it directly.
# For now, assuming it's primarily for the TypedDicts that were moved.
# The main typing imports (Optional, List, Dict, Any, Tuple) are at the top of the file.
from typing import Literal # Retain Literal if it's used for other type hints in this file, otherwise it's not strictly needed here.

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
            raise ValueError(f"要检索的实体URI '{entity_uri}' 无效。")

        query = sparql_builder.build_select_entity_properties_sparql(
            graph_uri=self.default_graph,
            entity_uri=entity_uri
        )
        
        # Add type hint for results_data
        results_data: Optional[SparqlQuerySolution] = self.connector.execute_select_query(query)
        
        # Use .get() for safer access and to help Pylance
        if results_data is None:
            return None
        
        sparql_results: Optional[SparqlSelectResults] = results_data.get("results")
        if sparql_results is None:
            # This could happen for ASK queries if they were mistakenly processed here,
            # or if the result format is unexpected.
            return None 
            
        bindings: List[SparqlBinding] = sparql_results.get("bindings", [])
        if not bindings:
            # URI might exist but have no properties/types listed (e.g. only referenced as an object)
            # Depending on desired behavior, one might return TCMEntity(uri=entity_uri) or None.
            # For now, returning None if no properties/types are found.
            # If an entity must exist if it has triples pointing to it, this check might change.
            # To check if an entity exists at all, an ASK query might be better first.
            # print(f"调试: 实体 <{entity_uri}> 未找到任何绑定 (类型或属性)。")
            return None


        properties: Dict[str, Any] = {}
        entity_types: List[str] = []

        for binding in bindings: # binding is now hinted as SparqlBinding
            predicate_binding_value: Optional[SparqlBindingValue] = binding.get("predicate")
            object_binding_value: Optional[SparqlBindingValue] = binding.get("object")

            if not predicate_binding_value or not object_binding_value:
                # print(f"警告: 在实体 <{entity_uri}> 的结果中发现不完整的绑定: {binding}") # 日志
                continue # Skip this malformed binding

            predicate: str = predicate_binding_value.get("value", "") # Default to empty string if "value" key is missing
            
            value_type: Optional[str] = object_binding_value.get("type")
            obj_value_str: str = object_binding_value.get("value", "") # Default to empty string

            processed_value: Any = obj_value_str # Default to the string value

            if value_type == "uri":
                processed_value = obj_value_str
            elif value_type == "literal" or value_type == "typed-literal":
                processed_value = obj_value_str # Keep as string initially
                datatype: Optional[str] = object_binding_value.get("datatype")
                if datatype:
                    # Attempt type conversion for known XSD types
                    xsd_ns = self.config.NAMESPACES.get("xsd", "http://www.w3.org/2001/XMLSchema#")
                    if datatype == xsd_ns + "integer":
                        try: processed_value = int(obj_value_str)
                        except ValueError: pass # Keep as string if conversion fails
                    elif datatype in [xsd_ns + "float", xsd_ns + "double", xsd_ns + "decimal"]:
                        try: processed_value = float(obj_value_str)
                        except ValueError: pass
                    elif datatype == xsd_ns + "boolean":
                        processed_value = obj_value_str.lower() == "true"
            # else: bnode or other types, keep as string value for now

            if predicate == self.rdf_type_uri:
                if str(processed_value) not in entity_types: # Ensure type URI is a string
                    entity_types.append(str(processed_value))
            else:
                current_prop_val = properties.get(predicate)
                if current_prop_val is not None:
                    if isinstance(current_prop_val, list):
                        if processed_value not in current_prop_val:
                            current_prop_val.append(processed_value)
                    elif current_prop_val != processed_value: # Property already exists, value is different, convert to list
                        properties[predicate] = [current_prop_val, processed_value]
                    # If value is the same, do nothing
                else: # New property
                    properties[predicate] = processed_value
        
        # If after processing all bindings, there are no types and no properties,
        # it implies the URI might exist but is "empty" or only referenced.
        # Behavior here depends on requirements: return an empty TCMEntity or None.
        # Current logic: if bindings were processed but resulted in no types/props, it's an empty entity.
        # If initial `bindings` list was empty, we returned None earlier.
        if not entity_types and not properties and bindings: 
             return TCMEntity(uri=entity_uri) # Entity exists but is "empty"
        elif not entity_types and not properties and not bindings: # Should have been caught by earlier check
             return None


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
