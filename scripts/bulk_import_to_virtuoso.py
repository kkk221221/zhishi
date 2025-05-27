# scripts/bulk_import_to_virtuoso.py
import argparse
import json
import os
import sys

# 为了能够从脚本内部导入 tcm_kg_virtuoso_module 包中的模块，
# 需要确保 tcm_kg_virtuoso_module 的父目录 (通常是项目根目录) 在 Python 路径中。
# 如果脚本是从项目根目录运行的 (例如 python scripts/bulk_import_to_virtuoso.py),
# Python 通常会自动处理。但如果脚本在其他地方或以其他方式运行，可能需要调整 sys.path。
# 以下是一种常见的处理方式：
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # 项目根目录是 scripts 目录的上一级
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.tcm_kg_virtuoso_module.core import config as app_config
    from src.tcm_kg_virtuoso_module.graph_db.virtuoso_connector import VirtuosoConnector
    from src.tcm_kg_virtuoso_module.services.entity_service import EntityService
    from src.tcm_kg_virtuoso_module.services.relationship_service import RelationshipService
    from src.tcm_kg_virtuoso_module.services.import_export_service import ImportExportService
    from src.tcm_kg_virtuoso_module.api.schemas import TripleSchema # 用于校验三元组结构 (可选)
except ImportError as e:
    print(f"错误：导入模块失败。请确保脚本能正确访问 'src.tcm_kg_virtuoso_module'。") # Updated error message
    print(f"ImportError: {e}")
    print(f"当前 Python 路径 (sys.path): {sys.path}")
    print(f"项目根目录 (尝试添加到路径): {PROJECT_ROOT}")
    sys.exit(1)


def main():
    """主函数，处理命令行参数并执行导入操作。"""
    parser = argparse.ArgumentParser(
        description="中医知识图谱批量导入脚本。",
        formatter_class=argparse.RawTextHelpFormatter # 允许在help信息中使用换行
    )
    
    # 参数组：通过文件批量导入三元组
    triples_group = parser.add_argument_group(
        title="通过文件批量导入三元组 (bulk_insert_triples)",
        description="从指定文件读取三元组并批量导入。"
    )
    triples_group.add_argument(
        "--file-path", 
        type=str,
        help="包含三元组数据的JSONL文件路径。\n"
             "每行一个JSON对象，格式为: \n"
             '  {"subject": "<s>", "predicate": "<p>", "object_val": "<o_uri_or_literal>"}\n'
             '或 {"subject": "<s>", "predicate": "<p>", "object_val": 123}\n'
             '其中 object_val 可以是URI字符串、普通字符串字面量、数字或布尔值。'
    )
    triples_group.add_argument(
        "--graph-uri", 
        type=str, 
        default=None,
        help="目标图的URI。如果未提供，则使用配置文件中的默认图URI。"
    )
    triples_group.add_argument(
        "--batch-size", 
        type=int, 
        default=100,
        help="每批次插入的三元组数量 (默认: 100)。"
    )

    # 参数组：从处理后的结构化数据导入 (占位符功能)
    processed_data_group = parser.add_argument_group(
        title="从处理后的结构化数据导入 (import_from_processed_data - 未来功能)",
        description="此功能依赖于服务层 'import_from_processed_data' 方法的完整实现。"
    )
    processed_data_group.add_argument(
        "--data-type", 
        type=str,
        help="要导入的数据类型 (例如 'tcm_book_paragraphs', 'clinical_case_json')。\n"
             "此参数用于调用服务层的 import_from_processed_data 方法。"
    )
    processed_data_group.add_argument(
        "--source-path", 
        type=str,
        help="包含已处理数据的文件或目录路径。\n"
             "此参数用于调用服务层的 import_from_processed_data 方法。"
    )

    args = parser.parse_args()

    # 初始化服务
    print("正在初始化服务...")
    try:
        connector = VirtuosoConnector(
            endpoint_url=app_config.VIRTUOSO_URL,
            username=app_config.VIRTUOSO_USER,
            password=app_config.VIRTUOSO_PASSWORD,
            default_graph=app_config.DEFAULT_GRAPH_URI
        )
        # 测试连接 (可选，但推荐)
        if connector.execute_select_query("ASK {?s ?p ?o}") is None:
            print("错误: 无法连接到 Virtuoso 数据库或执行测试查询失败。请检查配置和数据库状态。")
            sys.exit(1)
        print("Virtuoso 连接成功。")

        entity_service = EntityService(connector=connector, config_module=app_config)
        relationship_service = RelationshipService(connector=connector, config_module=app_config)
        import_export_service = ImportExportService(
            connector=connector,
            entity_service=entity_service,
            relationship_service=relationship_service,
            config_module=app_config
        )
        print("服务初始化完毕。")
    except Exception as e:
        print(f"错误: 服务初始化失败 - {e}")
        sys.exit(1)


    # --- 执行操作 ---
    action_taken = False

    # 1. 处理通过文件批量导入三元组
    if args.file_path:
        action_taken = True
        print(f"\n--- 开始从文件批量导入三元组 ---")
        print(f"  文件路径: {args.file_path}")
        print(f"  目标图 URI: {args.graph_uri if args.graph_uri else app_config.DEFAULT_GRAPH_URI}")
        print(f"  批次大小: {args.batch_size}")

        if not os.path.exists(args.file_path):
            print(f"错误: 文件 '{args.file_path}' 不存在。")
            sys.exit(1)

        triples_to_load = []
        try:
            with open(args.file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    try:
                        data = json.loads(line.strip())
                        # 使用Pydantic模型进行基本校验 (可选，但推荐)
                        triple_model = TripleSchema(**data)
                        triples_to_load.append(
                            (str(triple_model.subject), str(triple_model.predicate), triple_model.object_val)
                        )
                    except json.JSONDecodeError:
                        print(f"警告: 第 {i+1} 行JSON解析失败，已跳过: {line.strip()}")
                    except Exception as pydantic_err: # ValidationError from Pydantic
                        print(f"警告: 第 {i+1} 行数据结构校验失败，已跳过: {line.strip()} - 错误: {pydantic_err}")
            
            if not triples_to_load:
                print("错误: 文件中未找到有效的三元组数据。")
                sys.exit(1)

            print(f"从文件中成功加载 {len(triples_to_load)} 个三元组。")
            
            success = import_export_service.bulk_insert_triples(
                triples=triples_to_load,
                graph_uri=args.graph_uri, # 如果为None，服务层会用默认图
                batch_size=args.batch_size
            )

            if success:
                print("批量导入三元组成功完成。")
            else:
                print("批量导入三元组过程中发生错误或部分失败。请检查日志。")
        
        except Exception as e:
            print(f"处理三元组文件时发生错误: {e}")
            sys.exit(1)

    # 2. 处理从结构化数据导入 (占位符)
    if args.data_type and args.source_path:
        action_taken = True
        print(f"\n--- 尝试从处理后的结构化数据导入 (未来功能) ---")
        print(f"  数据类型: {args.data_type}")
        print(f"  源路径: {args.source_path}")
        try:
            import_export_service.import_from_processed_data(
                data_type=args.data_type,
                source_path=args.source_path
            )
            print("调用 import_from_processed_data 完成 (注意: 此功能当前为占位符)。")
        except NotImplementedError:
            print("错误: 'import_from_processed_data' 功能尚未完整实现。")
        except Exception as e:
            print(f"调用 import_from_processed_data 时发生错误: {e}")
    elif args.data_type or args.source_path: # 如果只提供了其中一个参数
        print("\n警告: 使用 --data-type 和 --source-path 参数进行导入时，两者都必须提供。")
        action_taken = True


    if not action_taken:
        print("\n没有指定操作。请使用 --file-path 或 (--data-type 和 --source-path) 参数。")
        parser.print_help()

if __name__ == "__main__":
    # 确保 .env 文件被加载 (如果配置依赖它)
    # from dotenv import load_dotenv
    # load_dotenv(os.path.join(PROJECT_ROOT, '.env')) # 假设 .env 在项目根目录

    main()
