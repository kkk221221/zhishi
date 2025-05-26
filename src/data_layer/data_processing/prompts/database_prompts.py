# src/data_layer/data_processing/prompts/database_prompts.py
# 数据库内容处理相关提示词

DATABASE_TEXT_CHUNK_TEMPLATE = """
请将以下文本内容分割成适合知识库检索的语义连贯的文本块 (chunks)。
每个文本块应尽可能自包含，并且长度不超过200字。

原始文本内容：
{text_content}
"""
