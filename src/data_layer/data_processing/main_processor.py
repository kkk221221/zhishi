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

    llm_interface = None
    try:
        print("初始化LLM接口...")
        llm_interface = LLMInterface()
        print("LLM接口初始化成功。")
    except Exception as e:
        print(f"错误：LLM接口初始化失败: {e}")
        print("由于LLM接口未能初始化，后续数据处理流程将无法执行。")
        return # 如果LLM接口无法初始化，则不继续执行

    processing_steps = [
        ("中医典籍", process_tcm_books),
        ("现代文学作品", process_modern_literature),
        ("临床案例", process_clinical_scenarios),
        ("数据库内容", process_database_content),
    ]

    all_successful = True
    for step_name, process_function in processing_steps:
        try:
            print(f"\n--- 开始处理 {step_name} ---")
            process_function(llm_interface)
            print(f"--- {step_name} 处理完成 ---\n")
        except Exception as e:
            print(f"错误：处理 {step_name} 时发生异常: {e}")
            all_successful = False
            # 根据需求，可以选择在这里 return 或 continue
            # continue 会尝试执行后续的处理步骤
            # return 会在第一个错误后停止整个流程

    if all_successful:
        print("所有数据处理流程已成功执行完毕。")
    else:
        print("部分或所有数据处理流程遇到错误，请检查日志。")

if __name__ == '__main__':
    main()
