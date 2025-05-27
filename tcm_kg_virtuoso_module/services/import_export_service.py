# tcm_kg_virtuoso_module/services/import_export_service.py
from typing import List, Tuple, Optional, Any
from tcm_kg_virtuoso_module.graph_db.virtuoso_connector import VirtuosoConnector
from tcm_kg_virtuoso_module.services.entity_service import EntityService
from tcm_kg_virtuoso_module.services.relationship_service import RelationshipService
from tcm_kg_virtuoso_module.graph_db import sparql_builder
from tcm_kg_virtuoso_module.core import config as app_config
import os # 用于 import_from_processed_data 中的文件路径操作

class ImportExportService:
    """
    导入/导出服务类
    提供批量数据操作，例如批量插入三元组，以及从处理后的数据源导入数据到知识图谱。
    """

    def __init__(self, 
                 connector: VirtuosoConnector, 
                 entity_service: EntityService, 
                 relationship_service: RelationshipService, 
                 config_module=app_config):
        """
        初始化导入/导出服务。

        参数:
            connector (VirtuosoConnector): Virtuoso连接器实例。
            entity_service (EntityService): 实体服务实例。
            relationship_service (RelationshipService): 关系服务实例。
            config_module (module): 项目的配置模块。
        """
        if not isinstance(connector, VirtuosoConnector):
            raise TypeError("传入的 connector 不是 VirtuosoConnector 类型")
        if not isinstance(entity_service, EntityService):
            raise TypeError("传入的 entity_service 不是 EntityService 类型")
        if not isinstance(relationship_service, RelationshipService):
            raise TypeError("传入的 relationship_service 不是 RelationshipService 类型")
            
        self.connector = connector
        self.entity_service = entity_service
        self.relationship_service = relationship_service
        self.config = config_module
        self.default_graph = self.config.DEFAULT_GRAPH_URI

    def bulk_insert_triples(self, 
                            triples: List[Tuple[str, str, str]], 
                            graph_uri: Optional[str] = None, 
                            batch_size: int = 100) -> bool:
        """
        向指定的图批量插入三元组。

        参数:
            triples (List[Tuple[str, str, str]]): 要插入的三元组列表，每个三元组为 (subject, predicate, object)。
            graph_uri (Optional[str]): 目标图的URI。如果为None，则使用默认图URI。
            batch_size (int): 每批次插入的三元组数量。

        返回:
            bool: 如果所有批次都成功提交则返回True，否则返回False。
        """
        if graph_uri is None:
            graph_uri = self.default_graph
        
        if not graph_uri:
            raise ValueError("目标图URI (graph_uri) 不能为空。")

        if not triples:
            # print("信息: 没有提供三元组进行批量插入。") # 日志
            return True # 没有操作也算成功

        all_successful = True
        for i in range(0, len(triples), batch_size):
            batch = triples[i:i + batch_size]
            if not batch: # Should not happen with correct loop logic, but as a safeguard
                continue

            # print(f"信息: 正在插入批次 {i // batch_size + 1}，包含 {len(batch)} 个三元组到图 <{graph_uri}>。") # 日志
            
            insert_query = sparql_builder.build_insert_triples_sparql(
                graph_uri=graph_uri,
                triples_list=batch
            )
            
            if not self.connector.execute_update_query(insert_query):
                # print(f"错误: 批次 {i // batch_size + 1} 插入失败。") # 日志
                all_successful = False
                # 根据需求，可以选择在这里中断并返回False，或者继续尝试其他批次
                # break 
        
        return all_successful

    def import_from_processed_data(self, data_type: str, source_path: str):
        """
        从处理后的数据源导入数据到知识图谱。
        此方法是一个高级接口，其具体实现将依赖于 `data_type` 和 `source_path` 的结构。

        参数:
            data_type (str): 数据的类型，用于确定如何解析文件。
                             例如: "tcm_book_paragraphs", "clinical_case_json"。
            source_path (str): 数据源的路径 (可以是文件或目录)。

        预期行为 (需要后续详细实现):
        - 根据 `data_type` 选择合适的解析逻辑。
        - 遍历 `source_path` (如果是目录) 或读取文件。
        - 将解析出的内容转换为 `TCMEntity` 和 `TCMRelationship` 对象。
          例如:
            - 对于 "tcm_book_paragraphs":
                - 每个段落文件可以被视为一个文本实体或内容节点。
                - 文件名中的信息 (如书名、篇章、序号) 可以作为该实体的属性。
                - 可能需要定义段落之间的顺序关系或与篇章的从属关系。
            - 对于 "clinical_case_json":
                - JSON文件中的字段需要映射到知识图谱的实体和关系。
                - 例如，一个病例可能是一个实体，其诊断、症状、治疗方案等是关联的实体或属性。
        - 使用 `self.entity_service.add_entity` 和 `self.relationship_service.add_relationship`
          (或直接使用 `self.bulk_insert_triples` 如果能直接生成三元组) 将数据存入图谱。

        当前的实现只是一个占位符，说明了预期的功能。
        """
        print(f"信息: 调用 import_from_processed_data 方法。")
        print(f"  数据类型: {data_type}")
        print(f"  源路径: {source_path}")
        print("  注意: 此方法的具体数据解析和导入逻辑尚未实现。")

        # 伪代码/概念验证:
        # if data_type == "tcm_book_paragraphs":
        #     if os.path.isdir(source_path):
        #         for book_dir_name in os.listdir(source_path): # e.g., 黄帝内经_特性_黄帝
        #             book_dir_path = os.path.join(source_path, book_dir_name)
        #             if os.path.isdir(book_dir_path):
        #                 for filename in os.listdir(book_dir_path): # e.g., 黄帝内经_上古天真论篇第一_1.txt
        #                     file_path = os.path.join(book_dir_path, filename)
        #                     if os.path.isfile(file_path) and filename.endswith(".txt"):
        #                         # 解析文件名获取书名、篇章、序号
        #                         # parts = filename.removesuffix(".txt").split("_")
        #                         # book_title, chapter_title, paragraph_num = parts[0], parts[1], parts[2]
        #                         # 读取文件内容
        #                         # with open(file_path, 'r', encoding='utf-8') as f:
        #                         #     content = f.read()
        #                         # 创建实体和关系...
        #                         # paragraph_uri = self.entity_service.uri_utils.generate_entity_uri("tcm_doc", filename)
        #                         # self.entity_service.add_entity(TCMEntity(...))
        #                         pass
        # elif data_type == "clinical_case_json":
        #     # 解析JSON文件，映射字段...
        #     pass
        # else:
        #     print(f"错误: 未知的数据类型 '{data_type}'。")
        #     return False
        
        # return True # 假设操作完成 (占位符)
        raise NotImplementedError("import_from_processed_data 方法的具体实现尚未完成。")


if __name__ == '__main__':
    print("ImportExportService 演示 (需要配置并连接到Virtuoso)")

    # 引入TCMEntity和TCMRelationship用于可能的演示数据创建
    from tcm_kg_virtuoso_module.models.tcm_entity import TCMEntity
    from tcm_kg_virtuoso_module.models.tcm_relationship import TCMRelationship
    
    try:
        # 准备依赖项
        connector_inst = VirtuosoConnector()
        entity_serv = EntityService(connector=connector_inst)
        rel_serv = RelationshipService(connector=connector_inst)
        
        import_export_serv = ImportExportService(
            connector=connector_inst,
            entity_service=entity_serv,
            relationship_service=rel_serv
        )
        print("ImportExportService 初始化成功。")

        # 1. 演示 bulk_insert_triples
        print("\n--- 演示批量插入三元组 ---")
        test_graph_uri = app_config.DEFAULT_GRAPH_URI + "/TestBulkInsert" # 使用一个特定的测试图
        
        sample_triples = []
        base_subject_uri = app_config.NAMESPACES.get("tcm_entity", "http://example.com/entity/") + "BulkItem"
        rdfs_label = app_config.NAMESPACES.get("rdfs", "") + "label"
        rdf_type = app_config.NAMESPACES.get("rdf", "") + "type"
        owl_NamedIndividual = app_config.NAMESPACES.get("owl", "") + "NamedIndividual"

        for i in range(5): # 创建一些示例三元组
            s = f"{base_subject_uri}{i+1}"
            sample_triples.append((s, rdf_type, owl_NamedIndividual))
            sample_triples.append((s, rdfs_label, f"批量项目 {i+1}"))
            sample_triples.append((s, app_config.NAMESPACES.get("tcm_prop")+"hasValue", str(i*10)))

        print(f"准备插入 {len(sample_triples)} 个三元组到图 <{test_graph_uri}>")
        bulk_success = import_export_serv.bulk_insert_triples(
            triples=sample_triples, 
            graph_uri=test_graph_uri, 
            batch_size=3 # 小批量测试
        )
        print(f"批量插入结果: {'成功' if bulk_success else '失败'}")

        if bulk_success:
            # 简单验证 (实际验证需要查询图谱)
            print(f"验证: 可以通过SPARQL查询图 <{test_graph_uri}> 来确认数据是否已插入。")
            # 清理演示数据 (删除整个测试图 - 如果Virtuoso支持并且权限允许)
            # connector_inst.execute_update_query(f"CLEAR GRAPH <{test_graph_uri}>")
            # print(f"测试图 <{test_graph_uri}> 已尝试清理。")
            # 或者逐个删除 (更安全)
            del_triples_query = sparql_builder.build_delete_triples_sparql(test_graph_uri, sample_triples)
            if del_triples_query: # build_delete_triples_sparql returns "" if list is empty
                connector_inst.execute_update_query(del_triples_query)
                print(f"测试图 <{test_graph_uri}> 中的演示数据已尝试删除。")
            else:
                print(f"没有生成删除查询，可能sample_triples为空。")


        # 2. 演示 import_from_processed_data (会抛出 NotImplementedError)
        print("\n--- 演示从处理后数据导入 (预期 NotImplementedError) ---")
        try:
            # 创建一个临时的伪数据文件/目录结构用于演示路径参数
            # 在实际测试中，你可能需要创建真实的临时文件
            dummy_source_path = "./temp_processed_data_demo" 
            os.makedirs(dummy_source_path, exist_ok=True) # 创建临时目录
            if os.path.exists(dummy_source_path): # 确保目录创建成功
                with open(os.path.join(dummy_source_path, "dummy.txt"), "w") as f:
                    f.write("dummy content")

                import_export_serv.import_from_processed_data(
                    data_type="tcm_book_paragraphs",
                    source_path=dummy_source_path 
                )
            else:
                print(f"错误: 未能创建临时目录 {dummy_source_path}，跳过 import_from_processed_data 演示。")

        except NotImplementedError as e:
            print(f"捕获到预期的错误: {e}")
        except Exception as e: #捕获其他可能的错误，例如文件操作
            print(f"执行 import_from_processed_data 演示时发生意外错误: {e}")
        finally:
            # 清理临时文件和目录
            if os.path.exists(dummy_source_path):
                try:
                    for item in os.listdir(dummy_source_path):
                        item_path = os.path.join(dummy_source_path, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                    os.rmdir(dummy_source_path)
                    print(f"临时目录 {dummy_source_path} 已清理。")
                except Exception as e:
                    print(f"清理临时目录 {dummy_source_path} 时出错: {e}")


    except Exception as e:
        print(f"ImportExportService 演示过程中发生错误: {e}")
        print("请确保 Virtuoso 服务正在运行，并且 .env 文件已正确配置。")
