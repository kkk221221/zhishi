# src/data_layer/data_processing/utils.py

import os
import re
import logging # Import logging module

# 通用工具函数模块
# 提供文件操作、路径创建、文件名清理等辅助功能。

def read_text_file(file_path: str) -> str | None:
    # 读取文本文件内容。
    # :param file_path: 文件路径。
    # :return: 文件内容字符串，如果文件不存在或发生错误则返回None。
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"错误: 文件未找到 {file_path}")
        return None
    except Exception as e:
        print(f"读取文件 {file_path} 时发生错误: {e}")
        return None

def write_text_file(file_path: str, content: str):
    # 将文本内容写入文件。
    # :param file_path: 要写入的文件路径。
    # :param content: 要写入的文本内容。
    try:
        # 确保目标目录存在
        ensure_directory_exists(os.path.dirname(file_path))
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"文件已成功写入: {file_path}")
    except Exception as e:
        print(f"写入文件 {file_path} 时发生错误: {e}")

def ensure_directory_exists(dir_path: str):
    # 确保目录存在，如果不存在则创建。
    # :param dir_path: 目录路径。
    if not dir_path: # 处理空字符串或None的情况
        return
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            print(f"目录已创建: {dir_path}")
        except Exception as e:
            print(f"创建目录 {dir_path} 时发生错误: {e}")
    else:
        print(f"目录已存在: {dir_path}")


def clean_filename(filename: str) -> str:
    # 清理文件名，移除或替换非法字符，并将空格替换为下划线。
    # :param filename: 原始文件名。
    # :return: 清理后的文件名。
    if not filename:
        return ""
    
    # 移除或替换在Windows和Unix系统中通常不允许的字符
    # Windows: < > : " / \ | ? *
    # Unix: / (以及空字符)
    # 我们将它们替换为下划线
    filename = re.sub(r'[\<\>\:"\/\\\|\?\*]', '_', filename)
    
    # 将一个或多个空格替换为单个下划线
    filename = re.sub(r'\s+', '_', filename)
    
    # 移除可能导致问题的开头或结尾的特殊字符（如下划线、点、空格 - 尽管空格已处理）
    filename = filename.strip('._ ')
    
    # 防止文件名过长
    MAX_FILENAME_COMPONENT_LENGTH = 70 # Max length for this cleaned filename component

    # If the filename (which might be a component) is too long, truncate it.
    # This logic primarily targets the name part, preserving an extension if present.
    if len(filename) > MAX_FILENAME_COMPONENT_LENGTH:
        logging.warning(f"原始文件名组件 '{filename}' 清理后长度为 {len(filename)}，超过限制 {MAX_FILENAME_COMPONENT_LENGTH}，将被截断。")

        name_part, ext_part = os.path.splitext(filename)

        # If there's no extension, or the name_part itself is the whole filename
        if not ext_part: # filename was 'verylongname'
            name_part = filename
            # ext_part remains ""

        # Calculate how much of the name_part can be kept
        # Max length for name_part = MAX_FILENAME_COMPONENT_LENGTH - length of extension (if any)
        allowed_name_part_len = MAX_FILENAME_COMPONENT_LENGTH - len(ext_part)

        # Ensure allowed_name_part_len is not negative (e.g. if extension itself is too long)
        if allowed_name_part_len < 0:
            allowed_name_part_len = 0 # Cannot keep any of name_part if ext is too long

        truncated_name_part = name_part[:allowed_name_part_len]

        filename = truncated_name_part + ext_part
        logging.info(f"文件名组件截断为: '{filename}'")

    return filename

# 示例用法 (可以注释掉或移除)
# if __name__ == '__main__':
#     # 测试 ensure_directory_exists
#     test_dir = "test_data/output_files"
#     ensure_directory_exists(test_dir)

#     # 测试 write_text_file 和 read_text_file
#     test_file_path = os.path.join(test_dir, "test_document.txt")
#     write_text_file(test_file_path, "这是�个测试文件。\n第二行内容。")
    
#     content = read_text_file(test_file_path)
#     if content:
#         print(f"\n从 {test_file_path} 读取的内容:\n{content}")

#     # 测试 read_text_file 处理不存在的文件
#     read_text_file("non_existent_file.txt")

#     # 测试 clean_filename
#     original_names = [
#         "My Chapter 1 / Section 2.txt",
#         "  leading and trailing spaces  .docx",
#         "file_with_many   spaces.pdf",
#         "in*val?id:chars\"<>.jpg|png",
#         "a/very/long/path/like/name/file.tar.gz"
#     ]
#     print("\n文件名清理测试:")
#     for name in original_names:
#         cleaned = clean_filename(name)
#         print(f"'{name}' -> '{cleaned}'")
#     cleaned_long = clean_filename("a"*300 + ".txt")
#     print(f"'a*300.txt' -> '{cleaned_long}' (length: {len(cleaned_long)})")
#     ensure_directory_exists("") # 测试空目录路径
#     write_text_file(os.path.join(test_dir, clean_filename("  My Document* .doc")), "Cleaned filename test.")
