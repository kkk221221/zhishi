import json

def parse_entity_line(line_string: str) -> dict | None:
    """
    将 TXT 文件中的一行 JSONL 字符串解析为 Python 字典。
    Args:
        line_string: 从文件中读取的一行字符串。
    Returns:
        解析后的 Python 字典，如果解析失败则返回 None。
    """
    try:
        # 移除字符串两端的空白字符，避免空行或意外的空格导致解析错误
        cleaned_line = line_string.strip()
        if not cleaned_line: # 如果是空行或只有空白字符的行
            return None
        return json.loads(cleaned_line)
    except json.JSONDecodeError as e:
        # 处理 JSON 解析错误
        print(f"解析行 '{line_string[:50]}...' 时发生JSON解码错误: {e}") # 只打印前50个字符以避免过长的日志
        return None
    except Exception as e:
        # 处理其他可能的未知错误
        print(f"解析行 '{line_string[:50]}...' 时发生未知错误: {e}")
        return None

def format_entity_for_txt(entity_object: dict) -> str | None:
    """
    将 Python 字典或对象格式化为待写入 TXT 文件的 JSONL 字符串。
    Args:
        entity_object: 待格式化的 Python 字典。
    Returns:
        格式化后的 JSON 字符串，如果格式化失败则返回 None。
    """
    try:
        # ensure_ascii=False 使得中文字符能正确显示，而不是被转义为 \uXXXX
        return json.dumps(entity_object, ensure_ascii=False)
    except TypeError as e:
        # 处理无法序列化为JSON的对象类型错误
        print(f"格式化对象 '{str(entity_object)[:50]}...' 为JSON时发生类型错误: {e}")
        return None
    except Exception as e:
        # 处理其他可能的未知错误
        print(f"格式化对象 '{str(entity_object)[:50]}...' 为JSON时发生未知错误: {e}")
        return None

# 示例用法 (可选, 可移除或注释掉)
if __name__ == '__main__':
    # 测试 parse_entity_line
    valid_line = '{"id": "YC001", "name": "人参", "properties": ["补气", "健脾"]}'
    invalid_line_syntax = '{"id": "YC002", "name": "枸杞", "properties": ["补肾", "明目]}' # 修正: properties 应该是字符串
    invalid_line_json = '{"id": "YC002", "name": "枸杞", properties: ["补肾", "明目"]}' # 属性名未加引号, JSON错误
    empty_line = ""
    whitespace_line = "   "

    print("--- 测试 parse_entity_line ---")
    print(f"解析有效行: {parse_entity_line(valid_line)}")
    print(f"解析无效行 (JSON语法错误): {parse_entity_line(invalid_line_json)}")
    print(f"解析空行: {parse_entity_line(empty_line)}")
    print(f"解析空白行: {parse_entity_line(whitespace_line)}")
    print(f"解析修正后的行: {parse_entity_line(invalid_line_syntax)}")


    # 测试 format_entity_for_txt
    print("\n--- 测试 format_entity_for_txt ---")
    valid_object = {"id": "FJ001", "name": "六味地黄丸", "composition": ["熟地黄", "山茱萸", "山药"]}
    
    # 一个不能直接JSON序列化的例子 (例如包含自定义类的实例而不自定义序列化方法)
    class NonSerializable:
        def __str__(self):
            return "NonSerializableInstance"
    invalid_object_type = {"id": "XX001", "data": NonSerializable()}

    print(f"格式化有效对象: {format_entity_for_txt(valid_object)}")
    print(f"格式化无效对象 (类型错误): {format_entity_for_txt(invalid_object_type)}")

    # 测试包含中文字符的格式化
    chinese_object = {"id": "YC003", "name": "黄芪", "功效": "补气升阳"}
    print(f"格式化含中文字符的对象: {format_entity_for_txt(chinese_object)}")
