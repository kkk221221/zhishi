import unittest
import os
import sys
import shutil # For rmtree

# Adjust sys.path to ensure modules can be imported correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.dirname(project_root))

from tcm_zhishitu_txt_mokuai.hexin import chaxun_yinqing, crud_caozuo, id_shengchengqi, wenjian_caozuo
from tcm_zhishitu_txt_mokuai.peizhi import shezhi
# shuju_jiexi is used by crud_caozuo, so direct import not essential here unless used directly in tests

class TestQueryEngine(unittest.TestCase):
    
    def setUp(self):
        # Store original paths
        self.original_yaocai_file = shezhi.YAOCAI_FILE
        self.original_zhengzhuang_file = shezhi.ZHENGZHUANG_FILE
        self.original_guanlian_file = shezhi.YAOCAI_ZHENGZHUANG_GUANLIAN_FILE
        
        self.original_crud_yaocai_path = crud_caozuo.ENTITY_CONFIG["herb"]["file"]
        self.original_crud_symptom_path = crud_caozuo.ENTITY_CONFIG["symptom"]["file"]
        self.original_crud_relationship_path = crud_caozuo.ENTITY_CONFIG["relationship"]["file"]

        # Define test file paths
        self.test_dir = os.path.join(project_root, "tests", "temp_test_query_data") 
        os.makedirs(self.test_dir, exist_ok=True)
        
        self.test_herbs_file = os.path.join(self.test_dir, "test_herbs_query.txt")
        self.test_symptoms_file = os.path.join(self.test_dir, "test_symptoms_query.txt")
        self.test_relations_file = os.path.join(self.test_dir, "test_relations_query.txt")

        # Monkeypatch paths in shezhi and crud_caozuo.ENTITY_CONFIG
        shezhi.YAOCAI_FILE = self.test_herbs_file
        shezhi.ZHENGZHUANG_FILE = self.test_symptoms_file
        shezhi.YAOCAI_ZHENGZHUANG_GUANLIAN_FILE = self.test_relations_file
        
        crud_caozuo.ENTITY_CONFIG["herb"]["file"] = self.test_herbs_file
        crud_caozuo.ENTITY_CONFIG["symptom"]["file"] = self.test_symptoms_file
        crud_caozuo.ENTITY_CONFIG["relationship"]["file"] = self.test_relations_file

        id_shengchengqi._counters.clear()

        # Ensure files are empty before populating by the main setUp
        open(self.test_herbs_file, 'w').close()
        open(self.test_symptoms_file, 'w').close()
        open(self.test_relations_file, 'w').close()

        # Populate with test data for general tests
        self.h1 = crud_caozuo.add_herb({"name": "人参", "properties": ["补气", "健脾", "大补元气"]}) 
        self.h2 = crud_caozuo.add_herb({"name": "当归", "properties": ["补血", "调经"]})       
        self.h3 = crud_caozuo.add_herb({"name": "黄芪", "properties": ["补气", "固表"]})       
        self.h4 = crud_caozuo.add_herb({"name": "板蓝根", "properties": ["清热解毒"]})     
        self.h5 = crud_caozuo.add_herb({"name": "金银花", "properties": ["清热解毒", "疏散风热"]})
        
        self.s1 = crud_caozuo.add_symptom({"name": "头痛", "description": "常见的头部不适症状,有时伴有眩晕"}) # Original description
        self.s2 = crud_caozuo.add_symptom({"name": "咳嗽", "description": "喉咙问题, 咳痰"})   
        self.s3 = crud_caozuo.add_symptom({"name": "鼻塞", "description": "此乃感冒之常见症状也"}) 
        self.s4 = crud_caozuo.add_symptom({"name": "食欲不振", "description": "脾胃虚弱导致食欲差"}) 
        
        self.r1 = crud_caozuo.add_relationship({"herb_id": self.h1["id"], "symptom_id": self.s1["id"], "relation_type": "主治"})
        self.r2 = crud_caozuo.add_relationship({"herb_id": self.h1["id"], "symptom_id": self.s2["id"], "relation_type": "缓解"})
        self.r3 = crud_caozuo.add_relationship({"herb_id": self.h2["id"], "symptom_id": self.s1["id"], "relation_type": "可用于"})
        self.r4 = crud_caozuo.add_relationship({"herb_id": self.h3["id"], "symptom_id": self.s1["id"], "relation_type": "主治"}) 
        self.r5 = crud_caozuo.add_relationship({"herb_id": self.h4["id"], "symptom_id": self.s2["id"], "relation_type": "主治"}) 
        self.r_invalid_symptom = crud_caozuo.add_relationship({"herb_id": self.h1["id"], "symptom_id": "ZZ999", "relation_type": "未知"})
        self.r_invalid_herb = crud_caozuo.add_relationship({"herb_id": "YC888", "symptom_id": self.s1["id"], "relation_type": "未知"})

    def tearDown(self):
        shezhi.YAOCAI_FILE = self.original_yaocai_file
        shezhi.ZHENGZHUANG_FILE = self.original_zhengzhuang_file
        shezhi.YAOCAI_ZHENGZHUANG_GUANLIAN_FILE = self.original_guanlian_file
        crud_caozuo.ENTITY_CONFIG["herb"]["file"] = self.original_crud_yaocai_path
        crud_caozuo.ENTITY_CONFIG["symptom"]["file"] = self.original_crud_symptom_path
        crud_caozuo.ENTITY_CONFIG["relationship"]["file"] = self.original_crud_relationship_path
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        id_shengchengqi._counters.clear()

    # --- Test find_herbs_by_property ---
    def test_find_herbs_by_property_found_multiple(self):
        results = chaxun_yinqing.find_herbs_by_property("补气")
        self.assertEqual(len(results), 2) 
        names = sorted([h["name"] for h in results])
        self.assertEqual(names, ["人参", "黄芪"])

    def test_find_herbs_by_property_found_single(self):
        results = chaxun_yinqing.find_herbs_by_property("补血")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "当归")

    def test_find_herbs_by_property_case_insensitive(self):
        results_chinese = chaxun_yinqing.find_herbs_by_property("补气")
        self.assertEqual(len(results_chinese), 2)
        results_lower_chinese = chaxun_yinqing.find_herbs_by_property("大补元气")
        self.assertEqual(len(results_lower_chinese), 1)
        self.assertEqual(results_lower_chinese[0]["name"], "人参")

    def test_find_herbs_by_property_not_found(self):
        results = chaxun_yinqing.find_herbs_by_property("活血化瘀")
        self.assertEqual(len(results), 0)

    def test_find_herbs_by_property_empty_input(self):
        results = chaxun_yinqing.find_herbs_by_property("")
        self.assertEqual(len(results), 0)
        results_whitespace = chaxun_yinqing.find_herbs_by_property("   ")
        self.assertEqual(len(results_whitespace), 0)

    # --- Test find_symptoms_by_keyword ---
    def test_find_symptoms_by_keyword_in_name(self):
        results = chaxun_yinqing.find_symptoms_by_keyword("头痛")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.s1["id"])

    def test_find_symptoms_by_keyword_in_description(self):
        # s1 description: "常见的头部不适症状,有时伴有眩晕" -> Does NOT contain "常见症状" as a CONSECUTIVE substring.
        # s3 description: "此乃感冒之常见症状也" -> DOES contain "常见症状" as a consecutive substring.
        results = chaxun_yinqing.find_symptoms_by_keyword("常见症状") 
        self.assertEqual(len(results), 1, "Expected to find only s3 for keyword '常见症状'")
        if results: 
            self.assertEqual(results[0]["id"], self.s3["id"], "The symptom found should be s3")

    def test_find_symptoms_by_keyword_in_name_and_description_no_duplicates(self):
        # s1: name="头痛", description="常见的头部不适症状,有时伴有眩晕"
        results = chaxun_yinqing.find_symptoms_by_keyword("头部") 
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.s1["id"])
        
        results_name_match = chaxun_yinqing.find_symptoms_by_keyword("头痛") 
        self.assertEqual(len(results_name_match), 1)
        self.assertEqual(results_name_match[0]["id"], self.s1["id"])

    def test_find_symptoms_by_keyword_not_found(self):
        results = chaxun_yinqing.find_symptoms_by_keyword("发热")
        self.assertEqual(len(results), 0)

    def test_find_symptoms_by_keyword_case_insensitive(self):
        results_chinese_upper = chaxun_yinqing.find_symptoms_by_keyword("喉咙")
        self.assertEqual(len(results_chinese_upper), 1)
        self.assertEqual(results_chinese_upper[0]["id"], self.s2["id"])

    def test_find_symptoms_by_keyword_empty_input(self):
        results = chaxun_yinqing.find_symptoms_by_keyword("")
        self.assertEqual(len(results), 0)
        results_whitespace = chaxun_yinqing.find_symptoms_by_keyword("   ")
        self.assertEqual(len(results_whitespace), 0)

    # --- Test get_related_symptoms_for_herb ---
    def test_get_related_symptoms_for_herb_multiple(self):
        results = chaxun_yinqing.get_related_symptoms_for_herb(self.h1["id"]) 
        self.assertEqual(len(results), 2) 
        ids = sorted([s["id"] for s in results])
        self.assertEqual(ids, sorted([self.s1["id"], self.s2["id"]]))

    def test_get_related_symptoms_for_herb_single(self):
        results = chaxun_yinqing.get_related_symptoms_for_herb(self.h2["id"]) 
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.s1["id"]) 

    def test_get_related_symptoms_for_herb_none(self):
        results = chaxun_yinqing.get_related_symptoms_for_herb(self.h5["id"]) 
        self.assertEqual(len(results), 0)

    def test_get_related_symptoms_for_herb_non_existent_herb_id(self):
        results = chaxun_yinqing.get_related_symptoms_for_herb("YC777")
        self.assertEqual(len(results), 0)

    def test_get_related_symptoms_for_herb_relationship_to_non_existent_symptom(self):
        results = chaxun_yinqing.get_related_symptoms_for_herb(self.h1["id"])
        self.assertEqual(len(results), 2) 
        valid_symptom_ids = {s["id"] for s in results}
        self.assertIn(self.s1["id"], valid_symptom_ids)
        self.assertIn(self.s2["id"], valid_symptom_ids)
        self.assertNotIn("ZZ999", valid_symptom_ids) 

    # --- Test get_related_herbs_for_symptom ---
    def test_get_related_herbs_for_symptom_multiple(self):
        results = chaxun_yinqing.get_related_herbs_for_symptom(self.s1["id"]) 
        self.assertEqual(len(results), 3) 
        ids = sorted([h["id"] for h in results])
        self.assertEqual(ids, sorted([self.h1["id"], self.h2["id"], self.h3["id"]]))

    def test_get_related_herbs_for_symptom_single(self):
        results_s2 = chaxun_yinqing.get_related_herbs_for_symptom(self.s2["id"]) 
        self.assertEqual(len(results_s2), 2) 
        ids = sorted([h["id"] for h in results_s2])
        self.assertEqual(ids, sorted([self.h1["id"], self.h4["id"]]))

    def test_get_related_herbs_for_symptom_none(self):
        results = chaxun_yinqing.get_related_herbs_for_symptom(self.s4["id"]) 
        self.assertEqual(len(results), 0)

    def test_get_related_herbs_for_symptom_non_existent_symptom_id(self):
        results = chaxun_yinqing.get_related_herbs_for_symptom("ZZ777")
        self.assertEqual(len(results), 0)

    def test_get_related_herbs_for_symptom_relationship_to_non_existent_herb(self):
        results = chaxun_yinqing.get_related_herbs_for_symptom(self.s1["id"])
        self.assertEqual(len(results), 3) 
        valid_herb_ids = {h["id"] for h in results}
        self.assertIn(self.h1["id"], valid_herb_ids)
        self.assertIn(self.h2["id"], valid_herb_ids)
        self.assertIn(self.h3["id"], valid_herb_ids)
        self.assertNotIn("YC888", valid_herb_ids)

if __name__ == '__main__':
    unittest.main()
