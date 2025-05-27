# tcm_kg_virtuoso_module/services/relationship_service.py
from typing import Optional, List, Tuple, Dict, Any
from tcm_kg_virtuoso_module.models.tcm_relationship import TCMRelationship
from tcm_kg_virtuoso_module.graph_db.virtuoso_connector import VirtuosoConnector
from tcm_kg_virtuoso_module.graph_db import sparql_builder
from tcm_kg_virtuoso_module.core import config as app_config
from tcm_kg_virtuoso_module.utils.uri_utils import validate_uri_format

class RelationshipService:
    """
    关系服务类
    封装对知识图谱中实体间关系的核心操作逻辑。
    """

    def __init__(self, connector: VirtuosoConnector, config_module=app_config):
        """
        初始化关系服务。

        参数:
            connector (VirtuosoConnector): 用于与Virtuoso数据库交互的连接器实例。
            config_module (module): 项目的配置模块。
        """
        if not isinstance(connector, VirtuosoConnector):
            raise TypeError("传入的 connector 不是 VirtuosoConnector 类型")
        self.connector = connector
        self.config = config_module
        self.default_graph = self.config.DEFAULT_GRAPH_URI

    def add_relationship(self, relationship: TCMRelationship) -> bool:
        """
        向知识图谱中添加一个新的关系。
        注意：关系自身的属性 (TCMRelationship.properties) 的存储依赖于图数据库对RDF*或关系具体化的支持。
        此基本实现仅插入核心的三元组。如果需要存储关系属性，需要扩展此方法和相应的SPARQL构建。

        参数:
            relationship (TCMRelationship): 要添加的关系对象。

        返回:
            bool: 如果关系成功添加则返回True，否则返回False。
        """
        if not isinstance(relationship, TCMRelationship):
            raise TypeError("输入参数 relationship 必须是 TCMRelationship 类型。")
        
        for uri, name in [
            (relationship.source_uri, "源实体URI"),
            (relationship.predicate_uri, "谓词URI"),
            (relationship.target_uri, "目标URI") # 目标可以是URI或字面量，但TCMRelationship将其视为URI字符串
        ]:
            if not uri or not validate_uri_format(uri): # validate_uri_format 需要能处理字面量和URI
                raise ValueError(f"关系中的 '{name}' ({uri}) 无效。")

        # 基本实现：只插入关系三元组本身
        triples_to_insert = [(
            relationship.source_uri,
            relationship.predicate_uri,
            relationship.target_uri # sparql_builder._format_term 会处理它是URI还是字面量
        )]
        
        # TODO: 如果需要支持关系属性 (relationship.properties)，需要在这里添加逻辑：
        # 1. 将关系具体化 (reification): 创建一个新的URI代表此关系实例。
        #    例如: relation_instance_uri = generate_entity_uri("tcm_rel", f"{hash(relationship)}")
        # 2. 添加三元组声明此关系实例的类型 (e.g., rdf:type rdf:Statement)。
        # 3. 添加三元组连接源、谓词、目标到此关系实例 (e.g., rdf:subject, rdf:predicate, rdf:object)。
        # 4. 将 relationship.properties 中的每个属性作为此关系实例的属性添加。
        # 这会显著增加三元组的数量和查询的复杂性。目前版本将忽略 relationship.properties。
        if relationship.properties:
            print(f"警告: TCMRelationship.properties 不为空，但当前 add_relationship 实现未处理关系属性的存储。")


        insert_query = sparql_builder.build_insert_triples_sparql(
            graph_uri=self.default_graph,
            triples_list=triples_to_insert
        )
        
        return self.connector.execute_update_query(insert_query)

    def get_relationships_for_entity(self, entity_uri: str, direction: str = "all") -> List[TCMRelationship]:
        """
        检索与指定实体相关的所有关系。

        参数:
            entity_uri (str): 实体的URI。
            direction (str): 查询方向。
                             "outgoing" - 查询以此实体为主语 (source) 的关系。
                             "incoming" - 查询以此实体为宾语 (target) 的关系。
                             "all"      - 查询上述两种关系。 默认为 "all"。

        返回:
            List[TCMRelationship]: 关系对象列表。如果未找到则返回空列表。
        """
        if not entity_uri or not validate_uri_format(entity_uri):
            raise ValueError(f"要查询关系的实体URI '{entity_uri}' 无效。")

        allowed_directions = ["outgoing", "incoming", "all"]
        if direction.lower() not in allowed_directions:
            raise ValueError(f"参数 'direction' 的值必须是 {allowed_directions} 之一。")

        query_parts = []
        entity_uri_formatted = sparql_builder._format_term(entity_uri, is_uri=True)

        if direction.lower() in ["outgoing", "all"]:
            query_parts.append(f"  {{ {entity_uri_formatted} ?p_out ?o_out . BIND({entity_uri_formatted} AS ?s_out) }}")
        
        if direction.lower() in ["incoming", "all"]:
            query_parts.append(f"  {{ ?s_in ?p_in {entity_uri_formatted} . BIND({entity_uri_formatted} AS ?o_in) }}")
        
        union_query_body = "\n  UNION\n".join(query_parts)

        # 统一变量名 s, p, o
        # 对于 outgoing: s = entity_uri, p = p_out, o = o_out
        # 对于 incoming: s = s_in, p = p_in, o = entity_uri
        # 我们需要查询并绑定 s, p, o 三个变量
        
        sparql_query = f"""
{sparql_builder.SPARQL_PREFIXES}

SELECT DISTINCT ?s ?p ?o
WHERE {{
  GRAPH <{self.default_graph}> {{
    {union_query_body}
    # 统一变量绑定
    OPTIONAL {{ ?s_out ?p_out ?o_out . BIND(?s_out AS ?s) BIND(?p_out AS ?p) BIND(?o_out AS ?o) }}
    OPTIONAL {{ ?s_in ?p_in ?o_in . BIND(?s_in AS ?s) BIND(?p_in AS ?p) BIND(?o_in AS ?o) }}
    # 确保只选择相关的三元组
    FILTER(BOUND(?s) && BOUND(?p) && BOUND(?o))
  }}
}}
"""
        # 上述查询逻辑可以通过更精简的方式构建，这里是为了清晰展示两个方向的合并
        # 一个更简洁的SELECT部分可以是：
        # SELECT DISTINCT ?subject ?predicate ?object
        # WHERE {
        #   GRAPH <{self.default_graph}> {
        #     { BIND({entity_uri_formatted} as ?subject) . ?subject ?predicate ?object . } # Outgoing
        #     UNION
        #     { BIND({entity_uri_formatted} as ?object) . ?subject ?predicate ?object . }  # Incoming
        #   }
        #   # 根据direction进行FILTER
        # }
        #
        # 根据direction调整查询：
        select_subject = "?s"
        select_predicate = "?p"
        select_object = "?o"
        
        where_clauses = []
        if direction.lower() in ["outgoing", "all"]:
            where_clauses.append(f"    {{ {entity_uri_formatted} {select_predicate} {select_object} . BIND({entity_uri_formatted} as {select_subject}) }}")
        if direction.lower() in ["incoming", "all"]:
            where_clauses.append(f"    {{ {select_subject} {select_predicate} {entity_uri_formatted} . BIND({entity_uri_formatted} as {select_object}) }}")

        final_sparql_query = f"""
{sparql_builder.SPARQL_PREFIXES}
SELECT DISTINCT {select_subject} {select_predicate} {select_object}
WHERE {{
  GRAPH <{self.default_graph}> {{
    {' UNION '.join(where_clauses)}
  }}
}}
"""

        results = self.connector.execute_select_query(final_sparql_query)
        relationships: List[TCMRelationship] = []

        if results and results.get("results", {}).get("bindings"):
            for binding in results["results"]["bindings"]:
                try:
                    s = binding[select_subject.lstrip("?")]["value"]
                    p = binding[select_predicate.lstrip("?")]["value"]
                    obj_binding = binding[select_object.lstrip("?")]
                    
                    # 对象可能是URI或字面量
                    o = obj_binding["value"]
                    # if obj_binding["type"] == "literal" or obj_binding["type"] == "typed-literal":
                    #   o = sparql_builder._format_term(o, is_uri=False) # 确保字面量被正确引用 (如果需要)
                    # else: # uri or bnode
                    #   o = sparql_builder._format_term(o, is_uri=True) # 确保URI被正确引用 (如果需要)
                    # TCMRelationship 的 target_uri 期望是一个URI字符串或代表字面量的字符串
                    # sparql_builder._format_term 内部会处理，这里直接用值

                    relationships.append(TCMRelationship(source_uri=s, predicate_uri=p, target_uri=o))
                except KeyError as e:
                    print(f"解析关系结果时出错: 缺少键 {e}。绑定: {binding}")
                    continue
        return relationships

    def delete_relationship(self, source_uri: str, predicate_uri: str, target_uri: str) -> bool:
        """
        从知识图谱中删除一个特定的关系 (三元组)。

        参数:
            source_uri (str): 源实体的URI。
            predicate_uri (str): 谓词的URI。
            target_uri (str): 目标实体或字面量的URI/字符串。

        返回:
            bool: 如果删除操作成功提交则返回True，否则返回False。
        """
        for uri, name in [(source_uri, "源实体URI"), (predicate_uri, "谓词URI"), (target_uri, "目标URI/字面量")]:
            if not uri: # validate_uri_format 可能对某些形式的字面量返回False，所以这里只检查空
                 raise ValueError(f"删除关系时 '{name}' ({uri}) 不能为空。")
            # if not validate_uri_format(uri): # 如果target是字面量，validate_uri_format可能不适用
            #     raise ValueError(f"删除关系时 '{name}' ({uri}) 格式无效。")


        # target_uri 可能是字面量，sparql_builder._format_term 在构建查询时会处理
        triples_to_delete = [(source_uri, predicate_uri, target_uri)]
        
        delete_query = sparql_builder.build_delete_triples_sparql(
            graph_uri=self.default_graph,
            triples_list=triples_to_delete
        )
        
        return self.connector.execute_update_query(delete_query)


if __name__ == '__main__':
    # 此部分仅为基本演示，实际测试需要 mock VirtuosoConnector 或连接到真实数据库
    print("RelationshipService 演示 (需要配置并连接到Virtuoso)")

    try:
        connector_instance = VirtuosoConnector()
        rel_service = RelationshipService(connector=connector_instance)
        # 依赖 EntityService 示例中的实体
        entity_service_module = __import__('tcm_kg_virtuoso_module.services.entity_service', fromlist=['EntityService'])
        EntityService = entity_service_module.EntityService
        # Need to import TCMEntity for the __main__ block
        from tcm_kg_virtuoso_module.models.tcm_entity import TCMEntity
        entity_service = EntityService(connector=connector_instance)


        print("RelationshipService 初始化成功。")

        # 准备测试实体 (如果不存在则添加)
        base_uri = app_config.NAMESPACES["tcm_entity"]
        herb_uri = base_uri + "TestHerb_RelDemo"
        effect_uri = base_uri + "TestEffect_RelDemo"
        taste_uri = base_uri + "SweetTaste_RelDemo" # 假设这是一个实体代表味

        for uri, types, props in [
            (herb_uri, [app_config.NAMESPACES["tcm_ont"] + "Herb"], {app_config.NAMESPACES["rdfs"] + "label": "测试草药_关系演示"}),
            (effect_uri, [app_config.NAMESPACES["tcm_ont"] + "Effect"], {app_config.NAMESPACES["rdfs"] + "label": "测试功效_补气"}),
            (taste_uri, [app_config.NAMESPACES["tcm_ont"] + "Taste"], {app_config.NAMESPACES["rdfs"] + "label": "甘味"})
        ]:
            if not entity_service.get_entity_by_uri(uri):
                print(f"添加测试实体: {uri}")
                entity_service.add_entity(TCMEntity(uri=uri, entity_types=types, properties=props))


        # 1. 添加关系
        print(f"\n尝试添加关系: {herb_uri} -> hasEffect -> {effect_uri}")
        rel1 = TCMRelationship(source_uri=herb_uri, predicate_uri=app_config.NAMESPACES["tcm_prop"]+"hasEffect", target_uri=effect_uri)
        add_rel_success1 = rel_service.add_relationship(rel1)
        print(f"添加关系1结果: {'成功' if add_rel_success1 else '失败'}")

        # 添加一个目标为字面量的关系 (例如，如果一个属性用关系表示)
        # 为了演示，我们用一个描述性的属性关系
        predicate_has_description = app_config.NAMESPACES["tcm_prop"] + "hasDescription"
        description_literal = "这是一个关于测试草药的描述。" # 字面量
        print(f"\n尝试添加关系 (目标为字面量): {herb_uri} -> hasDescription -> '{description_literal}'")
        rel2 = TCMRelationship(source_uri=herb_uri, predicate_uri=predicate_has_description, target_uri=description_literal)
        add_rel_success2 = rel_service.add_relationship(rel2)
        print(f"添加关系2结果: {'成功' if add_rel_success2 else '失败'}")


        if add_rel_success1:
            # 2. 获取与实体相关的关系
            print(f"\n尝试获取与实体 {herb_uri}相关的 'outgoing' 关系:")
            outgoing_rels = rel_service.get_relationships_for_entity(herb_uri, direction="outgoing")
            if outgoing_rels:
                for r in outgoing_rels:
                    print(f"  - {r.source_uri} --[{r.predicate_uri}]--> {r.target_uri}")
            else:
                print(f"  未找到与 {herb_uri} 相关的 'outgoing' 关系。")

            print(f"\n尝试获取与实体 {effect_uri} 相关的 'incoming' 关系:")
            incoming_rels = rel_service.get_relationships_for_entity(effect_uri, direction="incoming")
            if incoming_rels:
                for r in incoming_rels:
                    print(f"  - {r.source_uri} --[{r.predicate_uri}]--> {r.target_uri}")
            else:
                print(f"  未找到与 {effect_uri} 相关的 'incoming' 关系。")


        # 3. 删除关系
        if add_rel_success1:
            print(f"\n尝试删除关系: {herb_uri} -> hasEffect -> {effect_uri}")
            del_rel_success = rel_service.delete_relationship(
                source_uri=herb_uri, 
                predicate_uri=app_config.NAMESPACES["tcm_prop"]+"hasEffect", 
                target_uri=effect_uri
            )
            print(f"删除关系结果: {'成功' if del_rel_success else '失败'}")

            # 验证删除
            print(f"\n再次获取与实体 {herb_uri}相关的 'outgoing' 关系 (验证删除):")
            rels_after_delete = rel_service.get_relationships_for_entity(herb_uri, direction="outgoing")
            found_deleted_rel = False
            for r in rels_after_delete:
                if r.predicate_uri == app_config.NAMESPACES["tcm_prop"]+"hasEffect" and r.target_uri == effect_uri:
                    found_deleted_rel = True
                    break
            if found_deleted_rel:
                 print(f"  错误: 关系 {herb_uri} -> {effect_uri} 似乎未被成功删除。")
            else:
                 print(f"  关系 {herb_uri} -> {effect_uri} 已成功删除或未找到。")

        # 清理演示中添加的字面量关系
        if add_rel_success2:
            rel_service.delete_relationship(herb_uri, predicate_has_description, description_literal)
            print(f"演示用字面量关系已清理。")
            
        # 清理测试实体
        print("\n清理测试实体...")
        entity_service.delete_entity(herb_uri, cascade=True)
        entity_service.delete_entity(effect_uri, cascade=True)
        entity_service.delete_entity(taste_uri, cascade=True)
        print("测试实体清理完毕。")


    except Exception as e:
        print(f"RelationshipService 演示过程中发生错误: {e}")
        print("请确保 Virtuoso 服务正在运行，并且 .env 文件已正确配置。")
