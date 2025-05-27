# tcm_kg_virtuoso_module/models/tcm_entity.py
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class TCMEntity:
    """
    中医知识图谱实体的数据模型。
    
    用于在服务层和API层之间传递结构化的实体数据。
    """
    uri: str  # 实体的唯一标识符 (URI)
    entity_types: List[str] = field(default_factory=list) # 实体类型列表 (例如: ["tcm_ont:Herb", "owl:NamedIndividual"])
    properties: Dict[str, Any] = field(default_factory=dict)  # 实体的属性字典，键为属性URI，值为属性值或值列表

    # 示例:
    # TCMEntity(
    #     uri="tcm_entity:Herb001",
    #     entity_types=["tcm_ont:Herb", "owl:NamedIndividual"],
    #     properties={
    #         "rdfs:label": "人参",
    #         "tcm_prop:hasTaste": ["tcm_entity:SweetTaste", "tcm_entity:SlightlyBitterTaste"],
    #         "tcm_prop:meridianTropism": ["tcm_entity:SpleenMeridian", "tcm_entity:LungMeridian"],
    #         "tcm_prop:hasEffect": [{"uri": "tcm_entity:Effect001", "rdfs:label": "大补元气"}], # 对象属性可以是字典或另一个TCMEntity实例
    #         "tcm_prop:dosage": "3-9g"
    #     }
    # )

    def __post_init__(self):
        # 可以在这里添加一些初始化后的校验逻辑，例如检查URI是否为空
        if not self.uri:
            raise ValueError("实体URI (uri) 不能为空。")
        if not self.entity_types:
            # 根据实际需求，可以决定是否强制要求类型，或者提供一个默认类型
            # print(f"警告: 实体 {self.uri} 未指定类型 (entity_types)。")
            pass # 允许没有显式类型，或者在后续处理中赋予默认类型
