from fastapi import FastAPI
from tcm_kg_virtuoso_module.api import endpoints as api_endpoints

app = FastAPI(
    title="TCM Knowledge Graph API",
    version="0.1.0",
    description="API for interacting with the Traditional Chinese Medicine Knowledge Graph"
)

app.include_router(
    api_endpoints.router, 
    prefix="/api/v1/tcm/graph", 
    tags=["Knowledge Graph Operations"]
)

@app.get("/")
async def root():
    return {"message": "Welcome to the TCM Knowledge Graph API"}
