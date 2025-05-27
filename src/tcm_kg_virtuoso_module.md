中医知识图谱：存储与修改模块（基于 Virtuoso）
该模块将作为从各种来源提取的结构化中医知识的持久化和管理的后端。
tcm_kg_virtuoso_module/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── endpoints.py        # Defines the RESTful API endpoints (e.g., /entities, /relationships)
│   └── request_schemas.py  # (Optional) Validation schemas for request bodies (e.g., Pydantic models)
├── core/
│   ├── __init__.py
│   ├── connection_manager.py # Handles Virtuoso connection pooling and management
│   ├── data_formatter.py     # Converts input to RDF, builds SPARQL queries
│   ├── sparql_executor.py    # Executes SPARQL queries against Virtuoso
│   ├── source_manager.py     # Manages source information, named graphs, and provenance
│   └── uri_minter.py         # Generates unique URIs for entities and sources
├── rdf_templates/            # (Optional) Directory for SPARQL query templates if they are complex
│   ├── __init__.py
│   └── insert_entity.sparql  # Example SPARQL template
├── utils/
│   ├── __init__.py
│   └── rdf_helper.py         # (Optional) Helper functions for RDF, URI manipulation, etc.
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuration (Virtuoso connection details, URI base, prefixes)
└── main.py                   # (Optional) Entry point if the module is run as a standalone service (e.g., Flask/FastAPI app)
组件说明：
tcm_kg_virtuoso_module/ ：Python 模块的根目录。
__init__.py ：使目录成为 Python 包。
api/ ：包含与 API 接口相关的所有代码。
endpoints.py ：实现 HTTP 端点处理程序（例如，使用 Flask、FastAPI 或其他 Web 框架）。这些处理程序将协调对核心服务的调用。
request_schemas.py ：（推荐）定义用于验证传入请求有效负载的数据结构（例如，使用 Pydantic），确保数据在处理之前符合预期的格式。
core/ ：包含主要业务逻辑和与 Virtuoso 的交互。
connection_manager.py ：管理与 Virtuoso 的连接。
data_formatter.py ：负责将输入数据（如来自 API 的 JSON）转换为 RDF 三元组并构建必要的 SPARQL 查询。
sparql_executor.py ：获取生成的 SPARQL 查询并针对 Virtuoso 实例执行它们，处理事务。
source_manager.py ：专门处理创建和链接源信息，包括管理命名图形 URI 和有关源的元数据。
uri_minter.py ：根据预定义的模式为新实体和源生成唯一且一致的 URI。
rdf_templates/ ：（可选）如果您的 SPARQL 查询变得复杂或众多，您可以将它们作为模板文件存储在这里。
utils/ ：用于可能在模块不同部分之间共享的实用程序功能。
rdf_helper.py ：可能包含用于创建 RDF 文字、转义 URI 字符串或其他 RDF 相关任务的常用函数。
config/ ：用于配置文件。
settings.py ：存储配置，如 Virtuoso 端点 URL、凭据、默认 URI 前缀（例如， tcm-entity: 、 tcm-ontology: :）等。
main.py ：（可选）如果此模块要作为独立的 Web 服务运行，则此文件将初始化并运行 Web 应用程序（例如，用于 FastAPI 的 Uvicorn 或用于开发的 Flask 内置服务器）。





1.核心要求
全面的数据存储 ：
存储多种中医实体：疾病、证候、症状、体质、中药、方剂、治法、经络、穴位、净化病机、医家、理论（如阴阳、五）元素）。
存储实体属性：例如中药：性味归经（性味、归经）、功效主治（功效、主治）；方剂：组成（组合），功用（功能）。
存储实体之间的关系：例如，“治疗”（治疗）、“组成”（组成）、“导致”（导致）、“继承”（表现为）、“传承于”（继承自）。
知识出处（来源追踪） ：
每条知识（实体、属性、关系）都必须可追溯到其原始来源。
存储原文链接（例如古籍中的具体章节/段落、现代文献引文、临床病例 ID 等）。
存储从中提取信息的原始文本片段 。
存储接口 ：
添加具有其属性的新实体的功能。
在实体之间添加新关系的功能。
将存储的信息与其来源关联的机制。
修改接口 ：
更新现有实体的功能（例如，添加/更改属性、更正信息）。
更新现有关系的功能。
删除实体或关系的功能（考虑数据完整性）。
更新/更正与数据相关的源信息的功能。
底层技术 ：Virtuoso OpenSource（意味着使用 RDF、SPARQL）。
2. Virtuoso 数据模型（基于 RDF）
我们将使用 RDF（资源描述框架）来建模中医知识。Virtuoso 擅长存储和查询 RDF 数据。

URI（统一资源标识符） ：

每个实体（例如，特定草药、特定疾病）都有唯一的 URI。示例： http://tcm.example.org/entity/中药/麻黄 。
本体术语（类和属性）也具有 URI。示例： http://tcm.example.org/ontology/hasTaste 。
来源也将通过 URI 进行标识。例如： http://tcm.example.org/source/古籍/伤寒杂病论/太阳病篇/段落5 。
表示实体、属性和关系 ：

实体 ：实体是类的一个实例。
示例： tcm-entity:麻黄 rdf:type tcm-ontology:中药 .
属性 ：属性表示为将实体 URI 链接到文字值或另一个 URI 的 RDF 属性。
示例： tcm-entity:麻黄 tcm-ontology:hasTaste "辛"^^xsd:string .
tcm-entity:麻黄 tcm-ontology:归经 tcm-entity:经络/肺经 .
关系 ：关系也是链接两个实体 URI 的 RDF 属性。
示例： tcm-entity:麻黄汤 tcm-ontology:主治 tcm-entity:疾病/太阳病 .
存储源信息（出处） ：

命名图 ：这是 Virtuoso 推荐的溯源方法。从不同文本上下文中提取的每条信息（或一组相关的三元组）将存储在其各自的命名图中。命名图的 URI 将代表来源。
结构 ：
代码段

# Example Named Graph URI for a source
GRAPH <http://tcm.example.org/source/古籍/伤寒杂病论/方剂篇/麻黄汤条文> {
    tcm-entity:麻黄 tcm-ontology:性 "温"^^xsd:string .
    tcm-entity:麻黄 tcm-ontology:味 "辛"^^xsd:string .
    tcm-entity:麻黄 tcm-ontology:味 "微苦"^^xsd:string .
    tcm-entity:方剂/麻黄汤 tcm-ontology:组成 tcm-entity:中药/麻黄 .
}

# Metadata about the source itself
<http://tcm.example.org/source/古籍/伤寒杂病论/方剂篇/麻黄汤条文>
    rdf:type tcm-ontology:SourceContext ;
    dcterms:bibliographicCitation "《伤寒杂病论》方剂篇 - 麻黄汤条文" ;
    tcm-ontology:hasOriginalText "麻黄，性温，味辛、微苦。麻黄汤组成：麻黄、桂枝..." ; # Original text snippet
    tcm-ontology:sourceDocument <http://tcm.example.org/document/伤寒杂病论> .
这允许同时查询数据及其来源。dcterms dcterms:bibliographicCitation 和自定义 tcm-ontology:hasOriginalText 可以分别存储参考文献和摘要。
3.模块组件
连接管理器 ：
处理 Virtuoso 的连接池和管理。
数据格式化服务 ：
将输入数据（例如来自 API 的 JSON）转换为 RDF 三元组（N-Triples、Turtle 或 Virtuoso 可以接收的其他 RDF 格式）。
构建用于插入、更新和删除操作的 SPARQL 查询。
SPARQL 执行引擎 ：
针对 Virtuoso 实例执行生成的 SPARQL 查询。
处理原子操作的事务。
URI 铸造服务 ：
根据预定义模式或输入数据，为新实体和源生成唯一且一致的 URI。
源管理子模块 ：
具体处理源信息（命名图表、原始文本存储）的创建和链接。
4. API 设计（说明性 RESTful 端点）
这些端点将与模块组件交互，以在 Virtuoso 中执行操作。有效负载通常为 JSON。

基本网址 ： /api/v1/tcm/graph

4.1. 实体的存储和修改
POST /entities ：添加一个新实体。
请求主体示例（JSON） ：
JSON

{
  "type": "中药", // Maps to tcm-ontology:中药
  "label": "人参", // Used for rdfs:label and part of URI generation
  "attributes": [
    {"property": "hasTaste", "value": "甘"},
    {"property": "hasNature", "value": "微温"},
    {"property": "channelTropism", "value": ["脾经", "肺经", "心经"]} // Values can be literals or link to other entity URIs
  ],
  "source": {
    "citation": "《神农本草经》 - 上品 - 人参条",
    "originalText": "人参，味甘，微温。主补五脏...",
    "documentIdentifier": "SNBCJ_Vol1_Renshen" // Internal ID for the source document part
  }
}
操作 ：为“人参”创建新的 URI。为其类型和属性创建 RDF 三元组。所有这些三元组将被放置在一个新的命名图中，该图的 URI 可根据 source.documentIdentifier 创建或生成。有关来源的元数据（引文、原文）将链接到此命名图 URI。
PUT /entities/{entity_uri_encoded} ：更新现有实体。
请求正文 ：与 POST 类似，但指定要添加、更新或删除的属性。还应提供要添加的新属性的源信息。
操作 ：修改与实体相关的三元组。如果添加了来自新源的新属性，它们可能会被添加到新的命名图中；如果是更正操作，则可能会更新现有的源信息。
DELETE /entities/{entity_uri_encoded} ：删除实体及其关联属性。
操作 ：删除所有以实体 URI 为主体的三元组。该实体作为主体或客体的关联关系可能也需要处理（例如，删除或标记为悬空）。
4.2. 关系存储与修改
POST /relationships ：在两个现有实体之间添加新的关系。
请求主体示例（JSON） ：
JSON

{
  "subjectUri": "http://tcm.example.org/entity/方剂/麻黄汤",
  "predicate": "组成", // Maps to tcm-ontology:组成
  "objectUri": "http://tcm.example.org/entity/中药/麻黄",
  "source": {
    "citation": "《伤寒杂病论》 - 麻黄汤方",
    "originalText": "麻黄汤方：麻黄三两（去节），桂枝二两（去皮）...",
    "documentIdentifier": "SHL_MahuangTangRecipe"
  }
}
操作 ：在表示源的命名图中创建三元组 (<subjectUri> tcm-ontology:组成 <objectUri>) 。
DELETE /relationships ：删除特定关系。
请求正文 ：指定要删除的三元组的主体、谓词和对象，如果存在来自不同来源的多个相同三元组，则可能指定源图。
操作 ：从指定的命名图中删除指定的三元组。