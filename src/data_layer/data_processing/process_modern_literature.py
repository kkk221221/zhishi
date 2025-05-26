# src/data_layer/data_processing/process_modern_literature.py
# 处理现代文学的脚本

import os
from src.llm_center.llm_interface import LLMInterface
from src.data_layer.data_processing.utils import read_text_file, write_text_file, ensure_directory_exists, clean_filename
from src.data_layer.data_processing.prompts.literature_prompts import LITERATURE_SUMMARY_TEMPLATE

RAW_LITERATURE_DIR = "src/data_layer/data/raw/Modern_Literature"
PROCESSED_LITERATURE_DIR = "src/data_layer/data/processed/Modern_Literature"

def process_modern_literature(llm_interface: LLMInterface):
    # 处理所有现代文学文件，生成内容摘要。
    # 从原始数据目录读取，处理后存入处理后数据目录。
    # :param llm_interface: LLMInterface的实例，用于与大语言模型交互。
    
    ensure_directory_exists(PROCESSED_LITERATURE_DIR)
    print(f"开始处理现代文学作品，源目录: {RAW_LITERATURE_DIR}, 输出目录: {PROCESSED_LITERATURE_DIR}")

    if not os.path.exists(RAW_LITERATURE_DIR):
        print(f"错误: 原始数据目录 {RAW_LITERATURE_DIR} 不存在。请检查路径或数据。")
        return

    for filename in os.listdir(RAW_LITERATURE_DIR):
        # 根据需要处理的文件类型进行调整，这里以.txt为例
        if filename.endswith(".txt"): 
            file_path = os.path.join(RAW_LITERATURE_DIR, filename)
            file_title_original = os.path.splitext(filename)[0] # 保留原始标题用于显示和元数据
            
            print(f"\n正在处理文学作品: {file_title_original}")

            content_fragment = read_text_file(file_path)
            if not content_fragment:
                print(f"  警告: 未能读取文件内容或文件为空: {file_path}")
                continue

            # 构建提示词以生成摘要
            # 注意：这里的title参数使用的是原始标题，以提供给LLM更准确的上下文
            prompt = LITERATURE_SUMMARY_TEMPLATE.format(
                title=file_title_original,
                content_fragment=content_fragment
            )
            
            # 调用LLM进行处理 (生成摘要)
            summary = llm_interface.generate_text(prompt)
            
            # 保存处理后的摘要
            # 文件名使用清理后的标题
            safe_file_title = clean_filename(file_title_original)
            output_filename = f"{safe_file_title}_summary.txt"
            output_file_path = os.path.join(PROCESSED_LITERATURE_DIR, output_filename)
            
            write_text_file(output_file_path, summary)
            # print(f"    LLM提示词: {prompt[:200]}...") # 打印部分提示词用于调试
            print(f"  摘要已生成并保存至: {output_file_path}")
        else:
            print(f"跳过非 .txt 文件: {filename}")
            
    print("\n所有现代文学作品处理完毕。")

if __name__ == '__main__':
    print("初始化LLM接口...")
    # 确保LLMInterface可以被正确实例化
    # 如果LLMInterface的__init__需要参数，需要在这里提供
    try:
        llm_api = LLMInterface() 
    except Exception as e:
        print(f"实例化LLMInterface时发生错误: {e}")
        print("请确保LLMInterface类已正确定义并且其依赖项可用。")
        exit(1)
        
    print("开始执行现代文学作品处理脚本...")
    process_modern_literature(llm_api)
