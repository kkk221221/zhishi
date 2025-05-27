from fastapi import APIRouter, HTTPException, status, Depends
from typing import Any, Dict
from tcm_kg_virtuoso_module.api.request_schemas import EntityCreate
from tcm_kg_virtuoso_module.core.graph_operations import add_entity
from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager

router = APIRouter()

async def get_connection_manager() -> VirtuosoConnectionManager:
    return VirtuosoConnectionManager()

@router.post("/entities", status_code=status.HTTP_201_CREATED)
async def create_entity_endpoint(
    entity_create_data: EntityCreate, 
    conn_manager: VirtuosoConnectionManager = Depends(get_connection_manager)
):
    try:
        entity_payload_dict: Dict[str, Any] = {
            "entity_type_name": entity_create_data.entity_type_name,
            "entity_label": entity_create_data.label,
            "entity_properties": entity_create_data.properties if entity_create_data.properties is not None else {},
            "source_details": entity_create_data.source_details.model_dump(),
            "entity_id_args": entity_create_data.entity_id_args
        }
        new_entity_uri = add_entity(entity_payload_dict, conn_manager)
        return {"uri": new_entity_uri, "message": "Entity created successfully"}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # Basic error logging, consider using a proper logger
        print(f"ERROR creating entity: {e}") 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An internal error occurred: {type(e).__name__}"
        )
