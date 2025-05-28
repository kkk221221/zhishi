# TCM Zhishitu TXT Mokuai (中医药知识图谱TXT模块)

This module is responsible for managing and processing data for a Traditional Chinese Medicine (TCM) knowledge graph. It uses plain text files (specifically JSON Lines format) to store entity and relationship data.

## Data File Formats

The data for the knowledge graph is stored in several `.txt` files within the `shuju` directory. Each of these files uses the JSON Lines (JSONL) format, meaning each line in the file is a complete and independent JSON object.

### `shuju/shiti/yaocai.txt` (Medicinal Herbs)

Each line is a JSON object representing a medicinal herb.

*   `id` (string): A unique identifier for the herb (e.g., "YC001").
*   `name` (string): The common name of the herb (e.g., "人参").
*   `properties` (list of strings): A list of medicinal properties or actions of the herb (e.g., ["补气", "健脾"]).

**Example:**
```json
{ "id": "YC001", "name": "人参", "properties": ["补气", "健脾"] }
{ "id": "YC002", "name": "当归", "properties": ["补血", "调经"] }
```

### `shuju/shiti/zhengzhuang.txt` (Symptoms)

Each line is a JSON object representing a medical symptom.

*   `id` (string): A unique identifier for the symptom (e.g., "ZZ001").
*   `name` (string): The name of the symptom (e.g., "咳嗽").
*   `description` (string, optional): A brief description of the symptom.

**Example:**
```json
{ "id": "ZZ001", "name": "咳嗽", "description": "指肺气上逆作声，或有痰，或无痰。" }
{ "id": "ZZ002", "name": "头痛", "description": "头部疼痛的感觉。" }
```

### `shuju/shiti/fangji.txt` (Formulas/Prescriptions)

Each line is a JSON object representing a TCM formula or prescription.

*   `id` (string): A unique identifier for the formula (e.g., "FJ001").
*   `name` (string): The name of the formula (e.g., "桂枝汤").
*   `composition` (list of strings): A list of herb IDs or names that make up the formula. It's recommended to use herb IDs for consistency (e.g., ["YC003", "YC004"]).
*   `actions` (list of strings): A list of the formula's primary actions or indications (e.g., ["解肌发表", "调和营卫"]).

**Example:**
```json
{ "id": "FJ001", "name": "桂枝汤", "composition": ["YC003", "YC004", "YC005", "YC006", "YC007"], "actions": ["解肌发表", "调和营卫"] }
{ "id": "FJ002", "name": "麻黄汤", "composition": ["麻黄", "桂枝", "杏仁", "甘草"], "actions": ["发汗解表", "宣肺平喘"] }
```

### `shuju/guanxi/yaocai_zhengzhuang_guanlian.txt` (Herb-Symptom Relationships)

Each line is a JSON object representing a relationship between a medicinal herb and a symptom.

*   `id` (string): A unique identifier for this specific relationship instance (e.g., "REL_YZ_001").
*   `herb_id` (string): The ID of the herb involved in the relationship (foreign key to `yaocai.txt`).
*   `symptom_id` (string): The ID of the symptom involved in the relationship (foreign key to `zhengzhuang.txt`).
*   `relation_type` (string): Describes the nature of the relationship (e.g., "treats", "alleviates", "indicated_for").

**Example:**
```json
{ "id": "REL_YZ_001", "herb_id": "YC001", "symptom_id": "ZZ003", "relation_type": "alleviates" }
{ "id": "REL_YZ_002", "herb_id": "YC008", "symptom_id": "ZZ001", "relation_type": "treats" }
```

This file will serve as the primary documentation for understanding the data structure within the `tcm_zhishitu_txt_mokuai` project.
