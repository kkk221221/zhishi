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

import logging
import sys # For logging to stdout

# Configure logging
LOG_FILE_PATH = "process_tcm_books.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout) # Log to console as well
    ]
)

from src.llm_center.llm_interface import LLMInterface
from src.data_layer.data_processing.utils import read_text_file, write_text_file, ensure_directory_exists, clean_filename
from src.data_layer.data_processing.prompts.tcm_prompts import (
    SEMANTIC_MICRO_PARAGRAPH_SPLIT_TEMPLATE,
    IDENTIFY_AUTHOR_FROM_TITLE_TEMPLATE,
    TOC_GENERATION_PROMPT_TEMPLATE, # Added import for TOC_GENERATION_PROMPT_TEMPLATE
    SHORTEN_TITLE_PROMPT_TEMPLATE # Add this
)

RAW_TCM_BOOKS_DIR = "src/data_layer/data/raw/TCM_traditional_book"
PROCESSED_TCM_BOOKS_DIR = "src/data_layer/data/processed/TCM_traditional_book"

MAX_CHARS_FOR_TOC_PROMPT = 50000 # Example value, can be tuned
TOC_CHUNK_OVERLAP = 5000      # Example value, can be tuned

# segment_book_into_major_sections: 将书籍内容分割成主要章节。
# 使用LLM辅助生成目录(TOC)，并根据TOC精确切分内容。
def segment_book_into_major_sections(
    book_title: str,                    # 书籍标题
    full_book_content: str,             # 书籍的完整内容
    llm_interface: LLMInterface,        # LLM接口实例
    max_chars_for_toc_prompt: int,      # TOC生成提示的最大字符数
    toc_chunk_overlap: int              # TOC生成时文本块的重叠量
) -> list[dict]:
    """
    使用LLM辅助的目录生成和精确内容切分，将书籍内容分割成主要章节。
    :param book_title: 书籍标题。
    :param full_book_content: 书籍的全部文本内容。
    :param llm_interface: LLMInterface的实例。
    :param max_chars_for_toc_prompt: 用于TOC生成提示的最大字符数。
    :param toc_chunk_overlap: TOC生成时文本块之间的重叠字符数。
    :return: 一个字典列表，每个字典代表一个主要章节，包含 "major_section_title" 和 "major_section_content"。
    """
    logging.info(f"开始对书籍《{book_title}》进行主要章节切分")

    chapter_titles_from_llm = [] # 从LLM获取的章节标题列表

    # 如果书籍内容长度小于等于单次提示最大字符数限制
    if len(full_book_content) <= max_chars_for_toc_prompt:
        logging.info(f"书籍《{book_title}》内容长度 ({len(full_book_content)}) 在单次提示限制 ({max_chars_for_toc_prompt} 字符) 内。")
        prompt = TOC_GENERATION_PROMPT_TEMPLATE.format(
            book_title=book_title, text_content=full_book_content
        )
        try:
            raw_llm_output = llm_interface.generate_text(prompt)
            if raw_llm_output.startswith("错误："): # 检查LLM是否返回错误信息
                logging.warning(f"LLM在为《{book_title}》生成目录(单区块)时返回错误：{raw_llm_output}")
            elif isinstance(raw_llm_output, str) and raw_llm_output.strip(): # 确保返回的是非空字符串
                titles = [title.strip() for title in raw_llm_output.split('\n') if title.strip()]
                chapter_titles_from_llm.extend(titles)
                logging.info(f"LLM从单区块为《{book_title}》返回了 {len(titles)} 个潜在标题。")
            else:
                logging.warning(f"LLM调用失败或为《{book_title}》的单区块目录生成返回了空/意外的响应。输出：{raw_llm_output}")
        except Exception as e:
            logging.error(f"LLM在为《{book_title}》生成目录(单区块)时调用失败：{e}", exc_info=True)
    else: # 书籍内容过长，需要分块处理
        logging.info(f"书籍《{book_title}》内容长度 ({len(full_book_content)}) 超出单次提示限制 ({max_chars_for_toc_prompt} 字符)。将使用分块处理。")
        current_pos = 0 # 当前处理位置
        text_len = len(full_book_content) # 文本总长度
        chunk_num = 1 # 区块编号
        while current_pos < text_len:
            chunk_end = min(current_pos + max_chars_for_toc_prompt, text_len) # 区块结束位置
            text_chunk = full_book_content[current_pos:chunk_end] # 当前区块文本

            logging.debug(f"正在处理《{book_title}》的目录生成区块 {chunk_num}：字符 {current_pos}-{chunk_end}")
            prompt = TOC_GENERATION_PROMPT_TEMPLATE.format(
                book_title=book_title, text_content=text_chunk
            )
            try:
                raw_llm_output = llm_interface.generate_text(prompt)
                if raw_llm_output.startswith("错误："):
                    logging.warning(f"LLM在为《{book_title}》生成目录(区块 {chunk_num})时返回错误：{raw_llm_output}")
                elif isinstance(raw_llm_output, str) and raw_llm_output.strip():
                    titles = [title.strip() for title in raw_llm_output.split('\n') if title.strip()]
                    chapter_titles_from_llm.extend(titles)
                    logging.debug(f"LLM从区块 {chunk_num} 为《{book_title}》返回了 {len(titles)} 个潜在标题。")
                else:
                    logging.warning(f"LLM调用失败或为《{book_title}》的区块 {chunk_num} 返回了空/意外的响应。输出：{raw_llm_output}")
            except Exception as e:
                logging.error(f"LLM在为《{book_title}》的区块 {chunk_num} 生成目录时调用失败：{e}", exc_info=True)

            if chunk_end == text_len: # 已到达文本末尾
                break

            current_pos += max_chars_for_toc_prompt - toc_chunk_overlap # 移动到下一个区块的起始位置 (考虑重叠)
            # 确保如果由于重叠导致current_pos超出text_len，但实际上末尾还有一小部分未处理，则处理这部分尾部文本
            if current_pos >= text_len and chunk_end < text_len:
                logging.debug(f"正在处理《{book_title}》目录生成的尾部区块：字符 {chunk_end}-{text_len}")
                text_chunk = full_book_content[chunk_end:text_len]
                prompt = TOC_GENERATION_PROMPT_TEMPLATE.format(
                    book_title=book_title, text_content=text_chunk
                )
                try:
                    raw_llm_output = llm_interface.generate_text(prompt)
                    if raw_llm_output.startswith("错误："):
                         logging.warning(f"LLM在为《{book_title}》生成目录(尾部区块)时返回错误：{raw_llm_output}")
                    elif isinstance(raw_llm_output, str) and raw_llm_output.strip():
                         titles = [title.strip() for title in raw_llm_output.split('\n') if title.strip()]
                         chapter_titles_from_llm.extend(titles)
                         logging.debug(f"LLM从尾部区块为《{book_title}》返回了 {len(titles)} 个潜在标题。")
                    else:
                        logging.warning(f"LLM调用失败或为《{book_title}》的尾部区块返回了空/意外的响应。输出：{raw_llm_output}")
                except Exception as e:
                    logging.error(f"LLM在为《{book_title}》的尾部区块生成目录时调用失败：{e}", exc_info=True)
                break # 处理完尾部后退出循环
            chunk_num += 1

        if chapter_titles_from_llm:
            logging.info(f"从《{book_title}》的区块中总共收集到 {len(chapter_titles_from_llm)} 个标题（去重前）。")
            chapter_titles_from_llm = list(dict.fromkeys(chapter_titles_from_llm)) # 去重并保持顺序
            logging.info(f"为《{book_title}》去重后得到 {len(chapter_titles_from_llm)} 个唯一标题。")

    if not chapter_titles_from_llm: # 如果没有从LLM获取到任何标题
        logging.warning(f"未能从LLM为《{book_title}》提取任何章节标题。将整本书视为一个单独的章节。")
        return [{"major_section_title": book_title, "major_section_content": full_book_content}]

    logging.info(f"《{book_title}》的阶段1（目录生成）完成。找到 {len(chapter_titles_from_llm)} 个唯一标题：{chapter_titles_from_llm}")

    major_sections_data = [] # 存储主要章节数据的列表
    title_positions = [] # 存储标题及其在文本中位置的列表

    # 查找LLM提供的标题在原文中的确切位置
    for title_str in chapter_titles_from_llm:
        try:
            position = full_book_content.find(title_str)
            if position != -1: # 如果找到了标题
                title_positions.append((title_str, position))
            else:
                logging.warning(f"LLM提供的标题“{title_str}”在《{book_title}》的文本中未找到。")
        except TypeError: # 如果title_str不是字符串 (理论上不应发生)
             logging.warning(f"在《{book_title}》中查找标题时，标题类型无效 ({type(title_str)})：'{title_str}'")
             continue

    # 根据标题在文本中出现的位置排序
    sorted_title_positions = sorted(title_positions, key=lambda item: item[1])
    logging.info(f"在《{book_title}》文本中找到 {len(sorted_title_positions)} 个标题，并已按位置排序。")

    # 根据排序后的标题切分内容
    for i in range(len(sorted_title_positions)):
        current_title_text, current_title_start_pos = sorted_title_positions[i]
        next_title_start_pos = -1 # 默认为最后一个章节的结束位置（即文本末尾）

        if i + 1 < len(sorted_title_positions): # 如果不是最后一个标题
            next_title_start_pos = sorted_title_positions[i+1][1]
            # 章节内容从当前标题开始，到下一个标题之前
            section_content = full_book_content[current_title_start_pos : next_title_start_pos]
        else: # 如果是最后一个标题
            # 章节内容从当前标题开始，到文本末尾
            section_content = full_book_content[current_title_start_pos:]

        cleaned_section_content = section_content.strip() # 去除内容首尾空白
        cleaned_title = current_title_text.strip() # 去除标题首尾空白

        if cleaned_section_content: # 如果章节内容非空
            major_sections_data.append({
                "major_section_title": cleaned_title,
                "major_section_content": cleaned_section_content
            })
            logging.debug(f"为《{book_title}》添加了章节：“{cleaned_title}”（长度：{len(cleaned_section_content)}，开始：{current_title_start_pos}，结束：{next_title_start_pos}）")
        else:
            logging.warning(f"《{book_title}》中标题“{cleaned_title}”的内容在去除空白后为空。")

    if not major_sections_data: # 如果在所有尝试后，major_sections_data仍为空（例如，所有LLM标题都未在文本中找到，或找到后内容为空）
        logging.warning(f"未能从LLM的标题为《{book_title}》构建任何主要章节。将整本书视为一个单独的章节。")
        return [{"major_section_title": book_title, "major_section_content": full_book_content}]

    logging.info(f"《{book_title}》的章节切分完成。共创建 {len(major_sections_data)} 个主要章节。")
    return major_sections_data


def get_section_chunks(section_text: str, chunk_size: int = 3500, overlap: int = 400) -> list[str]:
    """
    将章节内容分割成适合LLM处理的、带有重叠的文本块。
    :param section_text: 章节的完整文本内容。
    :param chunk_size: 每个文本块的目标最大字符数。
    :param overlap: 连续文本块之间的重叠字符数，以保持上下文连贯。
    :return: 文本块列表。
    """
    if not section_text: # 如果章节文本为空，则返回空列表
        return []

    chunks = [] # 存储生成的文本块
    current_pos = 0 # 当前在文本中的处理位置
    text_len = len(section_text) # 文本总长度

    while current_pos < text_len:
        # 重叠部分在块的开始处 (例如，前一个块的最后 overlap 个字符)
        start_pos = max(0, current_pos - overlap)
        # 理想的块结束位置 (当前位置 + 块大小)
        end_pos = min(text_len, current_pos + chunk_size)

        actual_end_pos = end_pos # 实际的块结束位置，可能根据断点调整
        if end_pos < text_len: # 如果不是最后一个块，尝试寻找自然断点
            # 尝试在块的后半部分（例如，从80%处开始）寻找自然断点（段落或句子）
            # 这里简化为优先找双换行（通常表示段落结束），然后单换行（可能表示句子或小节结束）
            search_start_for_break = current_pos + int(chunk_size * 0.8) # 断点搜索的起始位置
            if end_pos > search_start_for_break: # 确保有足够的搜索区间
                # 优先找双换行符
                double_newline_idx = section_text.rfind('\n\n', search_start_for_break, end_pos)
                if double_newline_idx != -1:
                    actual_end_pos = double_newline_idx + 2 # 包含双换行符本身
                else:
                    # 其次找单换行符
                    single_newline_idx = section_text.rfind('\n', search_start_for_break, end_pos)
                    if single_newline_idx != -1:
                        actual_end_pos = single_newline_idx + 1 # 包含单换行符本身
                    # else: 如果找不到合适的断点，则保留 calculated end_pos (硬截断)

        chunk_content = section_text[start_pos:actual_end_pos] # 提取块内容
        chunks.append(chunk_content) # 添加到块列表
        
        # 更新下一个块的起始处理位置
        # current_pos 应该是下一个块主要内容（非重叠部分）的开始
        current_pos = actual_end_pos
        # 以下条件复杂且可能多余，主要用于防止在某些边界情况下actual_end_pos计算卡住导致的无限循环
        # 如果 actual_end_pos 将我们带到了 text_len，循环将在下一次迭代时终止。
        if current_pos >= text_len and len(chunks) > 0 and chunks[-1] != section_text[max(0, actual_end_pos - overlap):]:
             pass # 此处逻辑可能需要根据具体测试案例进一步审查和简化


        # 防止因重叠或切分逻辑问题导致的无限循环
        if start_pos == current_pos and current_pos < text_len: # 如果位置没有前进，但还没到文本末尾
            logging.warning(f"文本块处理位置未前进。强制移动 {chunk_size // 2} 个字符以避免无限循环。当前位置：{current_pos}，章节片段：{section_text[:200]}...") # 记录警告
            current_pos += chunk_size // 2 # 强制前进以避免死循环
            if current_pos >= text_len and chunks[-1] != section_text[start_pos:]: # 如果跳过了末尾
                 # 且最后一个块不是剩余部分
                 last_chunk_content = section_text[start_pos:]
                 if chunks[-1] != last_chunk_content: # 避免重复添加 (如果之前的逻辑已添加)
                    chunks.append(last_chunk_content)


    # 确保最后一个块包含到文本末尾的所有内容
    # 这个检查有点复杂，如果遇到问题可以简化
    if chunks and chunks[-1] != section_text[max(0, text_len - len(chunks[-1])):]: # 一个简化的检查：最后一个块的内容是否是文本的尾部
        # 更简单的启发式检查：最后一个块的末尾是否是整个文本的末尾（考虑到可能的微小差异或重复）
        if not chunks[-1].endswith(section_text[-(overlap if overlap > 0 else 10):]): # 检查最后一部分是否匹配
             # 此逻辑可能需要优化以确保尾部被捕获且无显著重复。
             # 目前，如果current_pos未到达末尾，意味着循环因start_pos == current_pos或其他条件退出。
             # 我们需要确保尾部被处理。
             # 尝试从最后一个块的预期开始位置（减去重叠）或实际的current_pos（如果更靠后）开始获取剩余文本
             final_start_guess = max(0, current_pos - overlap if chunks else 0) # 如果chunks为空，则从0开始
             if chunks:
                 # 尝试找到最后一个块在完整文本中的实际开始位置，然后从那里获取剩余部分
                 # 这是一个启发式的方法，可能不完美
                 try:
                     # 尝试从最后一个块的开头部分在完整文本中找到其位置
                     last_chunk_sample = chunks[-1][:100] # 取最后一个块的开头样本
                     search_from = max(0, text_len - len(chunks[-1]) - overlap - 100) # 限制搜索范围，避免从头搜索长文本
                     estimated_start_of_last_chunk = section_text.rfind(last_chunk_sample, search_from)
                     if estimated_start_of_last_chunk != -1:
                         final_start_guess = estimated_start_of_last_chunk + len(chunks[-1]) # 剩余部分的开始应该是最后一个块的结束
                     else: # 如果找不到样本，则退回到之前的猜测
                        final_start_guess = current_pos
                 except: # 防御性编程
                    final_start_guess = current_pos

             final_start = max(0, min(final_start_guess, text_len)) # 确保final_start在有效范围内

             if final_start < text_len: # 如果确实还有剩余文本
                remaining_text = section_text[final_start:]
                # 避免添加与最后一个块相同或只是其一小部分的剩余文本
                if remaining_text and (not chunks[-1].endswith(remaining_text)):
                     logging.debug(f"捕获到末尾遗漏的文本块，长度 {len(remaining_text)}")
                     chunks.append(remaining_text)


    # 移除可能产生的空字符串块
    return [c for c in chunks if c.strip()] # 同时去除仅含空白的块

# (确保 SEMANTIC_MICRO_PARAGRAPH_SPLIT_TEMPLATE 已从 .prompts 导入)
# (确保 TOC_GENERATION_PROMPT_TEMPLATE 已导入)

# perform_fine_grained_segmentation: 对单个章节内容进行细粒度的、基于语义的段落切分。
def perform_fine_grained_segmentation(
    document_title: str,               # 原始书籍/文档标题，用于LLM提示词上下文
    section_title: str,                # 当前处理章节的标题
    section_content: str,              # 章节的完整文本内容
    llm_interface: LLMInterface,       # LLM接口实例
    utils_clean_filename: callable     # clean_filename工具函数，用于处理子章节标题
) -> list[dict]:
    """
    对单个章节内容进行细粒度的、基于语义的段落切分。
    :param document_title: 原始文档标题，用于LLM提示词上下文。
    :param section_title: 当前章节的标题。
    :param section_content: 当前章节的完整文本内容。
    :param llm_interface: LLMInterface的实例。
    :param utils_clean_filename: clean_filename工具函数引用。
    :return: 一个字典列表，每个字典代表一个（可选的）子章节及其段落，
             格式为 [{"sub_section_title": "可选的子章节标题", "paragraphs": ["段落1文本", "段落2文本"]}, ...]。
             如果没有子章节标题，则 "sub_section_title" 键可能不存在或为None/空。
    """

    if not section_content.strip(): # 如果章节内容为空或仅有空白
        logging.warning(f"章节“{section_title}”（文档“{document_title}”）内容为空，跳过细粒度切分。")
        return []

    chunks = get_section_chunks(section_content) # 将章节内容切分为小块
    if not chunks: # 如果未能生成任何文本块
        logging.warning(f"未能为章节“{section_title}”（文档“{document_title}”）生成文本块，跳过细粒度切分。")
        return []

    all_structured_paragraphs = [] # 存储所有结构化段落的列表
    current_sub_section_title = None # 当前活动的子章节标题

    # Constants for sub-section title processing
    MIN_LEN_FOR_SHORTENING = 30         # Raw titles with length >= this (and <= MAX_LEN_BEFORE_DIRECT_DISCARD) will be attempted to be shortened
    MAX_LEN_BEFORE_DIRECT_DISCARD = 150 # Raw titles longer than this are discarded without attempting to shorten
    MAX_CLEANED_SUB_TITLE_LENGTH = 35   # Final max length for a cleaned title (either original short or shortened) to be accepted
    NO_SUITABLE_TITLE_MARKER = "不适合作标题" # Marker returned by LLM if shortening is not applicable

    logging.info(f"开始对章节“{section_title}”（文档“{document_title}”）进行细粒度段落切分（共 {len(chunks)} 个文本块）。")

    for i, chunk_text in enumerate(chunks): # 遍历每个文本块
        logging.debug(f"正在处理章节“{section_title}”的细粒度切分区块 {i + 1}/{len(chunks)}。")

        prompt = SEMANTIC_MICRO_PARAGRAPH_SPLIT_TEMPLATE.format(
            document_title=document_title,
            section_title=section_title,
            text_chunk_content=chunk_text
        )
        
        raw_llm_output = "" # 初始化LLM输出
        try:
            raw_llm_output = llm_interface.generate_text(prompt) # 调用LLM
            if raw_llm_output.startswith("错误："): # 检查LLM是否返回错误
                logging.warning(f"LLM在为文档“{document_title}” - 章节“{section_title}”的细粒度切分区块 {i+1} 返回错误：{raw_llm_output}")
                continue
        except Exception as e: # 捕获LLM调用过程中的其他异常
            logging.error(f"LLM在为文档“{document_title}” - 章节“{section_title}”的细粒度切分区块 {i+1} 调用失败：{e}", exc_info=True)
            continue

        if not isinstance(raw_llm_output, str) or not raw_llm_output.strip(): # 检查LLM输出是否为非空字符串
            logging.warning(f"LLM为章节“{section_title}”的区块 {i+1} 返回了空或非字符串响应：'{raw_llm_output}'。")
            continue

        raw_paragraphs = raw_llm_output.split("---PARAGRAPH_END---")

        chunk_paragraphs_buffer = [] # 存储当前块处理的段落，直到遇到新的子章节标题或块结束

        for para_text_raw in raw_paragraphs: # 遍历切分出的原始段落文本
            para_text = para_text_raw.strip() # 去除首尾空白

            if not para_text: # 跳过因额外换行或分隔符产生的空字符串
                continue
            
            if para_text.startswith("SUB-SECTION-TITLE:"):
                if chunk_paragraphs_buffer:
                    all_structured_paragraphs.append({
                        "sub_section_title": current_sub_section_title,
                        "paragraphs": list(chunk_paragraphs_buffer)
                    })
                    chunk_paragraphs_buffer.clear()

                extracted_text_after_marker = para_text.replace("SUB-SECTION-TITLE:", "").strip()
                new_sub_section_title_candidate = None # Stores the title that might become current_sub_section_title

                if not extracted_text_after_marker:
                    logging.debug(f"从 'SUB-SECTION-TITLE:' 标记后提取的原始子章节标题为空。忽略。文档《{document_title}》，章节“{section_title}”。")
                elif len(extracted_text_after_marker) > MAX_LEN_BEFORE_DIRECT_DISCARD:
                    logging.warning(f"原始提取的子章节标题过长（{len(extracted_text_after_marker)} > {MAX_LEN_BEFORE_DIRECT_DISCARD}字符），直接忽略。原始标题：'{extracted_text_after_marker[:100]}...'，文档《{document_title}》，章节“{section_title}”。")
                elif len(extracted_text_after_marker) >= MIN_LEN_FOR_SHORTENING:
                    logging.info(f"原始提取子章节标题长度为 {len(extracted_text_after_marker)}，在缩短尝试范围内。原文: '{extracted_text_after_marker[:100]}...'。文档《{document_title}》，章节“{section_title}”。")
                    shorten_prompt = SHORTEN_TITLE_PROMPT_TEMPLATE.format(long_title_candidate=extracted_text_after_marker)
                    try:
                        shortened_title = llm_interface.generate_text(shorten_prompt)
                        if shortened_title.startswith("错误："):
                            logging.warning(f"LLM在尝试缩短标题时返回错误: {shortened_title}。原始标题: '{extracted_text_after_marker[:100]}...'")
                        elif not shortened_title or shortened_title == NO_SUITABLE_TITLE_MARKER:
                            logging.info(f"LLM未能将标题 '{extracted_text_after_marker[:100]}...' 缩短或标记为不适用。")
                        else:
                            logging.info(f"LLM将标题 '{extracted_text_after_marker[:100]}...' 缩短为 '{shortened_title}'")
                            new_sub_section_title_candidate = shortened_title
                    except Exception as e_shorten:
                        logging.error(f"调用LLM缩短标题时发生异常: {e_shorten}。原始标题: '{extracted_text_after_marker[:100]}...'", exc_info=True)
                else: # 长度 < MIN_LEN_FOR_SHORTENING (且不为空)
                    # 作为短标题处理，直接成为候选标题，后续将进行清理和最终长度检查。
                    new_sub_section_title_candidate = extracted_text_after_marker

                # 处理候选标题（原始的短标题或缩短后的标题）
                if new_sub_section_title_candidate:
                    cleaned_title = utils_clean_filename(new_sub_section_title_candidate)
                    if not cleaned_title:
                        logging.debug(f"候选子章节标题 '{new_sub_section_title_candidate}' 清理后为空。忽略。文档《{document_title}》，章节“{section_title}”。")
                    elif len(cleaned_title) > MAX_CLEANED_SUB_TITLE_LENGTH:
                        logging.warning(f"候选子章节标题 '{new_sub_section_title_candidate}' 清理后为 '{cleaned_title}'，仍然过长（{len(cleaned_title)} > {MAX_CLEANED_SUB_TITLE_LENGTH}字符）。将忽略。文档《{document_title}》，章节“{section_title}”。")
                    else:
                        # Valid title found and processed
                        current_sub_section_title = cleaned_title
                        logging.debug(f"在章节“{section_title}”中识别并接受子章节标题：“{current_sub_section_title}”。(源: '{new_sub_section_title_candidate}')")
                # If new_sub_section_title_candidate is None (due to being too long initially, or shortening failed, or original short title was empty),
                # current_sub_section_title remains unchanged from previous iteration / or stays None.
                # This ensures paragraphs are appended to the correct (previous or main) section.
            else: # 是普通段落内容
                chunk_paragraphs_buffer.append(para_text)
        
        # 处理当前文本块末尾剩余的段落（属于最后一个子章节标题或主章节）
        if chunk_paragraphs_buffer:
            all_structured_paragraphs.append({
                "sub_section_title": current_sub_section_title, # 当前活动的子标题
                "paragraphs": list(chunk_paragraphs_buffer)
            })
            chunk_paragraphs_buffer.clear() # 清空缓冲区（良好习惯）

    # 合并逻辑：如果连续的条目具有相同的 sub_section_title (包括 None), 则合并它们的 paragraphs 列表。
    # 这可以处理一个子章节的内容跨越多个LLM输出块（由get_section_chunks分割）的情况。
    if not all_structured_paragraphs: # 如果在处理所有区块后仍没有结构化段落
        logging.warning(f"在处理所有区块后，未能为章节“{section_title}”（文档“{document_title}”）生成任何结构化段落。")
        return []

    merged_output = [] # 存储合并后的输出
    
    # 第一个元素直接添加（如果存在）
    # 注意：这里的current_sub_section_title是最后一个chunk的最后一个sub_section_title，不能作为全局的初始值
    # 我们需要从all_structured_paragraphs的第一个元素开始推断
    
    # 初始化第一个合并条目
    # (之前的合并逻辑注释被移除，因为当前逻辑是正确的)
    if not all_structured_paragraphs: # 再次检查，以防万一 (防御性编程)
        logging.warning(f"在处理所有区块后，未能为章节“{section_title}”（文档“{document_title}”）生成任何结构化段落。") # 重复警告，但逻辑上应在此处返回
        return []

    # merged_output = [] # 已在上方初始化
    if all_structured_paragraphs: # 确保列表非空
        merged_output.append(dict(all_structured_paragraphs[0])) # 使用dict()创建副本，避免修改原始列表中的字典
        for i in range(1, len(all_structured_paragraphs)): # 从第二个元素开始遍历
            current_seg_title = all_structured_paragraphs[i].get("sub_section_title")
            last_merged_title = merged_output[-1].get("sub_section_title") # 获取已合并输出中最后一个条目的子标题

            if current_seg_title == last_merged_title: # 如果当前条目的子标题与上一个相同
                merged_output[-1]["paragraphs"].extend(all_structured_paragraphs[i].get("paragraphs", [])) # 合并段落列表
            else: # 如果子标题不同，则添加新的条目
                merged_output.append(dict(all_structured_paragraphs[i])) # 创建副本
    else:
        return [] # 如果all_structured_paragraphs为空，则返回空列表


    total_paras = sum(len(s.get('paragraphs',[])) for s in merged_output) # 计算总段落数
    logging.info(f"章节“{section_title}”（文档“{document_title}”）的细粒度段落切分完成。共生成 {total_paras} 个段落，分布在 {len(merged_output)} 个内容组中。")
    return merged_output

# get_author_from_book_title_heuristic: 从书名中启发式地提取作者。
def get_author_from_book_title_heuristic(book_title: str) -> str:
    """
    启发式方法从书名中提取作者。
    示例: "黄帝内经" -> "黄帝"
    :param book_title: 书名。
    :return: 提取的作者名，如果无法确定则返回"未知作者"。
    """
    if "黄帝内经" in book_title:
        return "黄帝"
    if "伤寒杂病论" in book_title or "伤寒论" in book_title or "金匮要略" in book_title:
        return "张仲景"
    # 可以根据需要添加更多规则，例如基于正则表达式的模式匹配等。
    return "未知作者" # 默认返回"未知作者"

# process_tcm_books: 处理所有中医典籍文件的主函数。
def process_tcm_books(llm_interface: LLMInterface):
    """
    处理所有中医典籍文件。
    从原始数据目录读取，进行主要章节切分和细粒度段落切分，然后将处理后的内容存入处理后数据目录。
    :param llm_interface: LLMInterface的实例，用于与大语言模型交互。
    """
    
    ensure_directory_exists(PROCESSED_TCM_BOOKS_DIR) # 确保输出目录存在
    logging.info(f"开始处理中医典籍，源目录: {RAW_TCM_BOOKS_DIR}, 输出目录: {PROCESSED_TCM_BOOKS_DIR}")
    logging.info(f"TOC 生成参数: MAX_CHARS_FOR_TOC_PROMPT={MAX_CHARS_FOR_TOC_PROMPT}, TOC_CHUNK_OVERLAP={TOC_CHUNK_OVERLAP}")

    if not os.path.exists(RAW_TCM_BOOKS_DIR): # 检查原始数据目录是否存在
        logging.error(f"错误: 原始数据目录 {RAW_TCM_BOOKS_DIR} 不存在。请检查路径或数据。")
        return

    for filename in os.listdir(RAW_TCM_BOOKS_DIR): # 遍历目录中的所有文件
        if not filename.endswith(".txt"): # 只处理 .txt 文件
            continue # 跳过非txt文件

        book_file_path = os.path.join(RAW_TCM_BOOKS_DIR, filename) # 获取书籍文件的完整路径
        book_title_original = os.path.splitext(filename)[0] # 从文件名提取原始书名 (去除.txt后缀)

        try: # 为处理单本书籍设置主异常捕获块
            author = get_author_from_book_title_heuristic(book_title_original) # 提取作者信息
            logging.info(f"正在处理书籍: {book_title_original} (作者: {author})")

            book_content = read_text_file(book_file_path) # 读取书籍内容
            if book_content is None: # 如果读取失败 (read_text_file 返回 None)
                logging.error(f"未能读取书籍内容或文件为空: {book_file_path}. 跳过此书。")
                continue
            if not book_content.strip(): # 如果内容仅包含空白字符
                 logging.warning(f"书籍内容为空 (仅包含空白字符): {book_file_path}. 跳过此书。")
                 continue

            # 清理书名和作者名以用于创建安全的文件夹名
            safe_book_title = clean_filename(book_title_original)
            safe_author = clean_filename(author)
            # 构建特定书籍的输出目录路径, 格式: <处理后书籍目录>/<书名安全版>_特性_<作者安全版>
            book_output_dir = os.path.join(PROCESSED_TCM_BOOKS_DIR, f"{safe_book_title}_特性_{safe_author}")
            ensure_directory_exists(book_output_dir) # 确保该目录存在
            logging.info(f"输出目录已确认/创建: {book_output_dir}")

            # 检查书籍是否已被处理 (通过检查输出目录是否非空)
            if os.path.exists(book_output_dir) and os.listdir(book_output_dir):
                logging.warning(f"书籍 《{book_title_original}》 似乎已经处理过 (输出目录非空)，跳过。")
                continue

            # 阶段1: 调用 segment_book_into_major_sections 进行主要章节切分
            logging.info(f"阶段1: 开始为《{book_title_original}》调用 segment_book_into_major_sections...")
            coarse_sections_data = segment_book_into_major_sections(
                book_title=book_title_original,
                full_book_content=book_content,
                llm_interface=llm_interface,
                max_chars_for_toc_prompt=MAX_CHARS_FOR_TOC_PROMPT,
                toc_chunk_overlap=TOC_CHUNK_OVERLAP
            )

            coarse_sections = [] # 存储粗粒度章节的列表，每个元素是 (标题, 内容) 的元组
            if coarse_sections_data:
                for section_data in coarse_sections_data:
                    title = section_data.get("major_section_title", book_title_original) # 获取主要章节标题，若无则用原书名
                    content = section_data.get("major_section_content", "") # 获取主要章节内容
                    if content: # 仅当内容非空时添加
                        coarse_sections.append((title, content))

            if not coarse_sections: # 如果主要章节切分未返回有效章节 (例如LLM未能提取标题或所有内容为空)
                logging.warning(f"segment_book_into_major_sections 未能为《{book_title_original}》返回可处理的章节。将整本书视为一个章节。")
                coarse_sections = [(book_title_original, book_content)] # 将整本书作为一个章节处理

            logging.info(f"阶段1完成。为《{book_title_original}》找到 {len(coarse_sections)} 个主要章节。")

            # 遍历每个主要章节进行细粒度处理
            for section_idx, (section_title, section_content_text) in enumerate(coarse_sections):
                logging.info(f"正在处理主要章节 {section_idx + 1}/{len(coarse_sections)}: “{section_title}” (长度: {len(section_content_text)} 字符)")
                
                # 阶段2: 对每个主要章节执行细粒度段落切分
                logging.info(f"阶段2: 开始对书籍《{book_title_original}》的章节“{section_title}”进行细粒度切分...")
                structured_paragraphs_data = perform_fine_grained_segmentation(
                    document_title=book_title_original,    # 原始书名，用于LLM提示上下文
                    section_title=section_title,           # 当前主要章节的标题
                    section_content=section_content_text,  # 当前主要章节的内容
                    llm_interface=llm_interface,
                    utils_clean_filename=clean_filename 
                )

                if not structured_paragraphs_data: # 如果未能切分出段落
                    logging.warning(f"未能从书籍《{book_title_original}》的章节“{section_title}”中切分出细粒度段落。")
                    continue # 继续处理下一个主要章节

                # 阶段3: 文件命名、目录结构和保存
                logging.info(f"阶段3: 开始保存书籍《{book_title_original}》章节“{section_title}”的细粒度段落...")
                
                filename_counters = {} # 文件名计数器，用于处理可能因清理后同名的子章节文件
                total_paragraphs_saved_in_section = 0 # 当前章节已保存的总段落数

                for group_idx, para_group in enumerate(structured_paragraphs_data): # 遍历每个段落组 (可能带子章节标题)
                    sub_section_title_str = para_group.get("sub_section_title") # 获取子章节标题 (可能为空)
                    paragraphs_list = para_group.get("paragraphs", []) # 获取段落列表

                    if not paragraphs_list: # 如果该组没有段落
                        logging.debug(f"章节“{section_title}”的段落组 {group_idx} 没有段落。跳过。")
                        continue

                    safe_main_section_title = clean_filename(section_title) # 清理主章节标题以用于文件名
                    if not safe_main_section_title: # 如果清理后为空 (不太可能，但防御性)
                        safe_main_section_title = "未命名主章节"

                    # 构建计数器的键 (主章节标题 或 主章节标题-子章节标题)，以确保段落编号在正确范围内唯一
                    counter_key = f"{safe_main_section_title}-{sub_section_title_str}" if sub_section_title_str else safe_main_section_title

                    for para_content in paragraphs_list: # 遍历组内每个段落
                        current_paragraph_number = filename_counters.get(counter_key, 0) + 1 # 获取并更新段落编号
                        filename_counters[counter_key] = current_paragraph_number

                        # 构建输出文件名
                        if sub_section_title_str: # 如果有子章节标题
                            output_filename = f"{safe_main_section_title}-{sub_section_title_str}_{current_paragraph_number}.txt"
                        else: # 如果没有子章节标题 (直接属于主章节)
                            output_filename = f"{safe_main_section_title}_{current_paragraph_number}.txt"
                        
                        output_file_path = os.path.join(book_output_dir, output_filename) # 构建完整输出路径
                        try:
                            write_text_file(output_file_path, para_content) # 写入文件
                            total_paragraphs_saved_in_section += 1
                        except IOError as e: # 捕获文件写入错误
                            logging.error(f"无法将段落写入书籍《{book_title_original}》的文件 {output_file_path}：{e}", exc_info=True)
                
                logging.info(f"书籍《{book_title_original}》的章节“{section_title}”：已保存 {total_paragraphs_saved_in_section} 个细粒度段落。")

        except Exception as e: # 捕获处理单本书籍时的任何其他未预料异常
            logging.error(f"处理书籍 {filename} 失败，原因：{e}", exc_info=True)
            # 继续处理下一本书
            
    logging.info("所有中医典籍处理完毕。")

if __name__ == '__main__':
    logging.info("初始化LLM接口...")
    try:
        llm_api = LLMInterface() # 实例化LLM接口
    except Exception as e:
        logging.error(f"实例化LLMInterface时发生错误: {e}", exc_info=True)
        logging.error("请确保LLMInterface类已正确定义并且其依赖项可用。")
        exit(1) # 退出脚本，因为没有LLM接口无法继续
        
    logging.info("开始执行中医典籍处理脚本...")
    process_tcm_books(llm_api)
