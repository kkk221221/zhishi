# hexin/chaxun_yinqing.py

from . import crud_caozuo # 从当前包（hexin）导入 crud_caozuo

def find_herbs_by_property(property_value: str) -> list[dict]:
    # """
    # 根据功效查找药材。
    #
    # Args:
    #     property_value (str): 要查询的功效值 (例如 "补气", "活血化瘀")。
    #                           匹配时会忽略大小写。
    #
    # Returns:
    #     list[dict]: 包含匹配药材信息的字典列表。如果找不到则返回空列表。
    # """
    if not isinstance(property_value, str) or not property_value.strip():
        # print("信息：功效值无效或为空，返回空列表。") # 可选的日志
        return []

    all_herbs = crud_caozuo.get_all_herbs()
    if not all_herbs:
        return []

    matching_herbs = []
    search_prop_lower = property_value.strip().lower() # 查询条件转为小写并去除首尾空格

    for herb in all_herbs:
        # 确保药材数据中有 'properties' 键，并且它是一个列表
        if "properties" in herb and isinstance(herb["properties"], list):
            # 遍历药材的每个功效，进行不区分大小写的比较
            for prop in herb["properties"]:
                if isinstance(prop, str) and prop.lower() == search_prop_lower:
                    matching_herbs.append(herb)
                    break # 找到匹配功效后，无需再检查此药材的其他功效
    
    return matching_herbs

def find_symptoms_by_keyword(keyword: str) -> list[dict]:
    # """
    # 根据关键词搜索症状的名称或描述。

    # Args:
    #     keyword (str): 要搜索的关键词。匹配时会忽略大小写。

    # Returns:
    #     list[dict]: 包含匹配症状信息的字典列表。如果找不到则返回空列表。
    # """
    if not isinstance(keyword, str) or not keyword.strip():
        # print("信息：关键词无效或为空，返回空列表。") # 可选的日志
        return []

    all_symptoms = crud_caozuo.get_all_symptoms()
    if not all_symptoms:
        return []

    matching_symptoms = []
    search_keyword_lower = keyword.strip().lower() # 查询关键词转为小写并去除首尾空格
    
    # 用于记录已添加的症状ID，避免重复添加
    added_symptom_ids = set()

    for symptom in all_symptoms:
        matched = False
        # 检查名称字段
        if "name" in symptom and isinstance(symptom["name"], str):
            if search_keyword_lower in symptom["name"].lower():
                matched = True
        
        # 如果名称未匹配，则检查描述字段
        if not matched and "description" in symptom and isinstance(symptom["description"], str):
            if search_keyword_lower in symptom["description"].lower():
                matched = True
        
        if matched and symptom.get("id") not in added_symptom_ids:
            matching_symptoms.append(symptom)
            if "id" in symptom: # 确保ID存在才添加到set中
                 added_symptom_ids.add(symptom["id"])
            
    return matching_symptoms

def get_related_symptoms_for_herb(herb_id: str) -> list[dict]:
    # """
    # 根据药材ID，从关系文件中查找相关的症状。
    # 假设关系文件中的每条记录至少包含 'herb_id' 和 'symptom_id'。

    # Args:
    #     herb_id (str): 要查询的药材的ID。

    # Returns:
    #     list[dict]: 包含相关症状详细信息的字典列表。
    #                 如果药材ID无效、没有关系或关系中的症状ID无效，则返回空列表。
    # """
    if not isinstance(herb_id, str) or not herb_id.strip():
        # print("信息：药材ID无效或为空，返回空列表。") # 可选日志
        return []

    # 检查药材是否存在 (可选，但推荐，以避免无效查询)
    herb_exists = crud_caozuo.get_herb_by_id(herb_id)
    if not herb_exists:
        # print(f"信息：ID为 '{herb_id}' 的药材不存在。") # 可选日志
        return []

    all_relationships = crud_caozuo.get_all_entities("relationship") # 使用通用函数获取关系实体
    if not all_relationships:
        # print(f"信息：系统中没有找到任何关系数据。") # 可选日志
        return []

    related_symptom_ids = set() # 使用集合避免重复的症状ID
    for rel in all_relationships:
        # 确保关系字典中存在 'herb_id' 和 'symptom_id' 键
        if "herb_id" in rel and rel["herb_id"] == herb_id and "symptom_id" in rel:
            if isinstance(rel["symptom_id"], str) and rel["symptom_id"].strip():
                related_symptom_ids.add(rel["symptom_id"].strip())

    if not related_symptom_ids:
        # print(f"信息：未找到药材ID '{herb_id}' 的相关症状关系。") # 可选日志
        return []

    related_symptoms_details = []
    for symptom_id in related_symptom_ids:
        symptom_detail = crud_caozuo.get_symptom_by_id(symptom_id)
        if symptom_detail:
            related_symptoms_details.append(symptom_detail)
        else:
            # 记录在关系中找到但无法获取详情的症状ID
            print(f"警告：在关系中找到症状ID '{symptom_id}' (关联药材 '{herb_id}'), 但无法获取其详细信息。")
            
    return related_symptoms_details

def get_related_herbs_for_symptom(symptom_id: str) -> list[dict]:
    # """
    # 根据症状ID，从关系文件中查找相关的药材。
    # 假设关系文件中的每条记录至少包含 'herb_id' 和 'symptom_id'。

    # Args:
    #     symptom_id (str): 要查询的症状的ID。

    # Returns:
    #     list[dict]: 包含相关药材详细信息的字典列表。
    #                 如果症状ID无效、没有关系或关系中的药材ID无效，则返回空列表。
    # """
    if not isinstance(symptom_id, str) or not symptom_id.strip():
        # print("信息：症状ID无效或为空，返回空列表。") # 可选日志
        return []

    # 检查症状是否存在 (可选，但推荐)
    symptom_exists = crud_caozuo.get_symptom_by_id(symptom_id)
    if not symptom_exists:
        # print(f"信息：ID为 '{symptom_id}' 的症状不存在。") # 可选日志
        return []

    all_relationships = crud_caozuo.get_all_entities("relationship")
    if not all_relationships:
        # print(f"信息：系统中没有找到任何关系数据。") # 可选日志
        return []

    related_herb_ids = set() # 使用集合避免重复的药材ID
    for rel in all_relationships:
        # 确保关系字典中存在 'symptom_id' 和 'herb_id' 键
        if "symptom_id" in rel and rel["symptom_id"] == symptom_id and "herb_id" in rel:
            if isinstance(rel["herb_id"], str) and rel["herb_id"].strip():
                related_herb_ids.add(rel["herb_id"].strip())

    if not related_herb_ids:
        # print(f"信息：未找到症状ID '{symptom_id}' 的相关药材关系。") # 可选日志
        return []

    related_herbs_details = []
    for herb_id in related_herb_ids:
        herb_detail = crud_caozuo.get_herb_by_id(herb_id)
        if herb_detail:
            related_herbs_details.append(herb_detail)
        else:
            # 记录在关系中找到但无法获取详情的药材ID
            print(f"警告：在关系中找到药材ID '{herb_id}' (关联症状 '{symptom_id}'), 但无法获取其详细信息。")
            
    return related_herbs_details

# 示例用法 (可选, 可移除或注释掉)
if __name__ == '__main__':
    # --- 设置测试数据 ---
    from ..peizhi import shezhi
    from . import wenjian_caozuo
    from . import id_shengchengqi
    from . import shuju_jiexi
    import os

    # --- Global Setup for Examples ---
    id_shengchengqi._counters.clear() # Clear all ID counters at the beginning
    
    # Ensure parent directory for data files exists
    base_data_dir = os.path.dirname(shezhi.YAOCAI_FILE) # Assuming all data files are in subdirs of this
    if not os.path.exists(base_data_dir):
        os.makedirs(base_data_dir)
        print(f"创建基础数据目录: {base_data_dir}")

    # Ensure specific subdirectories exist as well
    for entity_type_config in crud_caozuo.ENTITY_CONFIG.values():
        entity_file_path = entity_type_config["file"]
        entity_dir = os.path.dirname(entity_file_path)
        if not os.path.exists(entity_dir):
            os.makedirs(entity_dir)
            print(f"创建子目录: {entity_dir}")


    # --- Herb Data Setup ---
    mock_herbs_data_for_example = [
        {"name": "人参", "properties": ["补气", "健脾"], "id": id_shengchengqi.generate_id(shezhi.YAOCAI_PREFIX)}, # YC001
        {"name": "当归", "properties": ["补血", "调经"], "id": id_shengchengqi.generate_id(shezhi.YAOCAI_PREFIX)}, # YC002
        {"name": "黄芪", "properties": ["补气", "固表"], "id": id_shengchengqi.generate_id(shezhi.YAOCAI_PREFIX)}, # YC003
        {"name": "枸杞", "properties": ["补肾", "明目", "补气"], "id": id_shengchengqi.generate_id(shezhi.YAOCAI_PREFIX)}  # YC004
    ]
    herb_lines_to_write = [shuju_jiexi.format_entity_for_txt(h) for h in mock_herbs_data_for_example if h]
    wenjian_caozuo.rewrite_file(shezhi.YAOCAI_FILE, herb_lines_to_write)
    print(f"已将模拟药材数据写入: {shezhi.YAOCAI_FILE}")

    print("\n--- 测试 find_herbs_by_property ---")
    property_to_find = "补气"
    herbs_with_property = find_herbs_by_property(property_to_find)
    print(f"具有 '{property_to_find}' 功效的药材 ({len(herbs_with_property)}):")
    for herb in herbs_with_property: print(f"  - {herb.get('name')}: {herb.get('properties')}")
    property_to_find_case = "补血" 
    herbs_with_property_case = find_herbs_by_property(property_to_find_case)
    print(f"具有 '{property_to_find_case}' 功效的药材 ({len(herbs_with_property_case)}):")
    for herb in herbs_with_property_case: print(f"  - {herb.get('name')}: {herb.get('properties')}")
    property_not_found = "祛湿"
    herbs_not_found = find_herbs_by_property(property_not_found)
    print(f"具有 '{property_not_found}' 功效的药材 ({len(herbs_not_found)}):") 
    if not herbs_not_found: print(f"  （未找到）")
    empty_property = "  "
    herbs_empty_prop = find_herbs_by_property(empty_property)
    print(f"查询功效为空字符串或仅空格时 ({len(herbs_empty_prop)}):") 
    if not herbs_empty_prop: print(f"  （未找到）")

    # --- Symptom Data Setup ---
    mock_symptoms_data = [
        {"name": "头痛", "description": "一种常见的头部不适症状。", "id": id_shengchengqi.generate_id(shezhi.ZHENGZHUANG_PREFIX)}, # ZZ001
        {"name": "咳嗽", "description": "喉咙受到刺激，引发的反射性动作，可能伴有咳痰。", "id": id_shengchengqi.generate_id(shezhi.ZHENGZHUANG_PREFIX)}, # ZZ002
        {"name": "鼻塞", "description": "感冒或鼻炎引起的常见症状，呼吸不畅。", "id": id_shengchengqi.generate_id(shezhi.ZHENGZHUANG_PREFIX)}, # ZZ003
        {"name": "食欲不振", "description": "不想吃饭，通常是脾胃功能不佳的表现。食欲差。", "id": id_shengchengqi.generate_id(shezhi.ZHENGZHUANG_PREFIX)} # ZZ004
    ]
    symptom_lines_to_write = [shuju_jiexi.format_entity_for_txt(s) for s in mock_symptoms_data if s]
    wenjian_caozuo.rewrite_file(shezhi.ZHENGZHUANG_FILE, symptom_lines_to_write)
    print(f"\n已将模拟症状数据写入: {shezhi.ZHENGZHUANG_FILE}")

    print("\n--- 测试 find_symptoms_by_keyword ---")
    keyword_to_find = "头痛"
    symptoms_found = find_symptoms_by_keyword(keyword_to_find)
    print(f"包含关键词 '{keyword_to_find}' 的症状 ({len(symptoms_found)}):")
    for s in symptoms_found: print(f"  - ID: {s.get('id')}, Name: {s.get('name')}, Desc: {s.get('description')}")
    keyword_in_desc = "常见症状"
    symptoms_desc_found = find_symptoms_by_keyword(keyword_in_desc)
    print(f"描述中包含 '{keyword_in_desc}' 的症状 ({len(symptoms_desc_found)}):")
    for s in symptoms_desc_found: print(f"  - ID: {s.get('id')}, Name: {s.get('name')}, Desc: {s.get('description')}")
    keyword_in_name_and_desc = "食欲" 
    symptoms_name_desc_found = find_symptoms_by_keyword(keyword_in_name_and_desc)
    print(f"名称或描述中包含 '{keyword_in_name_and_desc}' 的症状 ({len(symptoms_name_desc_found)}):")
    for s in symptoms_name_desc_found: print(f"  - ID: {s.get('id')}, Name: {s.get('name')}, Desc: {s.get('description')}")
    keyword_not_found = "发烧"
    symptoms_not_found = find_symptoms_by_keyword(keyword_not_found)
    print(f"包含关键词 '{keyword_not_found}' 的症状 ({len(symptoms_not_found)}):")
    if not symptoms_not_found: print("  （未找到）")
    empty_keyword = " "
    symptoms_empty_keyword = find_symptoms_by_keyword(empty_keyword)
    print(f"查询关键词为空或仅空格时 ({len(symptoms_empty_keyword)}):")
    if not symptoms_empty_keyword: print("  （未找到）")
    
    # --- Relationship Data Setup ---
    mock_relationships_data = [
        {"id": id_shengchengqi.generate_id(shezhi.GUANXI_PREFIX), "herb_id": "YC001", "symptom_id": "ZZ001", "relation_type": "主治"}, # 人参 -> 头痛
        {"id": id_shengchengqi.generate_id(shezhi.GUANXI_PREFIX), "herb_id": "YC001", "symptom_id": "ZZ004", "relation_type": "改善"}, # 人参 -> 食欲不振
        {"id": id_shengchengqi.generate_id(shezhi.GUANXI_PREFIX), "herb_id": "YC002", "symptom_id": "ZZ001", "relation_type": "可用于"}, # 当归 -> 头痛
        {"id": id_shengchengqi.generate_id(shezhi.GUANXI_PREFIX), "herb_id": "YC003", "symptom_id": "ZZ003", "relation_type": "缓解"}, # 黄芪 -> 鼻塞
        {"id": id_shengchengqi.generate_id(shezhi.GUANXI_PREFIX), "herb_id": "YC001", "symptom_id": "ZZ002", "relation_type": "可用于"}, # 人参 -> 咳嗽
        {"id": id_shengchengqi.generate_id(shezhi.GUANXI_PREFIX), "herb_id": "YC001", "symptom_id": "ZZ999", "relation_type": "主治"},  # 人参 -> 不存在的症状ID
        {"id": id_shengchengqi.generate_id(shezhi.GUANXI_PREFIX), "herb_id": "YC999", "symptom_id": "ZZ001", "relation_type": "主治"}  # 不存在的药材ID -> 头痛
    ]
    relationship_lines_to_write = [shuju_jiexi.format_entity_for_txt(r) for r in mock_relationships_data if r]
    wenjian_caozuo.rewrite_file(shezhi.YAOCAI_ZHENGZHUANG_GUANLIAN_FILE, relationship_lines_to_write)
    print(f"\n已将模拟关系数据写入: {shezhi.YAOCAI_ZHENGZHUANG_GUANLIAN_FILE}")

    print("\n--- 测试 get_related_symptoms_for_herb ---")
    herb_id_to_query_1 = "YC001" # 人参
    related_symptoms_1 = get_related_symptoms_for_herb(herb_id_to_query_1)
    print(f"药材ID '{herb_id_to_query_1}' (人参) 的相关症状 ({len(related_symptoms_1)}):")
    for s in related_symptoms_1: print(f"  - {s.get('name')} (ID: {s.get('id')})") # Expect: ZZ001, ZZ004, ZZ002. ZZ999 warning
    herb_id_to_query_2 = "YC002" # 当归
    related_symptoms_2 = get_related_symptoms_for_herb(herb_id_to_query_2)
    print(f"药材ID '{herb_id_to_query_2}' (当归) 的相关症状 ({len(related_symptoms_2)}):")
    for s in related_symptoms_2: print(f"  - {s.get('name')} (ID: {s.get('id')})") # Expected: ZZ001
    herb_id_no_relations = "YC004" 
    related_symptoms_none = get_related_symptoms_for_herb(herb_id_no_relations)
    print(f"药材ID '{herb_id_no_relations}' (枸杞) 的相关症状 ({len(related_symptoms_none)}):")
    if not related_symptoms_none: print("  （未找到相关症状）")
    non_existent_herb_id = "YC999"
    related_symptoms_invalid_herb = get_related_symptoms_for_herb(non_existent_herb_id)
    print(f"不存在的药材ID '{non_existent_herb_id}' 的相关症状 ({len(related_symptoms_invalid_herb)}):")
    if not related_symptoms_invalid_herb: print("  （未找到相关症状或药材不存在）")
    empty_herb_id = " "
    related_symptoms_empty_id = get_related_symptoms_for_herb(empty_herb_id)
    print(f"空的药材ID 的相关症状 ({len(related_symptoms_empty_id)}):")
    if not related_symptoms_empty_id: print("  （药材ID无效）")

    print("\n--- 测试 get_related_herbs_for_symptom ---")
    symptom_id_to_query_1 = "ZZ001" # 头痛
    related_herbs_1 = get_related_herbs_for_symptom(symptom_id_to_query_1)
    print(f"症状ID '{symptom_id_to_query_1}' (头痛) 的相关药材 ({len(related_herbs_1)}):")
    for herb in related_herbs_1: # Expect: YC001, YC002. YC999 warning
        print(f"  - {herb.get('name')} (ID: {herb.get('id')})")

    symptom_id_to_query_2 = "ZZ002" # 咳嗽
    related_herbs_2 = get_related_herbs_for_symptom(symptom_id_to_query_2)
    print(f"症状ID '{symptom_id_to_query_2}' (咳嗽) 的相关药材 ({len(related_herbs_2)}):")
    for herb in related_herbs_2: # Expected: YC001
        print(f"  - {herb.get('name')} (ID: {herb.get('id')})")

    symptom_id_no_relations = "ZZ000" # 假设这个ID不存在或没有关系定义
    # 为了测试一个确实没有关系的症状，先确认ZZ000不存在
    if not crud_caozuo.get_symptom_by_id(symptom_id_no_relations):
        print(f"确认症状ID '{symptom_id_no_relations}' 不存在或无数据。")
    related_herbs_none = get_related_herbs_for_symptom(symptom_id_no_relations)
    print(f"症状ID '{symptom_id_no_relations}' 的相关药材 ({len(related_herbs_none)}):")
    if not related_herbs_none:
        print("  （未找到相关药材或症状不存在）")
        
    non_existent_symptom_id = "ZZ888"
    related_herbs_invalid_symptom = get_related_herbs_for_symptom(non_existent_symptom_id)
    print(f"不存在的症状ID '{non_existent_symptom_id}' 的相关药材 ({len(related_herbs_invalid_symptom)}):")
    if not related_herbs_invalid_symptom:
        print("  （未找到相关药材或症状不存在）")

    empty_symptom_id = " "
    related_herbs_empty_id = get_related_herbs_for_symptom(empty_symptom_id)
    print(f"空的症状ID 的相关药材 ({len(related_herbs_empty_id)}):")
    if not related_herbs_empty_id:
        print("  （症状ID无效）")

    # Optional: Clean up test files after example run
    # wenjian_caozuo.rewrite_file(shezhi.YAOCAI_FILE, [])
    # wenjian_caozuo.rewrite_file(shezhi.ZHENGZHUANG_FILE, [])
    # wenjian_caozuo.rewrite_file(shezhi.YAOCAI_ZHENGZHUANG_GUANLIAN_FILE, [])
    # print(f"\n已清空测试文件。")
