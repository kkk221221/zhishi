# 中医知识图谱模块用户指南 (`tcm_kg_virtuoso_module`)

## 1. 简介 (Introduction)

欢迎使用 `tcm_kg_virtuoso_module`！本模块是一个Python工具集，旨在帮助您构建、管理和访问专门为中医药领域设计的知识图谱。它利用Virtuoso作为底层的三元组数据库，并通过FastAPI提供了一套便捷的RESTful API接口，方便数据的导入、查询和操作。

本指南将引导您完成模块的安装、设置、API服务的运行，并通过示例展示如何使用API接口和批量导入脚本。

**核心功能**:
- **数据存储**: 使用Virtuoso存储RDF三元组。
- **API服务**: 提供HTTP接口进行实体和关系的增删查改。
- **批量导入**: 支持通过脚本从文件批量导入三元组数据。
- **模块化设计**: 清晰的架构，易于理解和扩展。

## 2. 安装与设置 (Installation & Setup)

### 2.1. 依赖项列表 (Prerequisites)

在开始之前，请确保您的系统环境中已安装以下软件和库：

- **Python**: 版本 3.8 或更高。
- **pip**: Python包安装器 (通常随Python一同安装)。
- **Virtuoso**: OpenLink Virtuoso (开源版或商业版)。
    - 确保Virtuoso实例正在运行，并且其SPARQL endpoint是可访问的。
    - 用于数据写入的用户（例如`dba`）需要具有SPARQL Update权限。
- **关键Python库**:
    - `fastapi`: 用于构建API。
    - `uvicorn[standard]`: ASGI服务器，用于运行FastAPI应用。
    - `SPARQLWrapper`: 与Virtuoso的SPARQL端点交互。
    - `python-dotenv`: 用于从`.env`文件加载环境变量。
    - `pydantic`: 用于API数据校验和模型定义。

您可以通过项目根目录下的 `requirements.txt` (如果提供) 文件来安装Python依赖：
```bash
pip install -r requirements.txt 
```
如果 `requirements.txt` 未提供，您可以手动安装上述库：
```bash
pip install fastapi uvicorn[standard] SPARQLWrapper python-dotenv pydantic
```

### 2.2. Virtuoso数据库设置提示 (Virtuoso Database Setup)

- **SPARQL Endpoint**: 确认您的Virtuoso SPARQL端点URL (例如 `http://localhost:8890/sparql`)。
- **权限**: 用于API和脚本的用户（在`.env`中配置）必须对目标图（例如 `DEFAULT_GRAPH_URI` 中指定的图）具有读写权限。对于Virtuoso，`dba`用户通常拥有所有权限。如果使用其他用户，请确保在Virtuoso Conductor或通过`isql`授予相应权限。
    ```sql
    -- 示例：授予用户sparql_user对特定图的写权限
    GRANT SPARQL_UPDATE ON GRAPH <http://localhost:8890/TCMKG> TO "sparql_user";
    GRANT SPARQL_LOAD_SERVICE_DATA TO "sparql_user"; -- 如果需要LOAD命令
    ```

### 2.3. 项目配置 (`.env` 文件)

本模块使用 `.env` 文件来管理敏感配置和环境特定参数。

1.  **创建 `.env` 文件**:
    在项目根目录下，复制 `.env.example` 文件并将其重命名为 `.env`。
    ```bash
    cp .env.example .env
    ```

2.  **编辑 `.env` 文件**:
    打开 `.env` 文件并根据您的环境修改以下参数：

    -   `VIRTUOSO_URL`: Virtuoso SPARQL端点的完整URL。
        ```env
        VIRTUOSO_URL="http://localhost:8890/sparql"
        ```
    -   `VIRTUOSO_USER`: 连接Virtuoso的用户名。
        ```env
        VIRTUOSO_USER="dba"
        ```
    -   `VIRTUOSO_PASSWORD`: 连接Virtuoso的密码。
        ```env
        VIRTUOSO_PASSWORD="your_virtuoso_password" 
        ```
    -   `DEFAULT_GRAPH_URI`: 存储数据的默认图的URI。
        ```env
        DEFAULT_GRAPH_URI="http://localhost:8890/TCMKG"
        ```
    -   `TCM_ONT_PREFIX`, `TCM_PROP_PREFIX`, `TCM_ENTITY_PREFIX`: (可选) 如果您有自定义的中医药本体，可以在此定义基础URI前缀。这些主要用于 `core/config.py` 中的 `NAMESPACES` 字典，方便在代码中引用。
        ```env
        TCM_ONT_PREFIX="http://your.ontology.prefix/tcm#"
        TCM_PROP_PREFIX="http://your.property.prefix/tcm#"
        TCM_ENTITY_PREFIX="http://your.entity.prefix/tcm/"
        ```
        如果这些自定义前缀未设置，模块会使用 `core/config.py` 中定义的默认示例值。

## 3. 运行API服务 (Running the API Service)

配置完成后，您可以使用 `uvicorn` 来启动FastAPI应用。

1.  **启动命令**:
    在项目根目录下运行以下命令：
    ```bash
    uvicorn tcm_kg_virtuoso_module.main_fastapi_app:app --reload --host 0.0.0.0 --port 8000
    ```
    -   `tcm_kg_virtuoso_module.main_fastapi_app:app`: 指向FastAPI应用实例 (`app`) 所在的文件路径和变量名。
    -   `--reload`: 开发模式下启用自动重载，当代码更改时服务器会自动重启。生产环境请移除此选项。
    -   `--host 0.0.0.0`: 使服务可以从网络中的任何IP地址访问（如果防火墙允许）。
    -   `--port 8000`: 指定服务监听的端口。

2.  **访问API文档**:
    服务启动后，您可以通过浏览器访问自动生成的交互式API文档：
    -   **Swagger UI**: `http://localhost:8000/docs`
    -   **ReDoc**: `http://localhost:8000/redoc`

    在这些页面上，您可以查看所有可用的API端点、请求参数、响应模型，并直接进行API调用测试。

## 4. API接口使用示例 (API Usage Examples)

以下示例展示了如何使用 `curl` 或 Python `requests` 库与关键API端点进行交互。

### 4.1. 创建实体 (POST /api/v1/entities/)

创建一个新的草药实体。

**请求体示例 (`application/json`)**:
```json
{
  "uri_suffix": "Gancao",
  "entity_type_key_for_uri": "tcm_entity", 
  "entity_types": [
    "http://example.com/ontology/tcm#Herb",
    "http://www.w3.org/2002/07/owl#NamedIndividual"
  ],
  "properties": {
    "http://www.w3.org/2000/01/rdf-schema#label": "甘草",
    "http://example.com/ontology/tcm#hasTaste": "甘",
    "http://example.com/ontology/tcm#meridianTropism": [
      "http://example.com/entity/tcm/SpleenMeridian",
      "http://example.com/entity/tcm/LungMeridian"
    ]
  }
}
```

**`curl` 示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/entities/" \
-H "Content-Type: application/json" \
-d '{
  "uri_suffix": "Gancao",
  "entity_type_key_for_uri": "tcm_entity",
  "entity_types": ["http://example.com/ontology/tcm#Herb"],
  "properties": {
    "http://www.w3.org/2000/01/rdf-schema#label": "甘草",
    "http://example.com/ontology/tcm#hasTaste": "甘"
  }
}'
```

**Python `requests` 示例**:
```python
import requests
import json

url = "http://localhost:8000/api/v1/entities/"
payload = {
  "uri_suffix": "GancaoPy",
  "entity_type_key_for_uri": "tcm_entity",
  "entity_types": ["http://example.com/ontology/tcm#Herb"],
  "properties": {
    "http://www.w3.org/2000/01/rdf-schema#label": "甘草 (Python)",
    "http://example.com/ontology/tcm#hasTaste": "甘"
  }
}
response = requests.post(url, json=payload)
print(response.status_code)
print(response.json())
```

**预期响应示例 (Status 201 Created)**:
```json
{
  "uri": "http://your.entity.prefix/tcm/Gancao", // 或配置中的默认前缀 + Gancao
  "entity_types": ["http://example.com/ontology/tcm#Herb"],
  "properties": {
    "http://www.w3.org/2000/01/rdf-schema#label": "甘草",
    "http://example.com/ontology/tcm#hasTaste": "甘"
  }
}
```

### 4.2. 获取实体 (GET /api/v1/entities/{uri})

检索指定URI的实体信息。URI中的特殊字符需要进行URL编码。

**`curl` 示例** (假设实体URI为 `http://your.entity.prefix/tcm/Gancao`):
```bash
# URI需要URL编码，例如 : -> %3A, / -> %2F
# curl "http://localhost:8000/api/v1/entities/http%3A%2F%2Fyour.entity.prefix%2Ftcm%2FGancao"

# 如果你的curl版本和服务器配置支持，可以直接使用未编码的URI，但编码更安全
ENTITY_URI="http://your.entity.prefix/tcm/Gancao" 
curl "http://localhost:8000/api/v1/entities/${ENTITY_URI}"
```

**Python `requests` 示例**:
```python
import requests
# 假设之前创建的实体URI为 'http://your.entity.prefix/tcm/GancaoPy'
entity_uri = "http://your.entity.prefix/tcm/GancaoPy" 
# requests库会自动处理URL编码
response = requests.get(f"http://localhost:8000/api/v1/entities/{entity_uri}")
print(response.status_code)
if response.status_code == 200:
    print(response.json())
```

**预期响应示例 (Status 200 OK)**:
与创建实体时的响应体类似。

### 4.3. 创建关系 (POST /api/v1/relationships/)

在两个实体之间创建关系。

**请求体示例 (`application/json`)**:
```json
{
  "source_uri": "http://your.entity.prefix/tcm/Gancao",
  "predicate_uri": "http://example.com/ontology/tcm#hasEffect",
  "target_uri": "http://example.com/entity/tcm/TonifyQi" 
}
```
(假设 `http://example.com/entity/tcm/TonifyQi` 是一个已存在的“补气”功效实体URI)

**`curl` 示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/relationships/" \
-H "Content-Type: application/json" \
-d '{
  "source_uri": "http://your.entity.prefix/tcm/Gancao",
  "predicate_uri": "http://example.com/ontology/tcm#hasEffect",
  "target_uri": "http://example.com/entity/tcm/TonifyQi"
}'
```

**预期响应示例 (Status 201 Created)**:
```json
{
  "source_uri": "http://your.entity.prefix/tcm/Gancao",
  "predicate_uri": "http://example.com/ontology/tcm#hasEffect",
  "target_uri": "http://example.com/entity/tcm/TonifyQi",
  "properties": null 
}
```

### 4.4. 获取实体相关关系 (GET /api/v1/relationships/for-entity/{uri})

获取与指定实体相关的所有关系。

**`curl` 示例** (查询甘草的所有关系):
```bash
ENTITY_URI="http://your.entity.prefix/tcm/Gancao"
curl "http://localhost:8000/api/v1/relationships/for-entity/${ENTITY_URI}?direction=all"
```

**Python `requests` 示例**:
```python
import requests
entity_uri = "http://your.entity.prefix/tcm/Gancao"
params = {"direction": "all"} # outgoing, incoming, all
response = requests.get(f"http://localhost:8000/api/v1/relationships/for-entity/{entity_uri}", params=params)
print(response.status_code)
if response.status_code == 200:
    print(response.json())
```

**预期响应示例 (Status 200 OK)**:
```json
[
  {
    "source_uri": "http://your.entity.prefix/tcm/Gancao",
    "predicate_uri": "http://example.com/ontology/tcm#hasEffect",
    "target_uri": "http://example.com/entity/tcm/TonifyQi",
    "properties": null
  }
  // ... 其他与甘草相关的关系
]
```

### 4.5. 批量插入三元组 (POST /api/v1/bulk/triples)

**请求体示例 (`application/json`)**:
```json
{
  "triples": [
    {
      "subject": "http://your.entity.prefix/tcm/Renshen",
      "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
      "object_val": "http://example.com/ontology/tcm#Herb"
    },
    {
      "subject": "http://your.entity.prefix/tcm/Renshen",
      "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
      "object_val": "人参"
    },
    {
      "subject": "http://your.entity.prefix/tcm/Renshen",
      "predicate": "http://example.com/ontology/tcm#hasNumericalValue",
      "object_val": 100
    }
  ],
  "graph_uri": "http://localhost:8890/TCMKG_BulkTest" 
}
```
(如果 `graph_uri` 为 `null` 或不提供，则使用默认图。)

**`curl` 示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/bulk/triples" \
-H "Content-Type: application/json" \
-d '{
  "triples": [
    {"subject": "http://e.com/s1", "predicate": "http://p.com/p1", "object_val": "http://o.com/o1"},
    {"subject": "http://e.com/s1", "predicate": "http://p.com/label", "object_val": "Label S1"}
  ]
}'
```

**预期响应示例 (Status 200 OK)**:
```json
{
  "message": "成功处理 2 个三元组的批量插入请求。",
  "success": true
}
```

## 5. 使用批量导入脚本 (Using the Bulk Import Script)

模块提供了一个命令行脚本，用于从JSONL文件批量导入三元组数据到Virtuoso。

### 5.1. 脚本位置 (Script Location)

脚本位于项目内的 `scripts/bulk_import_to_virtuoso.py`。

### 5.2. 运行命令示例 (Example Command)

假设您在项目根目录下，并且有一个名为 `triples_data.jsonl` 的文件：

```bash
python scripts/bulk_import_to_virtuoso.py \
    --file-path ./triples_data.jsonl \
    --graph-uri "http://localhost:8890/MyCustomGraph" \
    --batch-size 200
```

如果 `--graph-uri` 未指定，则使用 `.env` 文件中配置的 `DEFAULT_GRAPH_URI`。
如果 `--batch-size` 未指定，默认为100。

### 5.3. 命令行参数详解 (Command-Line Arguments)

-   `--file-path <path_to_file>`: (必需) 包含三元组数据的JSONL文件路径。
-   `--graph-uri <uri>`: (可选) 目标图的URI。如果省略，则使用配置文件中定义的 `DEFAULT_GRAPH_URI`。
-   `--batch-size <integer>`: (可选) 每批次插入的三元组数量。默认为100。

### 5.4. 输入文件格式说明 (Input File Format)

输入文件 (`--file-path` 指定的文件) 必须是 **JSONL** 格式，即每行一个有效的JSON对象。
每个JSON对象代表一个三元组，并应包含以下键：
-   `subject`: (字符串) 三元组的主语URI。
-   `predicate`: (字符串) 三元组的谓语URI。
-   `object_val`: (字符串, 数字, 或布尔值) 三元组的宾语。
    -   如果宾语是URI，请提供完整的URI字符串 (例如 `"http://example.com/entity/SomeResource"`)。
    -   如果宾语是字面量，请提供字符串 (例如 `"这是一个标签"`)、数字 (例如 `123`, `3.14`) 或布尔值 (`true`, `false`)。脚本和后续的服务层会尝试正确处理这些类型。

**示例 `triples_data.jsonl`**:
```jsonl
{"subject": "http://example.com/entity/herb/H001", "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "object_val": "http://example.com/ontology/tcm#Herb"}
{"subject": "http://example.com/entity/herb/H001", "predicate": "http://www.w3.org/2000/01/rdf-schema#label", "object_val": "人参"}
{"subject": "http://example.com/entity/herb/H001", "predicate": "http://example.com/ontology/tcm#hasCI", "object_val": true}
{"subject": "http://example.com/entity/herb/H001", "predicate": "http://example.com/ontology/tcm#stockCount", "object_val": 500}
```

### 5.5. 未来功能参数 (`--data-type`, `--source-path`)

脚本中还定义了 `--data-type` 和 `--source-path` 参数，这些是为未来通过 `ImportExportService` 的 `import_from_processed_data` 方法导入更结构化数据（例如从处理后的文本或JSON文件）预留的。目前，该服务层方法是占位符，因此这些参数尚不能完全发挥作用。

## 6. 故障排查与常见问题 (Troubleshooting & FAQ)

-   **Virtuoso连接问题**:
    -   **错误**: `EndPointNotFound`, `SPARQLWrapperException` (包含 "Connection refused" 或 "Failed to establish a new connection")。
    -   **排查**:
        -   确认Virtuoso服务正在运行。
        -   检查 `.env` 文件中的 `VIRTUOSO_URL` 是否正确，并且网络可达。
        -   检查防火墙设置是否允许访问Virtuoso端口 (默认为 `8890` HTTP, `1111` SQL)。
        -   确认 `VIRTUOSO_USER` 和 `VIRTUOSO_PASSWORD` 正确，且该用户有权访问SPARQL端点和目标图。

-   **Python环境/依赖问题**:
    -   **错误**: `ModuleNotFoundError`。
    -   **排查**:
        -   确保您已在正确的Python虚拟环境中安装了所有必要的依赖库 (参见2.1节)。
        -   如果您从 `tcm_kg_virtuoso_module` 包外部运行脚本或应用，请确保该包的路径已添加到 `PYTHONPATH` 环境变量中，或者脚本内部正确处理了 `sys.path` (如 `scripts/bulk_import_to_virtuoso.py` 中所示)。

-   **API返回422 Unprocessable Entity**:
    -   **原因**: 请求体不符合API端点定义的Pydantic schema。
    -   **排查**: 仔细检查API文档 (`/docs`) 中对应端点的请求体模型，确保您的请求JSON结构和数据类型正确。响应体通常会包含详细的错误位置和原因。

-   **批量导入脚本权限问题**:
    -   **错误**: 脚本在读取文件或写入数据库时报告权限错误。
    -   **排查**:
        -   确保运行脚本的用户对输入的JSONL文件有读权限。
        -   确保Virtuoso用户对目标图有写权限。

---
如有其他问题或需要进一步协助，请查阅相关组件的文档或联系模块开发者。Okay, I have created the `user_guide.md` file with the content you provided.
