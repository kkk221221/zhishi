# 中医知识图谱模块架构 (`tcm_kg_virtuoso_module`)

## 1. 引言 (Introduction)

`tcm_kg_virtuoso_module` 是一个专门为构建、管理和访问中医知识图谱（TCM Knowledge Graph）而设计的Python模块。它旨在提供一套结构清晰、易于扩展的工具集，支持从中医药相关的原始数据（如古籍文献、现代研究、临床病例）中提取信息，构建RDF三元组，并将其存储到Virtuoso三元组数据库中。此外，该模块还通过FastAPI提供了一套RESTful API，方便上层应用查询和操作知识图谱数据。

本模块的核心目标是：
- **标准化数据表示**：通过定义统一的数据模型（实体、关系）来表示中医知识。
- **模块化组件设计**：各功能层分离，易于维护和独立开发。
- **便捷数据访问**：封装SPARQL查询和更新的复杂性，提供简洁的服务接口。
- **API驱动交互**：通过Web API暴露图谱能力，支持多样化的应用场景。
- **可扩展性**：预留接口和设计，方便未来功能的添加和完善。

## 2. 整体分层架构 (Overall Layered Architecture)

本模块采用典型的分层架构设计，以实现关注点分离 (Separation of Concerns) 和高内聚低耦合 (High Cohesion, Low Coupling) 的目标。主要分为以下几个层次：

```
+---------------------+
|     API Layer       |  (FastAPI 应用, 路由, Schemas)
|  (api, main_fastapi_app) |
+---------------------+
        /|\
         | (依赖注入, 数据模型)
        \|/
+---------------------+
|   Service Layer     |  (业务逻辑: Entity, Relationship, Import/Export, Ontology services)
|     (services)      |
+---------------------+
        /|\
         | (数据模型, SPARQL构建/执行)
        \|/
+---------------------+
| Data Access Layer   |  (VirtuosoConnector, SparqlBuilder)
|     (graph_db)      |
+---------------------+
        /|\
         | (数据库连接配置)
        \|/
+---------------------+
|    Core Layer       |  (配置管理: config.py, .env)
|       (core)        |
+---------------------+
        /|\ /|\
         |   | (数据模型定义, 工具函数)
        \|/ \|/
+---------------------+  +---------------------+
|    Models Layer     |  |    Utils Layer      |
|      (models)       |  |      (utils)        |
+---------------------+  +---------------------+
```

- **核心层 (Core Layer)**：提供基础配置。
- **数据访问层 (Data Access Layer)**：直接与Virtuoso数据库交互。
- **模型层 (Models Layer)**：定义核心数据结构。
- **工具层 (Utils Layer)**：提供通用的辅助函数。
- **服务层 (Service Layer)**：封装核心业务逻辑和操作流程。
- **API层 (API Layer)**：通过FastAPI暴露HTTP接口。

## 3. 各层详解 (Detailed Description of Each Layer)

### 3.1. 核心层 (`core`)

- **功能**: 管理模块的基础配置信息。
- **主要组件**:
    - `config.py`: 从环境变量（通过`.env`文件加载）或默认值中读取数据库连接参数（URL、用户、密码）、默认图URI、命名空间前缀 (Namespaces) 等。提供 `get_sparql_prefixes()` 函数生成SPARQL查询中常用的 `PREFIX` 声明。
- **交互**: 被所有需要配置信息的其他层（尤其是 `graph_db` 和 `services`）使用。

### 3.2. 数据访问层 (`graph_db`)

- **功能**: 封装与Virtuoso数据库的直接交互，包括连接管理、SPARQL查询的构建和执行。
- **主要组件**:
    - `virtuoso_connector.py`: 包含 `VirtuosoConnector` 类，使用 `SPARQLWrapper` 库来建立与Virtuoso的连接，并执行SELECT、CONSTRUCT、UPDATE等类型的SPARQL查询。处理认证和基本的错误捕获。
    - `sparql_builder.py`: 提供辅助函数（如 `build_insert_triples_sparql`, `build_select_entity_properties_sparql`, `build_delete_triples_sparql`）来动态构建SPARQL查询语句。包含一个内部函数 `_format_term` 用于正确格式化URI和字面量。
    - `sparql_templates/` (目录): 规划用于存放更复杂的、预定义的SPARQL查询模板文件（当前为空）。
- **交互**:
    - 依赖 `core.config` 获取数据库连接参数和命名空间。
    - 被 `services` 层调用以执行实际的数据库操作。

### 3.3. 模型层 (`models`)

- **功能**: 定义模块核心的数据结构，用于在各层之间传递结构化数据。
- **主要组件**:
    - `tcm_entity.py`: 定义 `TCMEntity` dataclass，表示知识图谱中的一个实体，包含URI、类型列表 (entity_types) 和属性字典 (properties)。
    - `tcm_relationship.py`: 定义 `TCMRelationship` dataclass，表示实体间的一个关系 (三元组)，包含源实体URI、谓词URI、目标URI/字面量，以及可选的关系自身属性。
- **交互**:
    - 被 `services` 层用于封装业务逻辑操作的数据对象。
    - 被 `api` 层的 schemas 模块引用，用于定义API请求和响应体的数据结构。

### 3.4. 工具层 (`utils`)

- **功能**: 提供通用的辅助函数，支持其他模块的功能实现。
- **主要组件**:
    - `uri_utils.py`: 包含 `generate_entity_uri` (根据配置和实体名称生成URI) 和 `validate_uri_format` (基础URI格式校验) 等函数。
    - `rdf_utils.py`: (当前为占位符) 规划用于存放RDF数据处理相关的工具函数，例如将Python对象批量转换为三元组列表，或将SPARQL查询结果解析为数据模型对象等。
- **交互**:
    - `uri_utils.py` 被 `services` 层和 `api` 层用于生成和校验URI。
    - `rdf_utils.py` (未来) 可能会被 `services` 层广泛使用。

### 3.5. 服务层 (`services`)

- **功能**: 封装模块的核心业务逻辑，协调数据访问层、模型层和工具层来完成具体操作。
- **主要组件**:
    - `entity_service.py` (`EntityService`): 处理实体的增删查改 (CRUD) 操作。例如，`add_entity` 方法接收 `TCMEntity` 对象，将其转换为三元组并存入数据库；`get_entity_by_uri` 方法从数据库检索实体数据并组装成 `TCMEntity` 对象。
    - `relationship_service.py` (`RelationshipService`): 处理实体间关系的增删查操作。例如，`add_relationship` 添加三元组，`get_relationships_for_entity` 查询与特定实体相关的关系。
    - `import_export_service.py` (`ImportExportService`): 提供批量数据操作功能。`bulk_insert_triples` 方法支持批量插入三元组。`import_from_processed_data` (当前为占位符) 规划用于从结构化文件导入数据。
    - `ontology_service.py` (`OntologyService` - 可选，当前为初步实现): 用于通过代码管理本体（RDFS/OWL Class, Property等）。包含 `add_class` 和 `add_property` 等方法。
- **交互**:
    - 调用 `graph_db` 层的 `VirtuosoConnector` 和 `sparql_builder` 来与数据库交互。
    - 使用 `models` 层定义的 `TCMEntity` 和 `TCMRelationship` 作为数据载体。
    - 可能使用 `utils` 层的辅助函数。
    - 被 `api` 层调用以执行具体的业务操作，是API路由处理函数的直接服务提供者。
    - 也可被 `scripts` 中的命令行脚本直接调用。

### 3.6. API层 (`api` 和 `main_fastapi_app.py`)

- **功能**: 基于 FastAPI 框架，将服务层的功能暴露为RESTful HTTP API接口。
- **主要组件**:
    - `main_fastapi_app.py`: FastAPI应用的入口点，初始化FastAPI应用实例，配置应用级别的元数据（如标题、描述、OpenAPI标签），并注册V1版本的API路由。包含应用启动事件 (`startup_event`) 和根节点 (`/`)。
    - `api/schemas.py`: 定义API请求和响应体的数据模型 (Pydantic models)，如 `EntitySchema`, `CreateEntitySchema`, `RelationshipSchema`, `BulkInsertTriplesRequest` 等。这些模型用于数据校验、序列化和OpenAPI文档生成。
    - `api/dependencies.py`: 定义FastAPI的依赖注入项。通过 `Depends` 机制，为API路由处理函数提供服务实例 (如 `EntityService`, `VirtuosoConnector` 等) 的单例或按需实例。使用 `@lru_cache` 缓存服务实例以提高效率。
    - `api/v1/` (目录): 存放V1版本的API路由模块。
        - `entity_routes.py`: 包含与实体相关的API端点 (如 `POST /v1/entities/`, `GET /v1/entities/{uri}`, `DELETE /v1/entities/{uri}`), 使用 `APIRouter` 进行组织。
        - `relationship_routes.py`: 包含与关系相关的API端点 (如 `POST /v1/relationships/`, `GET /v1/relationships/for-entity/{uri}`, `POST /v1/relationships/delete`)。
        - `bulk_routes.py`: 包含批量操作相关的API端点 (如 `POST /v1/bulk/triples`)。
- **交互**:
    - `main_fastapi_app.py` 导入并注册 `api/v1/` 中的各个路由模块。
    - 路由模块 (`entity_routes.py` 等) 使用 `dependencies.py` 来获取服务实例，并调用相应的服务层方法来处理请求。
    - `schemas.py` 中定义的Pydantic模型被路由模块用于请求体验证和响应体序列化。
    - 最终用户或其他服务通过HTTP请求与这些API端点交互。

## 4. 层间交互总结 (Interactions Between Layers)

- **API Layer** -> **Service Layer**: API路由处理函数通过依赖注入获取服务实例，并调用服务方法处理业务逻辑。API层使用Pydantic模型 (`schemas.py`)进行数据校验和序列化，服务层通常使用内部数据模型 (`models/tcm_entity.py` 等)。
- **Service Layer** -> **Data Access Layer**: 服务层使用 `VirtuosoConnector` 执行由 `sparql_builder` 构建的SPARQL查询。
- **Service Layer** -> **Models Layer**: 服务层方法接收和返回在 `models` 中定义的 `TCMEntity` 或 `TCMRelationship` 对象。
- **Service Layer** -> **Utils Layer**: 服务层可能调用 `uri_utils.py` 等工具函数。
- **Data Access Layer** -> **Core Layer**: `VirtuosoConnector` 从 `core.config` 获取数据库连接信息和命名空间。
- **All Layers** (potentially) -> **Core Layer**: 任何需要配置信息的组件都可以依赖 `core.config`。

## 5. API 使用概要 (API Usage Summary)

本模块通过 `main_fastapi_app.py` 启动一个 FastAPI 应用，提供 RESTful API。
- **API文档**: 启动应用后，可以通过浏览器访问 `/docs` (Swagger UI) 或 `/redoc` (ReDoc) 路径查看自动生成的交互式API文档。
- **主要端点分类**:
    - **实体管理 (`/api/v1/entities`)**: 支持创建、检索、删除单个实体。
    - **关系管理 (`/api/v1/relationships`)**: 支持创建、检索、删除关系。
    - **批量操作 (`/api/v1/bulk`)**: 支持批量插入三元组等。
- **请求与响应**: API使用JSON格式进行数据交换，并通过Pydantic模型 (`schemas.py`)进行严格的数据校验和序列化。

## 6. 配置 (`.env` File)

模块的核心配置（如Virtuoso数据库连接参数、默认图URI、自定义命名空间等）通过 `.env` 文件进行管理。项目根目录下提供了一个 `.env.example` 文件作为模板。实际部署时，应复制此文件为 `.env` 并填入具体配置值。
`core/config.py` 负责加载 `.env` 文件中的变量，并提供给模块的其他部分使用。

主要配置项包括：
- `VIRTUOSO_URL`
- `VIRTUOSO_USER`
- `VIRTUOSO_PASSWORD`
- `DEFAULT_GRAPH_URI`
- 自定义本体相关的命名空间前缀 (如 `TCM_ONT_PREFIX`, `TCM_PROP_PREFIX`, `TCM_ENTITY_PREFIX`)

## 7. 未来扩展点 (Future Extension Points)

- **完善 `ImportExportService`**:
    - 完整实现 `import_from_processed_data` 方法，支持从不同类型的结构化文件（如从 `src/data_layer/data/processed/` 目录下的文本文件、JSON文件等）解析并导入数据到知识图谱。
- **完善 `OntologyService`**:
    - 扩展本体服务，提供更全面的本体管理功能，如获取类别层级、属性详情、删除类别/属性、定义更复杂的OWL约束等。
- **更复杂的查询接口**:
    - 在服务层和API层添加支持更复杂查询模式的接口，例如基于特定条件组合查询实体、路径查询、子图提取等。
- **数据校验与清洗**:
    - 在导入过程中集成更强的数据校验和清洗逻辑。
- **安全性与认证**:
    - 为API层添加认证和授权机制。
- **异步任务处理**:
    - 对于耗时较长的操作（如大规模批量导入），可以考虑引入 Celery 等任务队列进行异步处理。
- **测试覆盖**:
    - 进一步提高单元测试和集成测试的覆盖率。

## 8. 脚本 (`scripts`)

- **`scripts/bulk_import_to_virtuoso.py`**: 提供了一个命令行工具，用于批量导入三元组数据到Virtuoso。它直接调用 `ImportExportService` 的功能。

---
此文档概述了 `tcm_kg_virtuoso_module` 的主要架构和组件，旨在为开发者提供清晰的指引。
