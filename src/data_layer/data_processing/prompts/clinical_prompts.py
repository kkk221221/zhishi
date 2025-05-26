# src/data_layer/data_processing/prompts/clinical_prompts.py
# 临床案例处理相关提示词

CLINICAL_CASE_STANDARDIZATION_TEMPLATE = """
请将以下临床案例内容进行简单标准化处理。目标是将其整理为包含“患者信息”、“主诉”、“诊断”、“治疗方案”等标准段落的格式。
如果原文中某些信息缺失，请在对应段落注明“信息缺失”。请勿臆断或添加原文未提及的信息。

原始案例内容：
{case_content}
"""
