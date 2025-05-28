import json
import os

# 确保目录存在，如果不存在则创建
def _ensure_dir_exists(file_path: str):
    """确保文件所在目录存在，如果不存在则创建。""" # Docstring for _ensure_dir_exists
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def read_file(file_path: str) -> list[str]:
    """
    读取指定文件的所有行。
    Args:
        file_path: 文件的完整路径。
    Returns:
        一个包含文件所有行的列表 (每行末尾的换行符会被去除)。
    Raises:
        FileNotFoundError: 如果文件未找到。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        # 文件未找到时，可以选择返回空列表或重新抛出异常
        # 此处选择重新抛出，由调用者处理
        raise FileNotFoundError(f"错误：文件 {file_path} 未找到。")
    except Exception as e:
        # 处理其他可能的读取错误
        print(f"读取文件 {file_path} 时发生错误: {e}")
        return []

def append_to_file(file_path: str, line_data: str):
    """
    向文件追加一行数据。
    Args:
        file_path: 文件的完整路径。
        line_data: 要追加到文件的数据行 (字符串)。
    """
    _ensure_dir_exists(file_path) # 确保目录存在
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(line_data + '\n')
    except Exception as e:
        # 处理可能的写入错误
        print(f"向文件 {file_path} 追加数据时发生错误: {e}")

def rewrite_file(file_path: str, lines_data: list[str]):
    """
    用新的数据行重写整个文件。
    Args:
        file_path: 文件的完整路径。
        lines_data: 一个包含新数据行的列表 (每个元素是一行字符串)。
    """
    _ensure_dir_exists(file_path) # 确保目录存在
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for line in lines_data:
                f.write(line + '\n')
    except Exception as e:
        # 处理可能的写入错误
        print(f"重写文件 {file_path} 时发生错误: {e}")

# 示例用法 (可选，用于测试)
if __name__ == '__main__':
    # 测试前，请确保 tcm_zhishitu_txt_mokuai/peizhi/shezhi.py 文件存在且已配置
    # 并且 tcm_zhishitu_txt_mokuai/shuju/ 目录结构已创建
    # (如果尚未创建，_ensure_dir_exists 会尝试创建)
    
    # 假设的测试文件路径 (实际应从 peizhi.shezhi 导入)
    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shuju", "test_data")
    test_file = os.path.join(test_dir, "test_wenjian.txt")
    
    print(f"测试文件将位于: {test_file}")

    # 1. 测试 _ensure_dir_exists (间接通过 append 和 rewrite 测试)
    # 2. 测试 append_to_file
    print("\n测试 append_to_file...")
    append_to_file(test_file, "第一行测试数据")
    append_to_file(test_file, "{\"id\": \"T001\", \"name\": \"测试条目\"}") # JSONL 格式
    
    # 3. 测试 read_file
    print("\n测试 read_file...")
    try:
        lines = read_file(test_file)
        print("文件内容:")
        for l in lines:
            print(l)
    except FileNotFoundError as e:
        print(e)
    
    # 4. 测试 rewrite_file
    print("\n测试 rewrite_file...")
    new_lines = [
        "这是重写后的第一行",
        "{\"id\": \"T002\", \"name\": \"新的测试条目\"}",
        "这是重写后的第三行"
    ]
    rewrite_file(test_file, new_lines)
    
    # 再次读取验证 rewrite
    print("\n再次读取文件 (验证 rewrite_file)...")
    try:
        lines = read_file(test_file)
        print("文件内容:")
        for l in lines:
            print(l)
    except FileNotFoundError as e:
        print(e)

    # 5. 测试 read_file 对不存在的文件
    print("\n测试 read_file (不存在的文件)...")
    try:
        read_file("non_existent_file.txt")
    except FileNotFoundError as e:
        print(f"成功捕获错误: {e}")
    
    print("\n测试完成。请检查 'shuju/test_data/test_wenjian.txt' 文件。")
