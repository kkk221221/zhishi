# tcm_kg_virtuoso_module/models/tcm_relationship.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class TCMRelationship:
    """
    中医知识图谱中实体间关系的数据模型。

    用于表示和传递结构化的关系数据。
    """
    source_uri: str      # 源实体的URI
    predicate_uri: str   # 谓词的URI (表示关系的类型)
    target_uri: str      # 目标实体的URI (可以是另一个实体或一个字面量节点的标识符)
    
    # 关系自身的属性，例如关系的发生时间、强度等 (可选)
    # 注意: 在标准的RDF三元组模型中，关系本身通常不直接拥有属性。
    # 如果需要为关系附加属性，通常采用RDF*的方法或者将关系具体化 (reification) 为一个实体。
    # 此处保留properties字段是为了灵活性，但使用时需考虑图数据库的实际支持情况。
    properties: Optional[Dict[str, Any]] = field(default_factory=dict)

    # 示例:
    # TCMRelationship(
    #     source_uri="tcm_entity:Herb001",      # 例如：人参
    #     predicate_uri="tcm_prop:hasEffect", # 例如：具有功效
    #     target_uri="tcm_entity:Effect001",    # 例如：大补元气 (作为独立的实体)
    #     properties={"confidence": 0.9}      # 可选的关系自身属性
    # )
    #
    # 或者，如果目标是字面量 (虽然通常字面量作为实体属性，但这里为了演示TCMRelationship的通用性)
    # TCMRelationship(
    #     source_uri="tcm_entity:Recipe001",
    #     predicate_uri="tcm_prop:hasInstruction",
    #     target_uri='"先煎麻黄去上沫，纳诸药，煮取二升半，分温三服。"' # 目标是一个字面量字符串
    # )

    def __post_init__(self):
        # 初始化后的校验逻辑
        if not self.source_uri:
            raise ValueError("源实体URI (source_uri) 不能为空。")
        if not self.predicate_uri:
            raise ValueError("谓词URI (predicate_uri) 不能为空。")
        if not self.target_uri:
            raise ValueError("目标URI (target_uri) 不能为空。")
