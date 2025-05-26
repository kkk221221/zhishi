# src/data_layer/data_processing/process_tcm_books.py
# 处理中医典籍的脚本

import os
# 确保模块的根目录在Python的搜索路径中，以便正确导入自定义模块
# 对于命令行直接运行此脚本，可能需要根据实际项目结构调整PYTHONPATH
# 或者在IDE中配置正确的源根目录
# 例如，如果项目根目录是TCM_LLM_Project，且src是其中的一个包
# 则可以这样添加:
# import sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


from src.llm_center.llm_interface import LLMInterface
from src.data_layer.data_processing.utils import read_text_file, write_text_file, ensure_directory_exists, clean_filename
from src.data_layer.data_processing.prompts.tcm_prompts import TCM_CHAPTER_PARAGRAPH_SPLIT_TEMPLATE

RAW_TCM_BOOKS_DIR = "src/data_layer/data/raw/TCM_traditional_book"
PROCESSED_TCM_BOOKS_DIR = "src/data_layer/data/processed/TCM_traditional_book"

def get_author_from_book_title_heuristic(book_title: str) -> str:
    # 启发式方法从书名中提取作者
    # 示例: "黄帝内经" -> "黄帝"
    # :param book_title: 书名
    # :return: 提取的作者名，如果无法确定则返回"未知作者"
    if "黄帝内经" in book_title:
        return "黄帝"
    if "伤寒杂病论" in book_title or "伤寒论" in book_title or "金匮要略" in book_title:
        return "张仲景"
    # 可以根据需要添加更多规则
    return "未知作者"

def split_into_chapters_placeholder(book_content: str, book_title: str) -> list[tuple[str, str]]:
    # 占位符函数：将书籍内容拆分为章节。
    # 实际应用中需要根据具体书籍的格式进行更复杂的拆分。
    # 例如，基于正则表达式匹配 "xxx篇"、"卷Y" 等。
    # :param book_content: 书籍的全部内容。
    # :param book_title: 书名。
    # :return: 一个包含 (章节标题, 章节内容) 元组的列表。
    print(f"提醒：当前对《{book_title}》的章节拆分使用的是占位符逻辑，将全书视为单一章节“完整内容”。")
    return [("完整内容", book_content)]

def process_tcm_books(llm_interface: LLMInterface):
    # 处理所有中医典籍文件。
    # 从原始数据目录读取，处理后存入处理后数据目录。
    # :param llm_interface: LLMInterface的实例，用于与大语言模型交互。
    
    ensure_directory_exists(PROCESSED_TCM_BOOKS_DIR)
    print(f"开始处理中医典籍，源目录: {RAW_TCM_BOOKS_DIR}, 输出目录: {PROCESSED_TCM_BOOKS_DIR}")

    if not os.path.exists(RAW_TCM_BOOKS_DIR):
        print(f"错误: 原始数据目录 {RAW_TCM_BOOKS_DIR} 不存在。请检查路径或数据。")
        return

    for filename in os.listdir(RAW_TCM_BOOKS_DIR):
        if filename.endswith(".txt"):
            book_file_path = os.path.join(RAW_TCM_BOOKS_DIR, filename)
            book_title_original = os.path.splitext(filename)[0] # 保留原始书名用于显示和元数据
            
            author = get_author_from_book_title_heuristic(book_title_original)
            
            print(f"\n正在处理书籍: {book_title_original} (作者: {author})")

            book_content = read_text_file(book_file_path)
            if not book_content:
                print(f"  警告: 未能读取书籍内容或文件为空: {book_file_path}")
                continue

            # 创建处理后书籍的特定输出目录
            # 书名和作者名进行清理以适配文件夹命名
            safe_book_title = clean_filename(book_title_original)
            safe_author = clean_filename(author)
            # 目录名使用清理后的书名和作者名
            book_output_dir = os.path.join(PROCESSED_TCM_BOOKS_DIR, f"{safe_book_title}_中医_{safe_author}")
            ensure_directory_exists(book_output_dir)
            print(f"  输出目录已确认/创建: {book_output_dir}")

            # 拆分章节 (当前使用占位符逻辑)
            chapters = split_into_chapters_placeholder(book_content, book_title_original)
            
            for i, (chapter_title_original, chapter_content) in enumerate(chapters):
                print(f"  正在处理章节: {chapter_title_original}")
                
                # 构建提示词
                # 注意：这里的book_title参数使用的是原始书名，以提供给LLM更准确的上下文
                prompt = TCM_CHAPTER_PARAGRAPH_SPLIT_TEMPLATE.format(
                    book_title=book_title_original,
                    chapter_title=chapter_title_original,
                    chapter_content=chapter_content
                )
                
                # 调用LLM进行处理 (例如，段落划分)
                processed_chapter_content = llm_interface.generate_text(prompt)
                
                # 保存处理后的章节
                # 章节名进行清理，并添加序号以防重名或特殊字符问题
                safe_chapter_title = clean_filename(chapter_title_original)
                # 文件名使用清理后的章节名，并添加序号
                output_filename = f"{safe_chapter_title}_段落划分_{i+1}.txt" 
                output_file_path = os.path.join(book_output_dir, output_filename)
                
                write_text_file(output_file_path, processed_chapter_content)
                # print(f"    LLM提示词: {prompt[:200]}...") # 打印部分提示词用于调试
                print(f"    章节处理完成，已保存至: {output_file_path}")
        else:
            print(f"跳过非 .txt 文件: {filename}")
            
    print("\n所有中医典籍处理完毕。")

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
        
    print("开始执行中医典籍处理脚本...")
    process_tcm_books(llm_api)
