import unittest
import os
import json
import sys
import shutil # For potential future use, like copying fixture files

# Adjust sys.path to ensure modules can be imported correctly
# Get current test file directory -> tcm_zhishitu_txt_mokuai/tests
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get project root directory -> tcm_zhishitu_txt_mokuai
project_root = os.path.dirname(current_dir)
# Add the parent directory of project_root to sys.path
# This allows imports like from tcm_zhishitu_txt_mokuai.hexin...
sys.path.insert(0, os.path.dirname(project_root))

from tcm_zhishitu_txt_mokuai.hexin import crud_caozuo
from tcm_zhishitu_txt_mokuai.hexin import id_shengchengqi
from tcm_zhishitu_txt_mokuai.peizhi import shezhi
from tcm_zhishitu_txt_mokuai.hexin import wenjian_caozuo # For direct file checks if needed

class TestCrudOperations(unittest.TestCase):
    """测试 CRUD 操作 (crud_caozuo.py)"""

    ENTITY_TYPE_HERB = "herb"
    ENTITY_TYPE_UNKNOWN = "nonexistent_entity_type"

    def setUp(self):
        """在每个测试方法运行前设置测试环境"""
        # 定义临时测试文件路径
        self.test_dir = os.path.join(project_root, "tests", "temp_test_data")
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)

        self.test_yaocai_file = os.path.join(self.test_dir, "test_yaocai_temp.txt")
        
        # 备份原始文件路径配置
        self.original_yaocai_file_path = shezhi.YAOCAI_FILE
        
        # 重定向shezhi中的文件路径到临时测试文件
        # AND more importantly, redirect the path within crud_caozuo.ENTITY_CONFIG
        self.original_crud_yaocai_file_path = crud_caozuo.ENTITY_CONFIG[self.ENTITY_TYPE_HERB]["file"]
        crud_caozuo.ENTITY_CONFIG[self.ENTITY_TYPE_HERB]["file"] = self.test_yaocai_file
        
        # 清理ID生成器的计数器，确保测试隔离性
        id_shengchengqi._counters.clear()

        # 如果测试文件已存在，先删除它，确保一个干净的开始
        if os.path.exists(self.test_yaocai_file):
            os.remove(self.test_yaocai_file)
        # Create an empty file so read operations on an empty file don't raise FileNotFoundError
        # in wenjian_caozuo.read_file based on its current implementation
        # Also, _ensure_dir_exists in wenjian_caozuo will create the directory if it doesn't exist.
        open(self.test_yaocai_file, 'w').close()


    def tearDown(self):
        """在每个测试方法运行后清理测试环境"""
        # 删除测试后创建的临时文件和目录
        if os.path.exists(self.test_yaocai_file):
            os.remove(self.test_yaocai_file)
        
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir) # Use shutil.rmtree to remove the directory and its contents

        # 恢复原始的文件路径配置
        # shezhi.YAOCAI_FILE = self.original_yaocai_file_path # This line is less critical now
        crud_caozuo.ENTITY_CONFIG[self.ENTITY_TYPE_HERB]["file"] = self.original_crud_yaocai_file_path
        
        # 再次清理ID生成器计数器
        id_shengchengqi._counters.clear()

    def _read_test_file_direct(self, file_path):
        """辅助方法：直接读取并解析测试文件的内容"""
        content = []
        if os.path.exists(file_path):
            lines = wenjian_caozuo.read_file(file_path) # Use our own file reader
            for line in lines:
                if line.strip(): # Ensure line is not empty
                    content.append(json.loads(line))
        return content

    # --- Test Add Entity ---
    def test_add_herb(self):
        herb_data = {"name": "枸杞", "properties": ["滋补肝肾", "益精明目"]}
        added_herb = crud_caozuo.add_entity(herb_data, self.ENTITY_TYPE_HERB)
        
        self.assertIsNotNone(added_herb)
        self.assertIn("id", added_herb)
        self.assertEqual(added_herb["id"], f"{shezhi.YAOCAI_PREFIX}001")
        self.assertEqual(added_herb["name"], herb_data["name"])
        self.assertEqual(added_herb["properties"], herb_data["properties"])

        file_content = self._read_test_file_direct(self.test_yaocai_file)
        self.assertEqual(len(file_content), 1)
        self.assertEqual(file_content[0], added_herb)

    def test_add_herb_with_preexisting_id_in_data(self):
        herb_data = {"id": "YC_PRESET", "name": "甘草", "properties": ["调和诸药"]}
        # add_entity should return None as 'id' is in entity_data_dict
        added_herb = crud_caozuo.add_entity(herb_data, self.ENTITY_TYPE_HERB)
        self.assertIsNone(added_herb, "add_entity should return None when 'id' is in input data")

        # Verify the file remains empty or unchanged
        file_content = self._read_test_file_direct(self.test_yaocai_file)
        self.assertEqual(len(file_content), 0, "File should be empty if add_entity failed as expected")


    # --- Test Get All Entities ---
    def test_get_all_herbs_empty_file(self):
        all_herbs = crud_caozuo.get_all_entities(self.ENTITY_TYPE_HERB)
        self.assertEqual(all_herbs, [])

    def test_get_all_herbs_with_data(self):
        herb1_data = {"name": "人参", "properties": ["大补元气"]}
        crud_caozuo.add_entity(herb1_data, self.ENTITY_TYPE_HERB)
        herb2_data = {"name": "当归", "properties": ["补血活血"]}
        crud_caozuo.add_entity(herb2_data, self.ENTITY_TYPE_HERB)
        
        all_herbs = crud_caozuo.get_all_entities(self.ENTITY_TYPE_HERB)
        self.assertEqual(len(all_herbs), 2)
        self.assertEqual(all_herbs[0]["name"], herb1_data["name"])
        self.assertEqual(all_herbs[1]["name"], herb2_data["name"])

    def test_get_all_herbs_non_existent_file(self):
        # Ensure file does not exist for this specific test
        if os.path.exists(self.test_yaocai_file):
            os.remove(self.test_yaocai_file)
        all_herbs = crud_caozuo.get_all_entities(self.ENTITY_TYPE_HERB)
        self.assertEqual(all_herbs, [])


    # --- Test Get Entity By ID ---
    def test_get_herb_by_id(self):
        herb_data = {"name": "黄芪", "properties": ["补气升阳"]}
        added_herb = crud_caozuo.add_entity(herb_data, self.ENTITY_TYPE_HERB)
        self.assertIsNotNone(added_herb)
        
        retrieved_herb = crud_caozuo.get_entity_by_id(added_herb["id"], self.ENTITY_TYPE_HERB)
        self.assertIsNotNone(retrieved_herb)
        self.assertEqual(retrieved_herb, added_herb)

    def test_get_herb_by_id_non_existent(self):
        retrieved_herb = crud_caozuo.get_entity_by_id("YC999", self.ENTITY_TYPE_HERB)
        self.assertIsNone(retrieved_herb)


    # --- Test Update Entity ---
    def test_update_herb(self):
        herb_data = {"name": "远志", "properties": ["安神益智"], "notes": "初版"}
        added_herb = crud_caozuo.add_entity(herb_data, self.ENTITY_TYPE_HERB)
        self.assertIsNotNone(added_herb)
        
        update_payload = {"properties": ["安神益智", "祛痰开窍"], "notes": "修订版"}
        updated_herb = crud_caozuo.update_entity(added_herb["id"], update_payload, self.ENTITY_TYPE_HERB)
        
        self.assertIsNotNone(updated_herb)
        self.assertEqual(updated_herb["id"], added_herb["id"]) # ID should not change
        self.assertEqual(updated_herb["name"], added_herb["name"]) # Name was not in payload
        self.assertEqual(updated_herb["properties"], update_payload["properties"])
        self.assertEqual(updated_herb["notes"], update_payload["notes"])

        retrieved_herb_after_update = crud_caozuo.get_entity_by_id(added_herb["id"], self.ENTITY_TYPE_HERB)
        self.assertEqual(retrieved_herb_after_update, updated_herb)

    def test_update_herb_non_existent(self):
        update_payload = {"name": "不存在的药"}
        result = crud_caozuo.update_entity("YC777", update_payload, self.ENTITY_TYPE_HERB)
        self.assertIsNone(result)

    def test_update_herb_with_id_in_payload(self):
        herb_data = {"name": "白术", "properties": ["健脾益气"]}
        added_herb = crud_caozuo.add_entity(herb_data, self.ENTITY_TYPE_HERB)
        self.assertIsNotNone(added_herb)

        update_payload = {"id": "NEW_ID_IGNORED", "name": "炒白术"}
        # update_entity should handle 'id' in payload (e.g., ignore it or warn)
        updated_herb = crud_caozuo.update_entity(added_herb["id"], update_payload, self.ENTITY_TYPE_HERB)
        self.assertIsNotNone(updated_herb)
        self.assertEqual(updated_herb["id"], added_herb["id"]) # ID must not change
        self.assertEqual(updated_herb["name"], "炒白术")
        
    def test_update_herb_does_not_affect_others(self):
        herb1_data = {"name": "茯苓", "properties": ["利水渗湿"]}
        herb2_data = {"name": "泽泻", "properties": ["利水泄热"]}
        added_herb1 = crud_caozuo.add_entity(herb1_data, self.ENTITY_TYPE_HERB)
        added_herb2 = crud_caozuo.add_entity(herb2_data, self.ENTITY_TYPE_HERB)

        update_payload = {"name": "茯神"} #茯苓 -> 茯神
        crud_caozuo.update_entity(added_herb1["id"], update_payload, self.ENTITY_TYPE_HERB)

        retrieved_herb1 = crud_caozuo.get_entity_by_id(added_herb1["id"], self.ENTITY_TYPE_HERB)
        retrieved_herb2 = crud_caozuo.get_entity_by_id(added_herb2["id"], self.ENTITY_TYPE_HERB)

        self.assertEqual(retrieved_herb1["name"], "茯神")
        self.assertEqual(retrieved_herb2["name"], added_herb2["name"]) # herb2 should be unchanged


    # --- Test Delete Entity ---
    def test_delete_herb(self):
        herb1_data = {"name": "丹参", "properties": ["活血祛瘀"]}
        herb2_data = {"name": "赤芍", "properties": ["清热凉血", "活血祛瘀"]}
        added_herb1 = crud_caozuo.add_entity(herb1_data, self.ENTITY_TYPE_HERB)
        added_herb2 = crud_caozuo.add_entity(herb2_data, self.ENTITY_TYPE_HERB)
        self.assertIsNotNone(added_herb1)
        self.assertIsNotNone(added_herb2)
        
        delete_result = crud_caozuo.delete_entity(added_herb1["id"], self.ENTITY_TYPE_HERB)
        self.assertTrue(delete_result)
        
        self.assertIsNone(crud_caozuo.get_entity_by_id(added_herb1["id"], self.ENTITY_TYPE_HERB))
        self.assertIsNotNone(crud_caozuo.get_entity_by_id(added_herb2["id"], self.ENTITY_TYPE_HERB))
        
        all_remaining_herbs = crud_caozuo.get_all_entities(self.ENTITY_TYPE_HERB)
        self.assertEqual(len(all_remaining_herbs), 1)
        self.assertEqual(all_remaining_herbs[0]["id"], added_herb2["id"])

    def test_delete_herb_non_existent(self):
        result = crud_caozuo.delete_entity("YC666", self.ENTITY_TYPE_HERB)
        self.assertFalse(result)


    # --- Test Unknown Entity Type ---
    def test_unknown_entity_type_operations(self):
        data = {"name": "测试数据"}
        self.assertIsNone(crud_caozuo.add_entity(data, self.ENTITY_TYPE_UNKNOWN))
        self.assertEqual(crud_caozuo.get_all_entities(self.ENTITY_TYPE_UNKNOWN), [])
        self.assertIsNone(crud_caozuo.get_entity_by_id("ID001", self.ENTITY_TYPE_UNKNOWN))
        self.assertIsNone(crud_caozuo.update_entity("ID001", data, self.ENTITY_TYPE_UNKNOWN))
        self.assertFalse(crud_caozuo.delete_entity("ID001", self.ENTITY_TYPE_UNKNOWN))


if __name__ == '__main__':
    unittest.main()
