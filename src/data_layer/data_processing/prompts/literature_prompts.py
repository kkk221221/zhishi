# src/data_layer/data_processing/prompts/literature_prompts.py
# 现代文学作品处理相关提示词

LITERATURE_SUMMARY_TEMPLATE = """
请为以下现代文学作品《{title}》的片段生成一个简洁的摘要，突出主要情节和核心思想。

作品片段：
{content_fragment}
"""
