## Setup and Running

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Virtuoso connection:**
    Ensure your Virtuoso instance is running and accessible. Update the connection details (host, port, user, password, DSN) in `tcm_kg_virtuoso_module/config/settings.py`.

4.  **Run the FastAPI application:**
    From the repository root directory (the one containing `tcm_kg_virtuoso_module` and `src`):
    ```bash
    uvicorn tcm_kg_virtuoso_module.main:app --reload --app-dir .
    ```
    The `--app-dir .` tells uvicorn to look for modules in the current directory, which helps it find `tcm_kg_virtuoso_module`.

5.  Access the API at [http://127.0.0.1:8000](http://127.0.0.1:8000) and the OpenAPI docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

**Important Note on Current Database Implementation:**
The current version uses a **simulated** database connection (`VirtuosoConnectionManager` and `SparqlExecutor` in `tcm_kg_virtuoso_module/core/`). SPARQL queries are generated but **not actually executed** against a Virtuoso database. To enable real database operations, these components need to be updated to use a library like `sparqlwrapper` and connect to your Virtuoso instance. The `sparqlwrapper` dependency is commented out in `requirements.txt` and should be enabled when this work is undertaken.
