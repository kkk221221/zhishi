# src/data_layer/data_processing/prompts/tcm_prompts.py
# 中医典籍处理相关提示词

TCM_CHAPTER_PARAGRAPH_SPLIT_TEMPLATE = """
请将以下《{book_title}》中的章节“{chapter_title}”内容，依据语义连贯性和上下文逻辑，智能划分为若干段落。
确保每个段落主题集中，避免过长或过短的段落。请直接输出划分后的段落内容，段落之间用空行分隔。

原始章节内容：
{chapter_content}
"""
