# src/data_layer/data_processing/prompts/clinical_prompts.py
# 临床案例处理相关提示词

# CLINICAL_CASE_STANDARDIZATION_TEMPLATE = """
# 请将以下临床案例内容进行简单标准化处理。目标是将其整理为包含“患者信息”、“主诉”、“诊断”、“治疗方案”等标准段落的格式。
# 如果原文中某些信息缺失，请在对应段落注明“信息缺失”。请勿臆断或添加原文未提及的信息。

# 原始案例内容：
# {case_content}
# """

CLINICAL_CASE_JSON_EXTRACTION_TEMPLATE = """
你的任务是仔细阅读以下提供的临床案例内容，并从中提取关键信息，按照指定的JSON格式进行结构化输出。
请确保输出的是一个【完整且语法正确】的JSON对象。

JSON结构说明如下：
{
  "patient_info": { // 患者基本信息
    "name": "患者姓名 (字符串，如果缺失则为 null)",
    "gender": "性别 (字符串，例如 男, 女, 未知，如果缺失则为 null)",
    "age": "年龄 (字符串，例如 35岁, 5个月，如果缺失则为 null)",
    "occupation": "职业 (字符串，如果缺失则为 null)"
  },
  "consultation_date": "就诊日期 (字符串 YYYY-MM-DD，如果格式不符或缺失则为 null)",
  "chief_complaint": "主诉 (字符串，如果缺失则为 null)",
  "history_of_present_illness": "现病史 (字符串，详细描述，如果缺失则为 null)",
  "past_history": "既往史 (字符串，包括重要疾病和手术史，如果缺失则为 null)",
  "personal_history": "个人史 (字符串，如吸烟、饮酒史，如果缺失则为 null)",
  "family_history": "家族史 (字符串，家族遗传病史，如果缺失则为 null)",
  "physical_examination": "体格检查结果 (字符串，如果缺失则为 null)",
  "auxiliary_examination": "辅助检查结果 (字符串，如实验室检测、影像学报告，如果缺失则为 null)",
  "tcm_diagnosis": { // 中医诊断信息
    "disease_name": "中医病名 (字符串，如果缺失则为 null)",
    "syndrome_pattern": "中医证型 (字符串，如果缺失则为 null)"
  },
  "western_medicine_diagnosis": "西医诊断 (字符串，如果缺失则为 null)",
  "treatment_principle": "治法/治疗原则 (字符串，如果缺失则为 null)",
  "treatment_plan": { // 详细治疗方案
    "chinese_herbal_medicine": "中药处方详情 (字符串，包含药材、剂量、用法，如果缺失则为 null)",
    "acupuncture_moxibustion": "针灸治疗详情 (字符串，包含穴位、操作方法，如果缺失则为 null)",
    "other_treatments": "其他治疗方法 (字符串，如果缺失则为 null)"
  },
  "treatment_outcome": "治疗结果及随访情况 (字符串，如果缺失则为 null)",
  "notes_and_analysis": "病案总结、分析或医生心得 (字符串，如果缺失则为 null)"
}

请注意：
- 严格按照上述JSON结构输出。
- 如果原文中某项信息明确不存在或未提及，请在该字段的值使用 `null` (JSON null类型) 或空字符串 ""。对于嵌套对象中的字段，如果整个对象的信息都缺失，可以使该对象值为 `null`，或者对象内所有字段值为 `null` / ""。请优先使用 `null` 表示缺失。
- 确保所有字符串值都使用双引号。
- 不要输出任何JSON对象之外的额外解释、注释或任何其他文本。输出结果应该可以直接通过JSON解析器解析。

原始案例内容：
---
{case_content}
---

输出的JSON对象：
"""
