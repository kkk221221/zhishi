# src/data_layer/data_processing/main_processor.py
# 统一调度所有数据处理脚本的主入口

from src.llm_center.llm_interface import LLMInterface
from src.data_layer.data_processing.process_tcm_books import process_tcm_books
from src.data_layer.data_processing.process_modern_literature import process_modern_literature
from src.data_layer.data_processing.process_clinical_scenarios import process_clinical_scenarios
from src.data_layer.data_processing.process_database_content import process_database_content

def main():
    # 主调度函数，按顺序执行所有数据处理流程。
    print("开始执行统一数据处理流程...")

    # =======================================================================
    # 测试配置: 修改此变量以测试不同的LLM后端
    # 可选值: "ollama", "deepseek", "qwen", "placeholder"
    # 注意: 
    # - "ollama" 需要Ollama服务正在运行。
    # - "deepseek" 需要在 .env 文件中配置 DEEPSEEK_API_KEY。
    # - "qwen" 需要在 .env 文件中配置 QWEN_API_KEY。
    llm_type_to_test = "deepseek"  # <--- 修改这里进行测试
    
    # 可选: 为特定后端指定非默认模型参数 (如果不想用LLMInterface中的默认值)
    # 例如，测试不同的Ollama模型:
    # ollama_model_to_test = "qwen2:1.5b" 
    # deepseek_model_to_test = "deepseek-coder" # 假设有这个模型
    # qwen_model_to_test = "qwen-max"
    # =======================================================================

    llm_interface = None
    try:
        print(f"初始化LLM接口 (类型: {llm_type_to_test})...")
        
        # 根据 llm_type_to_test 实例化 LLMInterface
        # 这里可以根据需要扩展，以传递特定模型的参数
        if llm_type_to_test == "ollama":
            # 示例: 如果要为Ollama传递特定模型 (取消下面一行的注释，并注释掉后面那个llm_interface的赋值)
            # llm_interface = LLMInterface(llm_type=llm_type_to_test, ollama_model=ollama_model_to_test) 
            llm_interface = LLMInterface(llm_type=llm_type_to_test) # 使用LLMInterface中ollama的默认模型
        elif llm_type_to_test == "deepseek":
            # 示例: 如果要为DeepSeek传递特定模型 (取消下面一行的注释，并注释掉后面那个llm_interface的赋值)
            # llm_interface = LLMInterface(llm_type=llm_type_to_test, deepseek_model=deepseek_model_to_test)
            llm_interface = LLMInterface(llm_type=llm_type_to_test) # 使用LLMInterface中deepseek的默认模型
        elif llm_type_to_test == "qwen":
            # 示例: 如果要为Qwen传递特定模型 (取消下面一行的注释，并注释掉后面那个llm_interface的赋值)
            # llm_interface = LLMInterface(llm_type=llm_type_to_test, qwen_model=qwen_model_to_test)
            llm_interface = LLMInterface(llm_type=llm_type_to_test) # 使用LLMInterface中qwen的默认模型
        elif llm_type_to_test == "placeholder":
            llm_interface = LLMInterface(llm_type=llm_type_to_test)
        else:
            # LLMInterface的构造函数本身会处理不支持的类型，但这里可以提前捕获
            print(f"错误: 无效的 llm_type_to_test ('{llm_type_to_test}')。请检查配置。")
            return

        print("LLM接口初始化成功。")
    except ValueError as ve: # 捕获LLMInterface中对llm_type的ValueError
        print(f"错误：LLM接口初始化失败: {ve}")
        print("由于LLM接口未能初始化，后续数据处理流程将无法执行。")
        return
    except Exception as e: # 捕获其他可能的初始化错误 (如API密钥问题导致的间接错误，尽管目前是警告)
        print(f"错误：LLM接口初始化时发生预料之外的错误: {e}")
        print("由于LLM接口未能初始化，后续数据处理流程将无法执行。")
        return

    processing_steps = [
        ("中医典籍", process_tcm_books),
        ("现代文学作品", process_modern_literature),
        ("临床案例", process_clinical_scenarios),
        ("数据库内容", process_database_content),
    ]

    all_successful = True
    for step_name, process_function in processing_steps:
        try:
            print(f"\n--- 开始处理 {step_name} (使用LLM: {llm_type_to_test}) ---")
            process_function(llm_interface)
            print(f"--- {step_name} 处理完成 ---\n")
        except Exception as e:
            print(f"错误：处理 {step_name} 时发生异常: {e}")
            all_successful = False
            # 根据需求，可以选择在这里 return 或 continue
            # continue 会尝试执行后续的处理步骤
            # return 会在第一个错误后停止整个流程

    if all_successful:
        print(f"所有数据处理流程已成功执行完毕 (使用LLM: {llm_type_to_test})。")
    else:
        print(f"部分或所有数据处理流程遇到错误 (使用LLM: {llm_type_to_test})，请检查日志。")

if __name__ == '__main__':
    main()
