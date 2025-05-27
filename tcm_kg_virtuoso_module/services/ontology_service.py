# tcm_kg_virtuoso_module/services/ontology_service.py
from typing import Optional, List, Dict, Any
from tcm_kg_virtuoso_module.graph_db.virtuoso_connector import VirtuosoConnector
from tcm_kg_virtuoso_module.graph_db import sparql_builder
from tcm_kg_virtuoso_module.core import config as app_config
# from tcm_kg_virtuoso_module.models.tcm_entity import TCMEntity # 可能用于定义类的元数据

class OntologyService:
    """
    (可选) 本体服务类
    
    用于通过代码管理和维护知识图谱的本体（Schema/Ontology）。
    例如，定义新的实体类别 (classes)、属性 (properties) 及其层级关系、定义域、值域等。
    
    这对于需要动态演化本体，或者希望通过代码来确保本体一致性的项目非常有用。
    如果本体相对固定并通过外部工具（如 Protege）管理，则此服务可能不是必需的。
    """

    def __init__(self, connector: VirtuosoConnector, config_module=app_config):
        """
        初始化本体服务。

        参数:
            connector (VirtuosoConnector): 用于与Virtuoso数据库交互的连接器实例。
            config_module (module): 项目的配置模块。
        """
        if not isinstance(connector, VirtuosoConnector):
            raise TypeError("传入的 connector 不是 VirtuosoConnector 类型")
        self.connector = connector
        self.config = config_module
        self.default_graph = self.config.DEFAULT_GRAPH_URI # 本体定义通常也在特定图中
        
        # 常用RDF/RDFS/OWL词汇的URI，方便使用
        self.RDF_TYPE = self.config.NAMESPACES.get("rdf", "") + "type"
        self.RDFS_CLASS = self.config.NAMESPACES.get("rdfs", "") + "Class"
        self.RDFS_SUBCLASSOF = self.config.NAMESPACES.get("rdfs", "") + "subClassOf"
        self.RDFS_LABEL = self.config.NAMESPACES.get("rdfs", "") + "label"
        self.RDFS_COMMENT = self.config.NAMESPACES.get("rdfs", "") + "comment"
        self.RDFS_DOMAIN = self.config.NAMESPACES.get("rdfs", "") + "domain"
        self.RDFS_RANGE = self.config.NAMESPACES.get("rdfs", "") + "range"
        self.OWL_CLASS = self.config.NAMESPACES.get("owl", "") + "Class" # OWL Class 与 RDFS Class 等价
        self.OWL_OBJECT_PROPERTY = self.config.NAMESPACES.get("owl", "") + "ObjectProperty"
        self.OWL_DATATYPE_PROPERTY = self.config.NAMESPACES.get("owl", "") + "DatatypeProperty"
        # ... 其他可能用到的OWL词汇


    def add_class(self, 
                  class_uri: str, 
                  label: Optional[str] = None, 
                  comment: Optional[str] = None,
                  parent_class_uri: Optional[str] = None,
                  graph_uri: Optional[str] = None) -> bool:
        """
        向图谱中添加一个新的类别 (Class) 定义。

        参数:
            class_uri (str): 新类别的URI。
            label (Optional[str]): 类别的标签 (rdfs:label)。
            comment (Optional[str]): 类别的注释 (rdfs:comment)。
            parent_class_uri (Optional[str]): 父类别的URI (rdfs:subClassOf)。
            graph_uri (Optional[str]): 操作的目标图URI，默认为配置中的DEFAULT_GRAPH_URI。
        
        返回:
            bool: 操作是否成功。
        """
        target_graph = graph_uri if graph_uri else self.default_graph
        triples = []
        triples.append((class_uri, self.RDF_TYPE, self.OWL_CLASS)) # 或 self.RDFS_CLASS
        
        if label:
            triples.append((class_uri, self.RDFS_LABEL, label)) # 假设标签是字符串字面量
        if comment:
            triples.append((class_uri, self.RDFS_COMMENT, comment))
        if parent_class_uri:
            triples.append((class_uri, self.RDFS_SUBCLASSOF, parent_class_uri))
            
        if not triples:
            return True # 没有实际操作

        query = sparql_builder.build_insert_triples_sparql(target_graph, triples)
        return self.connector.execute_update_query(query)

    def add_property(self,
                     property_uri: str,
                     property_type: str, # 例如 self.OWL_OBJECT_PROPERTY 或 self.OWL_DATATYPE_PROPERTY
                     label: Optional[str] = None,
                     comment: Optional[str] = None,
                     domain_uri: Optional[str] = None, # rdfs:domain
                     range_uri: Optional[str] = None,  # rdfs:range
                     graph_uri: Optional[str] = None) -> bool:
        """
        向图谱中添加一个新的属性 (Property) 定义。

        参数:
            property_uri (str): 新属性的URI。
            property_type (str): 属性的类型 (例如 owl:ObjectProperty, owl:DatatypeProperty)。
            label (Optional[str]): 属性的标签。
            comment (Optional[str]): 属性的注释。
            domain_uri (Optional[str]): 属性的定义域 (rdfs:domain)。
            range_uri (Optional[str]): 属性的值域 (rdfs:range)。
            graph_uri (Optional[str]): 操作的目标图URI。

        返回:
            bool: 操作是否成功。
        """
        target_graph = graph_uri if graph_uri else self.default_graph
        triples = []
        triples.append((property_uri, self.RDF_TYPE, property_type))
        
        if label:
            triples.append((property_uri, self.RDFS_LABEL, label))
        if comment:
            triples.append((property_uri, self.RDFS_COMMENT, comment))
        if domain_uri:
            triples.append((property_uri, self.RDFS_DOMAIN, domain_uri))
        if range_uri:
            triples.append((property_uri, self.RDFS_RANGE, range_uri))

        if not triples:
            return True

        query = sparql_builder.build_insert_triples_sparql(target_graph, triples)
        return self.connector.execute_update_query(query)

    # 未来可能添加更多方法，例如:
    # - get_class_hierarchy(class_uri)
    # - get_property_details(property_uri)
    # - remove_class(class_uri)
    # - remove_property(property_uri)

if __name__ == '__main__':
    print("OntologyService 演示 (当前为占位符和初步实现)")
    # 此演示需要连接到真实的Virtuoso实例，并已正确配置 .env
    
    try:
        connector = VirtuosoConnector()
        ontology_service = OntologyService(connector)
        print("OntologyService 初始化成功。")

        # 定义一些示例URI (通常会从配置文件或模型中获取)
        tcm_ont_ns = app_config.NAMESPACES.get("tcm_ont", "http://example.com/ontology/tcm#")
        
        new_class_uri = tcm_ont_ns + "TestHerbalFormula"
        parent_class_uri = tcm_ont_ns + "BaseFormula" # 假设父类已存在或也要定义
        
        new_prop_uri = tcm_ont_ns + "hasChiefIngredient"
        domain_class_uri = new_class_uri
        range_class_uri = tcm_ont_ns + "Herb" # 假设Herb类已存在

        # 1. 添加父类 (如果不存在)
        print(f"\n尝试添加父类: {parent_class_uri}")
        success_parent = ontology_service.add_class(
            class_uri=parent_class_uri,
            label="基础方剂",
            comment="所有方剂的基础类别"
        )
        print(f"添加父类结果: {'成功' if success_parent else '失败'}")
        
        # 2. 添加新类别
        print(f"\n尝试添加新类别: {new_class_uri}")
        success_class = ontology_service.add_class(
            class_uri=new_class_uri,
            label="测试草药方剂",
            comment="一个用于演示的草药方剂类别。",
            parent_class_uri=parent_class_uri
        )
        print(f"添加新类别结果: {'成功' if success_class else '失败'}")

        # 3. 添加新属性
        print(f"\n尝试添加新属性: {new_prop_uri}")
        success_prop = ontology_service.add_property(
            property_uri=new_prop_uri,
            property_type=ontology_service.OWL_OBJECT_PROPERTY, # 对象属性，因为值域是另一个类
            label="具有主要成分",
            comment="指向方剂中的主要草药成分。",
            domain_uri=domain_class_uri,
            range_uri=range_class_uri
        )
        print(f"添加新属性结果: {'成功' if success_prop else '失败'}")
        
        # 注意: 此处的演示代码会实际修改数据库。
        # 在真实的测试或应用中，应谨慎操作，或使用专门的测试图谱。
        # 清理操作 (可选，但建议在测试后进行):
        # ontology_service.connector.execute_update_query(f"CLEAR GRAPH <{ontology_service.default_graph}>") # 非常危险!
        # 或者更精细地删除添加的三元组。

    except Exception as e:
        print(f"OntologyService 演示过程中发生错误: {e}")
        print("请确保 Virtuoso 服务正在运行，并且 .env 文件已正确配置。")
