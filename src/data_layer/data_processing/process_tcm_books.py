# src/data_layer/data_processing/process_tcm_books.py
# 处理中医典籍的脚本

import os
import math
import json
# 确保模块的根目录在Python的搜索路径中，以便正确导入自定义模块
# 对于命令行直接运行此脚本，可能需要根据实际项目结构调整PYTHONPATH
# 或者在IDE中配置正确的源根目录
# 例如，如果项目根目录是TCM_LLM_Project，且src是其中的一个包
# 则可以这样添加:
# import sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


from src.llm_center.llm_interface import LLMInterface
from src.data_layer.data_processing.utils import read_text_file, write_text_file, ensure_directory_exists, clean_filename
from src.data_layer.data_processing.prompts.tcm_prompts import SEMANTIC_MICRO_PARAGRAPH_SPLIT_TEMPLATE

RAW_TCM_BOOKS_DIR = "src/data_layer/data/raw/TCM_traditional_book"
PROCESSED_TCM_BOOKS_DIR = "src/data_layer/data/processed/TCM_traditional_book"

def get_section_chunks(section_text: str, chunk_size: int = 3500, overlap: int = 400) -> list[str]:
    # 将章节内容分割成适合LLM处理的、带有重叠的文本块。
    # :param section_text: 章节的完整文本内容。
    # :param chunk_size: 每个文本块的目标最大字符数。
    # :param overlap: 连续文本块之间的重叠字符数，以保持上下文连贯。
    # :return: 文本块列表。

    if not section_text:
        return []

    chunks = []
    current_pos = 0
    text_len = len(section_text)

    while current_pos < text_len:
        # 重叠部分在块的开始处
        start_pos = max(0, current_pos - overlap)
        # 理想的块结束位置
        end_pos = min(text_len, current_pos + chunk_size)

        actual_end_pos = end_pos
        if end_pos < text_len: # 如果不是最后一个块
            # 尝试在块的后半部分（例如，最后20%）寻找自然断点（段落或句子）
            # 这里简化为优先找双换行，然后单换行
            search_start_for_break = current_pos + int(chunk_size * 0.8)
            if end_pos > search_start_for_break: # 确保有搜索区间
                # 优先找双换行符
                double_newline_idx = section_text.rfind('\n\n', search_start_for_break, end_pos)
                if double_newline_idx != -1:
                    actual_end_pos = double_newline_idx + 2 # 包含双换行符
                else:
                    # 其次找单换行符
                    single_newline_idx = section_text.rfind('\n', search_start_for_break, end_pos)
                    if single_newline_idx != -1:
                        actual_end_pos = single_newline_idx + 1 # 包含单换行符
                    # else: 保留 calculated end_pos (硬截断)

        chunk_content = section_text[start_pos:actual_end_pos]
        chunks.append(chunk_content)
        
        # 更新下一个块的起始处理位置 (不是 start_pos，而是 actual_end_pos 减去 overlap 才是下一个迭代的 current_pos)
        # current_pos 应该是下一个块主要内容（非重叠部分）的开始
        current_pos = actual_end_pos
        if current_pos >= text_len and len(chunks) > 0 and chunks[-1] != section_text[max(0, actual_end_pos - overlap):]:
             # This condition is tricky. If actual_end_pos brought us to text_len, loop will terminate.
             # This is mostly to prevent infinite loops if actual_end_pos calculation is stuck.
             pass


        # 防止因重叠或切分逻辑问题导致的无限循环
        if start_pos == current_pos and current_pos < text_len: 
            # 如果位置没有前进，但还没到文本末尾，则强制前进以避免死循环
            print(f"警告：文本块处理位置未前进。强制移动 {chunk_size // 2} 个字符以避免无限循环。当前位置：{current_pos}")
            current_pos += chunk_size // 2
            if current_pos >= text_len and chunks[-1] != section_text[start_pos:]: # if we jumped past the end
                 # and the last chunk wasn't the remainder
                 last_chunk_content = section_text[start_pos:]
                 if chunks[-1] != last_chunk_content: # avoid duplicate if previous logic added it
                    chunks.append(last_chunk_content)


    # 确保最后一个块包含到文本末尾的所有内容
    if chunks and chunks[-1] != section_text[max(0, current_pos - overlap - len(chunks[-1])):]: # A bit complex check, simplify if problematic
        # A simpler check: if the end of the last chunk isn't the end of the text
        if not chunks[-1].endswith(section_text[-overlap:]): # Heuristic
             #This logic might need refinement to ensure the very end is captured without significant duplication
             #For now, if current_pos didn't reach end, it means the loop exited due to start_pos == current_pos
             #or some other condition. We ensure the tail is processed.
             final_start = chunks[-1].find(section_text[current_pos-overlap:current_pos-overlap+100]) if overlap > 100 else current_pos-overlap
             if final_start == -1 : final_start = current_pos - overlap
             final_start = max(0, final_start) # ensure positive
             if final_start < text_len: # If there's remaining text
                remaining_text = section_text[final_start:]
                # Avoid adding if it's identical to the last chunk or a small part of it
                if remaining_text and (not chunks[-1].endswith(remaining_text)):
                     chunks.append(remaining_text)


    # 移除可能产生的空字符串块
    return [c for c in chunks if c]

# (Ensure SEMANTIC_MICRO_PARAGRAPH_SPLIT_TEMPLATE is imported from .prompts)

def perform_fine_grained_segmentation(
    document_title: str,               # Original book/document title for context
    section_title: str,                # Title of the current section being processed
    section_content: str,              # Full text content of the section
    llm_interface: LLMInterface,       # LLM interface
    utils_clean_filename: callable     # clean_filename utility for sub-section titles
) -> list[dict]:
    # 对单个章节内容进行细粒度的、基于语义的段落切分。
    # :param document_title: 原始文档标题，用于LLM提示词上下文。
    # :param section_title: 当前章节的标题。
    # :param section_content: 当前章节的完整文本内容。
    # :param llm_interface: LLMInterface的实例。
    # :param utils_clean_filename: clean_filename工具函数引用。
    # :return: 一个字典列表，每个字典代表一个（可选的）子章节及其段落，
    #          格式为 [{"sub_section_title": "可选的子章节标题", "paragraphs": ["段落1文本", "段落2文本"]}, ...]。
    #          如果没有子章节标题，则 "sub_section_title" 键可能不存在或为None/空。

    if not section_content.strip():
        print(f"      警告：章节 “{section_title}” 内容为空，跳过细粒度切分。")
        return []

    # 使用 get_section_chunks 将章节内容切分为适合LLM处理的小块
    # 注意：这里的 document_title 对应 SEMANTIC_MICRO_PARAGRAPH_SPLIT_TEMPLATE 中的 {document_title}
    chunks = get_section_chunks(section_content) # Uses default chunk_size and overlap from get_section_chunks

    all_structured_paragraphs = [] # 最终结果列表
    current_sub_section_title = None # 当前活动的子章节标题

    print(f"      开始对章节 “{section_title}” (共 {len(chunks)} 个文本块) 进行细粒度段落切分...")

    for i, chunk_text in enumerate(chunks):
        print(f"        处理文本块 {i + 1}/{len(chunks)}...")

        prompt = SEMANTIC_MICRO_PARAGRAPH_SPLIT_TEMPLATE.format(
            document_title=document_title,
            section_title=section_title,
            text_chunk_content=chunk_text
        )
        
        raw_llm_output = llm_interface.generate_text(prompt)

        if not raw_llm_output or not raw_llm_output.strip():
            print(f"          警告：LLM对于文本块 {i+1} 返回了空响应。")
            # 考虑是否将原始chunk_text作为未处理段落加入
            # all_structured_paragraphs.append({"sub_section_title": current_sub_section_title, "paragraphs": [chunk_text]})
            continue

        # 按分隔符 ---PARAGRAPH_END--- 切分LLM的输出
        # LLM被指示在每个段落后（包括最后一个）都添加此分隔符
        raw_paragraphs = raw_llm_output.split("---PARAGRAPH_END---")

        chunk_paragraphs_buffer = [] # 存储当前块处理的段落，直到遇到新的子章节标题或块结束

        for para_text_raw in raw_paragraphs:
            para_text = para_text_raw.strip() # 去除首尾空白

            if not para_text: # 跳过因额外换行或分隔符产生的空字符串
                continue
            
            # 检查是否为子章节标题
            if para_text.startswith("SUB-SECTION-TITLE:"):
                # 如果当前缓冲区有段落，先保存它们到上一个子章节（或主章节）
                if chunk_paragraphs_buffer:
                    all_structured_paragraphs.append({
                        "sub_section_title": current_sub_section_title, # 这将是上一个子标题
                        "paragraphs": list(chunk_paragraphs_buffer) # 复制列表
                    })
                    chunk_paragraphs_buffer.clear()

                # 更新当前子章节标题
                potential_title = para_text.replace("SUB-SECTION-TITLE:", "").strip()
                current_sub_section_title = utils_clean_filename(potential_title) if potential_title else "未命名子章节"
                if not current_sub_section_title: # 如果清理后为空
                     current_sub_section_title = "未命名子章节"
                print(f"          识别到子章节标题： “{current_sub_section_title}”")
            else:
                # 是普通段落内容
                chunk_paragraphs_buffer.append(para_text)
        
        # 处理当前文本块末尾剩余的段落（属于最后一个子章节标题或主章节）
        if chunk_paragraphs_buffer:
            all_structured_paragraphs.append({
                "sub_section_title": current_sub_section_title, # 当前活动的子标题
                "paragraphs": list(chunk_paragraphs_buffer)
            })
            chunk_paragraphs_buffer.clear() # 虽然循环结束，好习惯

    # 合并逻辑：如果连续的条目具有相同的 sub_section_title (包括 None), 则合并它们的 paragraphs 列表。
    # 这可以处理一个子章节的内容跨越多个LLM输出块（由get_section_chunks分割）的情况。
    if not all_structured_paragraphs:
        return []

    merged_output = []
    
    # 第一个元素直接添加
    # 注意：这里的current_sub_section_title是最后一个chunk的最后一个sub_section_title，不能作为全局的初始值
    # 我们需要从all_structured_paragraphs的第一个元素开始推断
    
    # 初始化第一个合并条目
    # merged_output.append({
    #     "sub_section_title": all_structured_paragraphs[0].get("sub_section_title"), 
    #     "paragraphs": list(all_structured_paragraphs[0].get("paragraphs", []))
    # })
    
    # for current_segment in all_structured_paragraphs[1:]:
    #     current_seg_title = current_segment.get("sub_section_title")
    #     prev_merged_title = merged_output[-1].get("sub_section_title")
        
    #     if current_seg_title == prev_merged_title: # 比较 cleaned title
    #         merged_output[-1]["paragraphs"].extend(current_segment.get("paragraphs", []))
    #     else:
    #         merged_output.append({
    #             "sub_section_title": current_seg_title,
    #             "paragraphs": list(current_segment.get("paragraphs", []))
    #         })
    # 简单的合并：如果一个子章节跨越多个LLM chunk的边界，这里的合并逻辑可能不够完美。
    # LLM通过overlap和上下文提示，理论上应该能在chunk内完成一个子章节的标题声明。
    # 如果LLM严格遵守“在子分组第一个段落前声明SUB-SECTION-TITLE”，那么这里的合并逻辑可以简化。
    # 目前的结构是，每个chunk处理完后，如果buffer中有内容，就追加到all_structured_paragraphs。
    # 如果一个子章节的段落分布在两个chunk中，且第二个chunk的开头没有再次声明SUB-SECTION-TITLE，
    # 那么第二个chunk的段落会错误地继承第一个chunk末尾的sub_section_title。

    # 修正后的合并逻辑：
    # 上面的 all_structured_paragraphs 可能包含重复的 title 和分散的 paragraphs 列表
    # 例如: [{"title": "A", "paras": ["p1"]}, {"title": "A", "paras": ["p2"]}]
    # 需要合并为: [{"title": "A", "paras": ["p1", "p2"]}]
    
    # 或者，如果LLM在每个新chunk的开头都能正确地重新声明（或不声明）SUB-SECTION-TITLE，
    # 那么 all_structured_paragraphs 的结构可能已经是接近期望的了，
    # 例如：chunk1处理结果 [{"title":"T1", "paras":["p1","p2"]}]
    #       chunk2处理结果 [{"title":"T1", "paras":["p3"]}, {"title":"T2", "paras":["p4"]}]
    # all_structured_paragraphs 会是 [..., {"title":"T1", "paras":["p1","p2"]}, {"title":"T1", "paras":["p3"]}, {"title":"T2", "paras":["p4"]}, ...]
    # 这种情况下，下面的合并逻辑是正确的。

    if not all_structured_paragraphs: return []

    # 第一个元素直接作为起点
    merged_output.append(dict(all_structured_paragraphs[0])) # 使用dict()创建副本

    for i in range(1, len(all_structured_paragraphs)):
        current_seg_title = all_structured_paragraphs[i].get("sub_section_title")
        # 使用 cleaned title 进行比较
        # merged_output[-1] 是当前正在构建的合并后条目
        last_merged_title = merged_output[-1].get("sub_section_title")

        if current_seg_title == last_merged_title:
            merged_output[-1]["paragraphs"].extend(all_structured_paragraphs[i].get("paragraphs", []))
        else:
            # 新的子章节标题或从有标题变为无标题（主章节段落）
            merged_output.append(dict(all_structured_paragraphs[i])) # 创建副本

    print(f"      章节 “{section_title}” 的细粒度段落切分完成。共生成 {sum(len(s.get('paragraphs',[])) for s in merged_output)} 个段落，分布在 {len(merged_output)} 个内容组中。")
    return merged_output

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
            
            # The directory name from user feedback is f"{safe_book_title}_特性_{safe_author_or_source}"
            # Assuming "特性" is a literal part of the name, and "source" is the author.
            book_output_dir = os.path.join(PROCESSED_TCM_BOOKS_DIR, f"{safe_book_title}_特性_{safe_author}")
            ensure_directory_exists(book_output_dir)
            print(f"  输出目录已确认/创建 (新规则): {book_output_dir}")

            # Phase 1: Initial Coarse-Grained Text Segmentation
            print(f"  Phase 1: 《{book_title_original}》被视为单一主要章节进行处理。")
            coarse_sections = [(book_title_original, book_content)] 

            for section_idx, (section_title, section_content_text) in enumerate(coarse_sections):
                print(f"    处理文档章节 {section_idx + 1}/{len(coarse_sections)}: “{section_title}”")
                
                # Phase 2: Fine-Grained Semantic Paragraph Splitting
                # document_title is book_title_original, section_title is from coarse_sections
                # utils_clean_filename is clean_filename from utils
                structured_paragraphs_data = perform_fine_grained_segmentation(
                    document_title=book_title_original,
                    section_title=section_title,
                    section_content=section_content_text,
                    llm_interface=llm_interface,
                    utils_clean_filename=clean_filename 
                )

                if not structured_paragraphs_data:
                    print(f"      警告：未能从章节 “{section_title}” 中切分出细粒度段落。")
                    continue

                # Phase 3: File Naming, Directory Structure, and Saving
                print(f"      Phase 3: 开始保存章节 “{section_title}” 的细粒度段落...")
                
                # 初始化文件名计数器字典 (每个主章节/书本重置)
                filename_counters = {} 
                total_paragraphs_saved_in_section = 0

                for group_idx, para_group in enumerate(structured_paragraphs_data):
                    sub_section_title_str = para_group.get("sub_section_title") # 已被 perform_fine_grained_segmentation 清理
                    paragraphs_list = para_group.get("paragraphs", [])

                    if not paragraphs_list:
                        continue

                    safe_main_section_title = clean_filename(section_title)
                    if not safe_main_section_title: 
                        safe_main_section_title = "未命名主章节"

                    # 确定当前段落组的计数器键
                    if sub_section_title_str:
                        counter_key = f"{safe_main_section_title}-{sub_section_title_str}"
                    else:
                        counter_key = safe_main_section_title

                    # 遍历当前组的所有段落，并使用 filename_counters 来获取正确的序号
                    for para_content in paragraphs_list:
                        # 获取并更新当前键的序号
                        current_paragraph_number = filename_counters.get(counter_key, 0) + 1
                        filename_counters[counter_key] = current_paragraph_number

                        if sub_section_title_str:
                            output_filename = f"{safe_main_section_title}-{sub_section_title_str}_{current_paragraph_number}.txt"
                        else:
                            output_filename = f"{safe_main_section_title}_{current_paragraph_number}.txt"
                        
                        output_file_path = os.path.join(book_output_dir, output_filename)
                        write_text_file(output_file_path, para_content)
                        total_paragraphs_saved_in_section += 1
                
                print(f"      章节 “{section_title}” 的所有 {total_paragraphs_saved_in_section} 个细粒度段落已保存。")
            
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
