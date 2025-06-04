# src/data_layer/data_processing/process_database_content.py
# 处理“database”文件夹内容的脚本

import os
from src.llm_center.llm_interface import LLMInterface
from src.data_layer.data_processing.utils import read_text_file, write_text_file, ensure_directory_exists, clean_filename
from src.data_layer.data_processing.prompts.database_prompts import DATABASE_TEXT_CHUNK_TEMPLATE

RAW_DATABASE_DIR = "src/data_layer/data/raw/database"
PROCESSED_DATABASE_DIR = "src/data_layer/data/processed/database"

def process_database_content(llm_interface: LLMInterface):
    # 处理所有“database”目录下的文本文件，进行文本分块。
    # :param llm_interface: LLMInterface的实例。
    
    ensure_directory_exists(PROCESSED_DATABASE_DIR)
    print(f"开始处理数据库内容，源目录: {RAW_DATABASE_DIR}, 输出目录: {PROCESSED_DATABASE_DIR}")

    if not os.path.exists(RAW_DATABASE_DIR):
        print(f"错误: 原始数据目录 {RAW_DATABASE_DIR} 不存在。请检查路径或数据。")
        return

    for filename in os.listdir(RAW_DATABASE_DIR):
        # 根据需要处理的文件类型进行调整，这里以.txt为例
        # 注意: 之前的文件列表显示该目录下可能有 .pdf 文件，此脚本当前只处理 .txt。
        # 后续可能需要添加对其他文件类型的支持（如PDF文本提取）。
        if filename.endswith(".txt"): 
            file_path = os.path.join(RAW_DATABASE_DIR, filename)
            file_title = os.path.splitext(filename)[0] # 保留原始标题用于显示和元数据
            
            print(f"\n正在处理数据库文件: {file_title}")

            text_content = read_text_file(file_path)
            if not text_content:
                print(f"  警告: 未能读取文件内容或文件为空: {file_path}")
                continue

            # 构建提示词进行文本分块
            prompt = DATABASE_TEXT_CHUNK_TEMPLATE.format(text_content=text_content)
            
            # 调用LLM进行处理
            chunked_text = llm_interface.generate_text(prompt)
            
            # 保存处理后的文本块
            safe_file_title = clean_filename(file_title)
            output_filename = f"{safe_file_title}_chunked.txt"
            output_file_path = os.path.join(PROCESSED_DATABASE_DIR, output_filename)

            # Check if the chunked file already exists
            if os.path.exists(output_file_path):
                print(f"  数据库文件 《{file_title}》 的分块输出似乎已经存在 ({output_filename})，跳过。")
                continue
            
            write_text_file(output_file_path, chunked_text)
            # print(f"    LLM提示词: {prompt[:200]}...") # 打印部分提示词用于调试
            print(f"  分块文本已保存至: {output_file_path}")
        elif filename.endswith(".pdf"):
            # 对PDF的处理需要额外的库（如PyMuPDF/fitz, pdfplumber）来提取文本
            # 此处仅作提醒，当前脚本不包含PDF处理逻辑
            pdf_file_path = os.path.join(RAW_DATABASE_DIR, filename)
            print(f"提醒: 文件 {pdf_file_path} 是PDF。当前脚本仅处理.txt文件。PDF文本提取需额外实现。")
        else:
            print(f"跳过非txt/非pdf文件: {filename}") # 更明确的跳过信息
            
    print("\n数据库内容处理完毕。")

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
        
    print("开始执行数据库内容处理脚本...")
    process_database_content(llm_api)
