from urllib.parse import quote
from tcm_kg_virtuoso_module.config import settings

def mint_entity_uri(entity_type: str, entity_name: str, *args: str) -> str:
    # URL encode each path component to handle special characters, spaces, etc.
    # The `safe=''` argument ensures that even '/' characters in the components are encoded if they are not meant to be path separators.
    # However, for path segments, we usually want '/' to be a separator, so we encode them individually.
    encoded_entity_type = quote(entity_type, safe='')
    encoded_entity_name = quote(entity_name, safe='')
    encoded_args = [quote(arg, safe='') for arg in args]
    
    path_components = [encoded_entity_type, encoded_entity_name] + encoded_args
    return f"{settings.ENTITY_BASE_URI}{'/'.join(path_components)}"

def mint_source_uri(source_type: str, document_identifier: str, section: str, sub_section: str, *args: str) -> str:
    encoded_source_type = quote(source_type, safe='')
    encoded_document_identifier = quote(document_identifier, safe='')
    encoded_section = quote(section, safe='')
    encoded_sub_section = quote(sub_section, safe='')
    encoded_args = [quote(arg, safe='') for arg in args]

    path_components = [
        encoded_source_type,
        encoded_document_identifier,
        encoded_section,
        encoded_sub_section
    ] + encoded_args
    return f"{settings.SOURCE_BASE_URI}{'/'.join(path_components)}"
