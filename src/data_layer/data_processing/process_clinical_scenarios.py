# src/data_layer/data_processing/process_clinical_scenarios.py
# 处理临床案例的脚本

import os
import json # 新增JSON导入
from src.llm_center.llm_interface import LLMInterface
from src.data_layer.data_processing.utils import read_text_file, write_text_file, ensure_directory_exists, clean_filename
from src.data_layer.data_processing.prompts.clinical_prompts import CLINICAL_CASE_JSON_EXTRACTION_TEMPLATE # 更改导入的模板

RAW_CLINICAL_DIR = "src/data_layer/data/raw/clinical_scenario"
PROCESSED_CLINICAL_DIR = "src/data_layer/data/processed/clinical_scenario"

def process_clinical_scenarios(llm_interface: LLMInterface):
    # 处理所有临床案例文件，进行简单标准化。
    # 遍历RAW_CLINICAL_DIR下的所有子目录和文件，
    # 在PROCESSED_CLINICAL_DIR下创建相同的目录结构，并保存处理后的文件。
    # :param llm_interface: LLMInterface的实例。
    
    ensure_directory_exists(PROCESSED_CLINICAL_DIR) # 确保根输出目录存在
    print(f"开始处理临床案例，源目录: {RAW_CLINICAL_DIR}, 输出目录: {PROCESSED_CLINICAL_DIR}")

    if not os.path.exists(RAW_CLINICAL_DIR):
        print(f"错误: 原始数据目录 {RAW_CLINICAL_DIR} 不存在。请检查路径或数据。")
        return

    for root, dirs, files in os.walk(RAW_CLINICAL_DIR):
        # 计算对应的输出目录路径
        # os.path.relpath 获取从 RAW_CLINICAL_DIR 到当前 root 的相对路径
        # 例如，如果 RAW_CLINICAL_DIR 是 "src/data/raw/clinical_scenario"
        # root 是 "src/data/raw/clinical_scenario/docter-li"
        # relative_path 将是 "docter-li"
        relative_path = os.path.relpath(root, RAW_CLINICAL_DIR)
        
        # 如果 relative_path 是 "." (表示当前是RAW_CLINICAL_DIR本身), 
        # 则 current_output_dir 就是 PROCESSED_CLINICAL_DIR
        # 否则，它是 PROCESSED_CLINICAL_DIR 下的相应子目录
        if relative_path == ".":
            current_output_dir = PROCESSED_CLINICAL_DIR
        else:
            current_output_dir = os.path.join(PROCESSED_CLINICAL_DIR, relative_path)
        
        ensure_directory_exists(current_output_dir) # 确保当前子目录在processed中也存在
        print(f"  确保输出子目录存在: {current_output_dir}")

        for filename in files:
            # 根据需要处理的文件类型进行调整，这里以.txt为例
            if filename.endswith(".txt"): 
                raw_file_path = os.path.join(root, filename)
                
                print(f"  正在处理临床案例文件: {raw_file_path}")

                case_content = read_text_file(raw_file_path)
                if not case_content:
                    print(f"    警告: 未能读取文件内容或文件为空: {raw_file_path}")
                    continue

                # 构建提取JSON的提示词
                prompt = CLINICAL_CASE_JSON_EXTRACTION_TEMPLATE.format(case_content=case_content)
                
                # 调用LLM进行处理，期望返回JSON字符串
                llm_output_str = llm_interface.generate_text(prompt)
                
                if not llm_output_str or not llm_output_str.strip():
                    print(f"    警告: LLM对于文件 {filename} 返回了空响应。跳过此文件。")
                    continue

                try:
                    extracted_data = json.loads(llm_output_str)
                except json.JSONDecodeError as e:
                    print(f"    错误: 解析文件 {filename} 的LLM输出为JSON时失败: {e}")
                    print(f"    LLM原始输出 (前500字符): {llm_output_str[:500]}")
                    # 可选：将原始错误输出保存到特定文件
                    # error_filename = f"{base}_error.txt"
                    # error_file_path = os.path.join(current_output_dir, error_filename)
                    # write_text_file(error_file_path, f"Error parsing JSON from LLM for {filename}:\n{e}\nRaw output:\n{llm_output_str}")
                    continue # 跳过此文件

                # 定义输出JSON文件名
                base, ext = os.path.splitext(filename)
                # 使用 clean_filename 清理基础文件名，确保文件名在各系统上有效且整洁
                cleaned_base = clean_filename(base) 
                if not cleaned_base: # 万一清理后文件名变为空（例如，原文件名只包含非法字符）
                    cleaned_base = f"untitled_case_{os.path.basename(raw_file_path).split('.')[0]}" # 提供一个基于原始路径的备用名
                output_filename = f"{cleaned_base}.json" # 新的文件名为 .json
                output_file_path = os.path.join(current_output_dir, output_filename)

                # Check if the processed JSON file already exists
                if os.path.exists(output_file_path):
                    print(f"    临床案例 《{filename}》 的JSON输出文件似乎已经存在 ({output_filename})，跳过。")
                    continue
                
                # 将提取的数据作为JSON字符串写入文件
                # 使用 ensure_ascii=False 来正确处理中文字符，indent=4 来格式化输出
                try:
                    json_output_content = json.dumps(extracted_data, ensure_ascii=False, indent=4)
                    write_text_file(output_file_path, json_output_content)
                    print(f"    提取的JSON数据已保存至: {output_file_path}")
                except Exception as e:
                    print(f"    错误: 将提取的JSON数据写入文件 {output_file_path} 时失败: {e}")
                    continue
            else:
                print(f"  跳过非 .txt 文件: {os.path.join(root, filename)}")
            
    print("\n所有临床案例处理完毕。")

if __name__ == '__main__':
    print("初始化LLM接口...")
    # 确保LLMInterface可以被正确实例化
    try:
        llm_api = LLMInterface() 
    except Exception as e:
        print(f"实例化LLMInterface时发生错误: {e}")
        print("请确保LLMInterface类已正确定义并且其依赖项可用。")
        exit(1)
        
    print("开始执行临床案例处理脚本...")
    process_clinical_scenarios(llm_api)
