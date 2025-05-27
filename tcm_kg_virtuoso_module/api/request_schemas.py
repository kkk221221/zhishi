# api/request_schemas.py
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any

class Attribute(BaseModel):
    property: str
    value: Any # Can be str, List[str], or HttpUrl for links

class Source(BaseModel):
    citation: str
    originalText: str
    documentIdentifier: str

class EntityCreate(BaseModel):
    type: str
    label: str
    attributes: List[Attribute]
    source: Source

class RelationshipCreate(BaseModel):
    subjectUri: HttpUrl
    predicate: str  # This will be a CURIE, e.g., "tcm-onto:hasSymptom"
    objectUri: HttpUrl
    source: Source # Reusing the existing Source model
