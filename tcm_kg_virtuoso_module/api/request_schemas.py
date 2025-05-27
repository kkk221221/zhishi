# tcm_kg_virtuoso_module/api/request_schemas.py
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional

# Matches the structure needed for source_details in graph_operations.add_entity,
# which in turn matches the arguments of core.source_manager.create_source_metadata
class SourceModel(BaseModel):
    citation: str
    original_text: str 
    document_identifier: str
    source_type: str
    source_section: str
    source_subsection: str
    uri_args: Optional[List[str]] = None

# Main model for the POST /entities request body
# Designed to be easily transformable into the entity_data dict for graph_operations.add_entity
class EntityCreate(BaseModel):
    entity_type_name: str  # Changed from 'type' in user example to match add_entity
    label: str             # Matches 'entity_label' in add_entity
    properties: Optional[Dict[str, Any]] = {} # Matches 'entity_properties' in add_entity
    source_details: SourceModel # Matches 'source_details' in add_entity
    entity_id_args: Optional[List[str]] = None # Matches 'entity_id_args' in add_entity

    # Example of how this EntityCreate model might be used by the API endpoint:
    # entity_data_for_add_entity = {
    #     "entity_type_name": request_body.entity_type_name,
    #     "entity_label": request_body.label,
    #     "entity_properties": request_body.properties,
    #     "source_details": request_body.source_details.model_dump(), # Pydantic v2
    #     "entity_id_args": request_body.entity_id_args
    # }
