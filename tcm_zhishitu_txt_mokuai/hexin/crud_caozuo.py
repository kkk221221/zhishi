# hexin/crud_caozuo.py

from . import id_shengchengqi
from . import shuju_jiexi
from . import wenjian_caozuo
from ..peizhi import shezhi # 从父目录的peizhi模块导入shezhi

# 实体类型到文件路径和ID前缀的映射
ENTITY_CONFIG = {
    "herb": {"file": shezhi.YAOCAI_FILE, "prefix": shezhi.YAOCAI_PREFIX},
    "symptom": {"file": shezhi.ZHENGZHUANG_FILE, "prefix": shezhi.ZHENGZHUANG_PREFIX},
    "formula": {"file": shezhi.FANGJI_FILE, "prefix": shezhi.FANGJI_PREFIX},
    "relationship": {"file": shezhi.YAOCAI_ZHENGZHUANG_GUANLIAN_FILE, "prefix": shezhi.GUANXI_PREFIX}
    # 可以根据需要添加更多实体类型
}

# --- Generic CRUD Functions ---
def add_entity(entity_data_dict: dict, entity_type: str) -> dict | None:
    """
    通用函数，用于向指定的实体文件添加新的实体记录。

    Args:
        entity_data_dict (dict): 包含实体数据的字典，不应包含 'id'。
        entity_type (str): 实体类型 (例如 "herb", "symptom", "formula", "relationship")。
                            需要在 ENTITY_CONFIG 中定义。

    Returns:
        dict | None: 如果成功，返回包含生成ID的完整实体字典；否则返回 None。
    """
    if entity_type not in ENTITY_CONFIG:
        print(f"错误：未知的实体类型 '{entity_type}'。")
        return None
    
    if "id" in entity_data_dict:
        print(f"错误：提供的 entity_data_dict 不应包含 'id'。 'id' 将自动生成。")
        return None

    config = ENTITY_CONFIG[entity_type]
    file_path = config["file"]
    id_prefix = config["prefix"]

    # 1. 生成ID
    generated_id = id_shengchengqi.generate_id(id_prefix)
    
    entity_with_id = entity_data_dict.copy()
    entity_with_id["id"] = generated_id

    # 2. 格式化数据
    formatted_line = shuju_jiexi.format_entity_for_txt(entity_with_id)
    if formatted_line is None:
        print(f"错误：格式化实体数据失败。实体类型: {entity_type}, 数据: {entity_with_id}")
        return None

    # 3. 追加到文件
    try:
        wenjian_caozuo.append_to_file(file_path, formatted_line)
        print(f"信息：成功添加实体到 {file_path}。ID: {generated_id}")
        return entity_with_id
    except Exception as e:
        print(f"错误：向文件 {file_path} 追加数据时发生异常: {e}")
        return None

def get_all_entities(entity_type: str) -> list[dict]:
    # """
    # 读取并解析指定类型实体的所有记录。
    # (Docstring remains commented as per original)
    # """
    if entity_type not in ENTITY_CONFIG:
        print(f"错误：未知的实体类型 '{entity_type}'。")
        return []

    file_path = ENTITY_CONFIG[entity_type]["file"]
    entities = []
    try:
        lines = wenjian_caozuo.read_file(file_path)
        for line_str in lines:
            entity_dict = shuju_jiexi.parse_entity_line(line_str)
            if entity_dict:
                entities.append(entity_dict)
            else:
                print(f"警告：在文件 {file_path} 中解析行失败: {line_str[:100]}...") 
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"错误：读取或解析文件 {file_path} 时发生异常: {e}")
        return []
    return entities

def get_entity_by_id(entity_id: str, entity_type: str) -> dict | None:
    # """
    # 根据ID读取并解析单个实体记录。
    # (Docstring remains commented as per original)
    # """
    if entity_type not in ENTITY_CONFIG:
        print(f"错误：未知的实体类型 '{entity_type}'。")
        return None
    all_entities = get_all_entities(entity_type)
    for entity in all_entities:
        if "id" in entity and entity["id"] == entity_id:
            return entity
    return None

def update_entity(entity_id: str, updated_data_dict: dict, entity_type: str) -> dict | None:
    # """
    # 更新指定ID的实体数据。
    # (Docstring remains commented as per original)
    # """
    if entity_type not in ENTITY_CONFIG:
        print(f"错误：未知的实体类型 '{entity_type}'。")
        return None

    if "id" in updated_data_dict:
        print(f"警告：updated_data_dict 中不应包含 'id' 键。实体的 ID ({entity_id}) 不可更改。")
        del updated_data_dict["id"] 

    file_path = ENTITY_CONFIG[entity_type]["file"]
    all_entities = get_all_entities(entity_type)
    entity_found = False
    updated_entity_reference = None
    new_lines_data = []

    for i, entity in enumerate(all_entities):
        if entity.get("id") == entity_id:
            entity_found = True
            original_id = entity["id"]
            current_entity_copy = entity.copy()
            current_entity_copy.update(updated_data_dict)
            current_entity_copy["id"] = original_id
            all_entities[i] = current_entity_copy
            updated_entity_reference = current_entity_copy
            break 

    if not entity_found:
        print(f"信息：在实体类型 '{entity_type}' 中未找到ID为 '{entity_id}' 的实体，无法更新。")
        return None

    for entity_dict in all_entities:
        formatted_line = shuju_jiexi.format_entity_for_txt(entity_dict)
        if formatted_line:
            new_lines_data.append(formatted_line)
        else:
            print(f"严重错误：在准备重写文件时，格式化实体失败: {entity_dict}")
            return None

    try:
        wenjian_caozuo.rewrite_file(file_path, new_lines_data)
        print(f"信息：实体 '{entity_id}' (类型: {entity_type}) 已成功更新。文件 {file_path} 已重写。")
        return updated_entity_reference
    except Exception as e:
        print(f"错误：重写文件 {file_path} 以更新实体 '{entity_id}' 时发生异常: {e}")
        return None

def delete_entity(entity_id: str, entity_type: str) -> bool:
    # """
    # 删除指定ID的实体。
    # (Docstring remains commented as per original)
    # """
    if entity_type not in ENTITY_CONFIG:
        print(f"错误：未知的实体类型 '{entity_type}'。")
        return False

    file_path = ENTITY_CONFIG[entity_type]["file"]
    all_entities = get_all_entities(entity_type)
    entity_found = False
    remaining_entities = []
    for entity in all_entities:
        if entity.get("id") == entity_id:
            entity_found = True
        else:
            remaining_entities.append(entity)

    if not entity_found:
        print(f"信息：在实体类型 '{entity_type}' 中未找到ID为 '{entity_id}' 的实体，无需删除。")
        return False

    new_lines_data = []
    for entity_dict in remaining_entities:
        formatted_line = shuju_jiexi.format_entity_for_txt(entity_dict)
        if formatted_line:
            new_lines_data.append(formatted_line)
        else:
            print(f"严重错误：在准备重写文件以删除实体时，格式化剩余实体失败: {entity_dict}")
            return False

    try:
        wenjian_caozuo.rewrite_file(file_path, new_lines_data)
        print(f"信息：实体 '{entity_id}' (类型: {entity_type}) 已成功删除。文件 {file_path} 已重写。")
        return True
    except Exception as e:
        print(f"错误：重写文件 {file_path} 以删除实体 '{entity_id}' 时发生异常: {e}")
        return False

# --- Specific CRUD Wrappers ---

# --- Herb (药材) Wrappers ---
def add_herb(herb_data: dict) -> dict | None:
    # """
    # 添加一个新的药材记录。
    # Args:
    #     herb_data (dict): 包含药材数据的字典，不应包含 'id'。
    # Returns:
    #     dict | None: 如果成功，返回包含生成ID的药材字典；否则返回 None。
    # """
    return add_entity(herb_data, "herb")

def get_all_herbs() -> list[dict]:
    # """
    # 获取所有药材记录。
    # Returns:
    #     list[dict]: 包含所有药材数据的字典列表。
    # """
    return get_all_entities("herb")

def get_herb_by_id(herb_id: str) -> dict | None:
    # """
    # 根据ID获取单个药材记录。
    # Args:
    #     herb_id (str): 药材的ID。
    # Returns:
    #     dict | None: 如果找到，返回药材字典；否则返回 None。
    # """
    return get_entity_by_id(herb_id, "herb")

def update_herb(herb_id: str, herb_data: dict) -> dict | None:
    # """
    # 更新指定ID的药材记录。
    # Args:
    #     herb_id (str): 要更新的药材的ID。
    #     herb_data (dict): 包含更新字段的字典，不应包含 'id'。
    # Returns:
    #     dict | None: 如果成功，返回更新后的药材字典；否则返回 None。
    # """
    return update_entity(herb_id, herb_data, "herb")

def delete_herb(herb_id: str) -> bool:
    # """
    # 删除指定ID的药材记录。
    # Args:
    #     herb_id (str): 要删除的药材的ID。
    # Returns:
    #     bool: 如果成功删除，返回 True；否则返回 False。
    # """
    return delete_entity(herb_id, "herb")

# --- Symptom (症状) Wrappers ---
def add_symptom(symptom_data: dict) -> dict | None:
    # """
    # 添加一个新的症状记录。
    # Args:
    #     symptom_data (dict): 包含症状数据的字典，不应包含 'id'。
    # Returns:
    #     dict | None: 如果成功，返回包含生成ID的症状字典；否则返回 None。
    # """
    return add_entity(symptom_data, "symptom")

def get_all_symptoms() -> list[dict]:
    # """
    # 获取所有症状记录。
    # Returns:
    #     list[dict]: 包含所有症状数据的字典列表。
    # """
    return get_all_entities("symptom")

def get_symptom_by_id(symptom_id: str) -> dict | None:
    # """
    # 根据ID获取单个症状记录。
    # Args:
    #     symptom_id (str): 症状的ID。
    # Returns:
    #     dict | None: 如果找到，返回症状字典；否则返回 None。
    # """
    return get_entity_by_id(symptom_id, "symptom")

def update_symptom(symptom_id: str, symptom_data: dict) -> dict | None:
    # """
    # 更新指定ID的症状记录。
    # Args:
    #     symptom_id (str): 要更新的症状的ID。
    #     symptom_data (dict): 包含更新字段的字典，不应包含 'id'。
    # Returns:
    #     dict | None: 如果成功，返回更新后的症状字典；否则返回 None。
    # """
    return update_entity(symptom_id, symptom_data, "symptom")

def delete_symptom(symptom_id: str) -> bool:
    # """
    # 删除指定ID的症状记录。
    # Args:
    #     symptom_id (str): 要删除的症状的ID。
    # Returns:
    #     bool: 如果成功删除，返回 True；否则返回 False。
    # """
    return delete_entity(symptom_id, "symptom")

# --- Formula (方剂) Wrappers ---
def add_formula(formula_data: dict) -> dict | None:
    # """
    # 添加一个新的方剂记录。
    # Args:
    #     formula_data (dict): 包含方剂数据的字典，不应包含 'id'。
    # Returns:
    #     dict | None: 如果成功，返回包含生成ID的方剂字典；否则返回 None。
    # """
    return add_entity(formula_data, "formula")

def get_all_formulas() -> list[dict]:
    # """
    # 获取所有方剂记录。
    # Returns:
    #     list[dict]: 包含所有方剂数据的字典列表。
    # """
    return get_all_entities("formula")

def get_formula_by_id(formula_id: str) -> dict | None:
    # """
    # 根据ID获取单个方剂记录。
    # Args:
    #     formula_id (str): 方剂的ID。
    # Returns:
    #     dict | None: 如果找到，返回方剂字典；否则返回 None。
    # """
    return get_entity_by_id(formula_id, "formula")

def update_formula(formula_id: str, formula_data: dict) -> dict | None:
    # """
    # 更新指定ID的方剂记录。
    # Args:
    #     formula_id (str): 要更新的方剂的ID。
    #     formula_data (dict): 包含更新字段的字典，不应包含 'id'。
    # Returns:
    #     dict | None: 如果成功，返回更新后的方剂字典；否则返回 None。
    # """
    return update_entity(formula_id, formula_data, "formula")

def delete_formula(formula_id: str) -> bool:
    # """
    # 删除指定ID的方剂记录。
    # Args:
    #     formula_id (str): 要删除的方剂的ID。
    # Returns:
    #     bool: 如果成功删除，返回 True；否则返回 False。
    # """
    return delete_entity(formula_id, "formula")

# --- Relationship (关系) Wrappers ---
def add_relationship(relationship_data: dict) -> dict | None:
    # """
    # 添加一个新的关系记录。
    # Args:
    #     relationship_data (dict): 包含关系数据的字典，不应包含 'id'。
    # Returns:
    #     dict | None: 如果成功，返回包含生成ID的关系字典；否则返回 None。
    # """
    return add_entity(relationship_data, "relationship")

def get_all_relationships() -> list[dict]:
    # """
    # 获取所有关系记录。
    # Returns:
    #     list[dict]: 包含所有关系数据的字典列表。
    # """
    return get_all_entities("relationship")

def get_relationship_by_id(relationship_id: str) -> dict | None:
    # """
    # 根据ID获取单个关系记录。
    # Args:
    #     relationship_id (str): 关系的ID。
    # Returns:
    #     dict | None: 如果找到，返回关系字典；否则返回 None。
    # """
    return get_entity_by_id(relationship_id, "relationship")

def update_relationship(relationship_id: str, relationship_data: dict) -> dict | None:
    # """
    # 更新指定ID的关系记录。
    # Args:
    #     relationship_id (str): 要更新的关系的ID。
    #     relationship_data (dict): 包含更新字段的字典，不应包含 'id'。
    # Returns:
    #     dict | None: 如果成功，返回更新后的关系字典；否则返回 None。
    # """
    return update_entity(relationship_id, relationship_data, "relationship")

def delete_relationship(relationship_id: str) -> bool:
    # """
    # 删除指定ID的关系记录。
    # Args:
    #     relationship_id (str): 要删除的关系的ID。
    # Returns:
    #     bool: 如果成功删除，返回 True；否则返回 False。
    # """
    return delete_entity(relationship_id, "relationship")

# 示例用法 (可选, 可移除或注释掉)
if __name__ == '__main__':
    # 测试前确保相关txt文件和目录已存在，或由 wenjian_caozuo 自动创建
    # 清理/创建测试文件 (简单演示，实际测试应在测试模块中进行)
    print("--- 初始化测试文件 ---")
    for entity_t, conf in ENTITY_CONFIG.items():
        # 确保目录存在
        dir_path = os.path.dirname(conf["file"])
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        wenjian_caozuo.rewrite_file(conf["file"], []) # 清空文件

    # 重置ID计数器 (仅为示例，实际应在测试setup中处理)
    id_shengchengqi._counters.clear()

    print("\n--- 测试 Herb (药材) CRUD ---")
    herb_data1 = {"name": "人参", "properties": ["补气", "健脾"], "description": "一种珍贵的中药材"}
    added_herb1 = add_herb(herb_data1)
    if added_herb1:
        print(f"成功添加药材: {added_herb1}")

    herb_data2 = {"name": "枸杞", "properties": ["滋补肝肾", "益精明目"]}
    add_herb(herb_data2) # 添加第二个药材

    all_herbs = get_all_herbs()
    print(f"所有药材 ({len(all_herbs)}):")
    for herb in all_herbs:
        print(herb)

    if all_herbs:
        herb_to_update_id = all_herbs[0]["id"]
        update_payload = {"name": "高丽参", "properties": ["大补元气", "益气摄血"]}
        updated_h = update_herb(herb_to_update_id, update_payload)
        if updated_h:
            print(f"更新后药材 ({herb_to_update_id}): {updated_h}")
        
        herb_to_delete_id = all_herbs[1]["id"] if len(all_herbs) > 1 else herb_to_update_id
        if delete_herb(herb_to_delete_id):
            print(f"成功删除药材: {herb_to_delete_id}")
        
        print("删除操作后剩余药材:")
        for herb in get_all_herbs():
            print(herb)

    print("\n--- 测试 Symptom (症状) CRUD ---")
    symptom_data1 = {"name": "头痛", "description": "头部疼痛的常见症状"}
    added_symptom1 = add_symptom(symptom_data1)
    if added_symptom1:
        print(f"成功添加症状: {added_symptom1}")
    
    get_symptom_by_id(added_symptom1["id"]) # 只是调用一下

    print("\n--- 测试 Formula (方剂) CRUD ---")
    formula_data1 = {"name": "桂枝汤", "composition": ["桂枝", "芍药", "生姜", "大枣", "甘草"], "actions": ["解肌发表", "调和营卫"]}
    added_formula1 = add_formula(formula_data1)
    if added_formula1:
        print(f"成功添加方剂: {added_formula1}")

    print("\n--- 测试 Relationship (关系) CRUD ---")
    # 假设我们已经有了药材ID和症状ID
    # yc001_id = added_herb1["id"] if added_herb1 else "YC001" # 确保有ID
    # zz001_id = added_symptom1["id"] if added_symptom1 else "ZZ001" # 确保有ID
    
    # 为了保证示例能运行，我们先检查之前添加的herb和symptom是否存在
    temp_herb = get_herb_by_id(f"{shezhi.YAOCAI_PREFIX}001") # ID是根据添加顺序生成的
    temp_symptom = get_symptom_by_id(f"{shezhi.ZHENGZHUANG_PREFIX}001")

    if temp_herb and temp_symptom:
        relationship_data1 = {"herb_id": temp_herb["id"], "symptom_id": temp_symptom["id"], "relation_type": "treats", "description": "人参可用于治疗头痛（气虚型）"}
        added_rel1 = add_relationship(relationship_data1)
        if added_rel1:
            print(f"成功添加关系: {added_rel1}")
    else:
        print("未能获取之前添加的药材或症状ID，跳过关系添加测试。")

    print("\n--- 最终文件内容检查 ---")
    print(f"\n药材文件 ({shezhi.YAOCAI_FILE}):")
    for line in wenjian_caozuo.read_file(shezhi.YAOCAI_FILE): print(line)
    print(f"\n症状文件 ({shezhi.ZHENGZHUANG_FILE}):")
    for line in wenjian_caozuo.read_file(shezhi.ZHENGZHUANG_FILE): print(line)
    print(f"\n方剂文件 ({shezhi.FANGJI_FILE}):")
    for line in wenjian_caozuo.read_file(shezhi.FANGJI_FILE): print(line)
    print(f"\n关系文件 ({shezhi.YAOCAI_ZHENGZHUANG_GUANLIAN_FILE}):")
    for line in wenjian_caozuo.read_file(shezhi.YAOCAI_ZHENGZHUANG_GUANLIAN_FILE): print(line)
