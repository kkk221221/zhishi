# tcm_kg_virtuoso_module/tests/core/test_real_entity_creation.py

import uuid
import requests
import json
import time
import pytest # Import pytest

from tcm_kg_virtuoso_module.config import settings as tcm_settings
from tcm_kg_virtuoso_module.core.connection_manager import VirtuosoConnectionManager
from tcm_kg_virtuoso_module.core.sparql_executor import SparqlExecutor
from tcm_kg_virtuoso_module.core.graph_operations import add_entity
from tcm_kg_virtuoso_module.core.uri_minter import mint_source_uri as actual_mint_source_uri
from tcm_kg_virtuoso_module.core.data_formatter import format_uri, format_literal, _expand_curie

# --- Configuration ---
BASE_API_URL = "http://localhost:8000/api/v1/tcm/graph"  # Ensure your FastAPI app is running here
CONFIG = tcm_settings.get_settings()
DEFAULT_PREFIXES = tcm_settings.DEFAULT_PREFIXES

# --- Helper Functions (identical to your previous script) ---

def get_virtuoso_executor_and_manager():
    """Creates, connects, and returns a Virtuoso executor and its manager."""
    manager = VirtuosoConnectionManager(
        host=CONFIG.virtuoso_host,
        port=CONFIG.virtuoso_port,
        user=CONFIG.virtuoso_user,
        password=CONFIG.virtuoso_password,
        default_graph_uri=CONFIG.virtuoso_graph_uri
    )
    manager.connect()
    executor = SparqlExecutor(manager)
    return executor, manager

def cleanup_test_data(executor: SparqlExecutor, source_graph_uri: str):
    """
    Cleans up test data: clears the specified named graph and deletes its metadata.
    """
    if not source_graph_uri:
        print("WARNING: No source_graph_uri provided for cleanup. Skipping.")
        return

    current_executor = executor
    temp_manager_created = False # Flag to track if we created a temporary manager

    # Check if the executor or its connection is valid. If not, create a temporary one for cleanup.
    if not current_executor or not current_executor.connection_manager or \
       not current_executor.connection_manager.connection or \
       current_executor.connection_manager.cursor is None: # Also check cursor
        print("WARNING: Executor or connection is invalid for cleanup. Creating a temporary one.")
        current_executor, temp_manager_for_cleanup = get_virtuoso_executor_and_manager()
        temp_manager_created = True
    else:
        temp_manager_for_cleanup = None # Not used if current_executor is fine


    try:
        current_executor.begin_transaction()
        print(f"INFO: Attempting to clear graph: <{source_graph_uri}>")
        clear_graph_query = f"SPARQL CLEAR GRAPH <{source_graph_uri}>"
        current_executor.execute_update(clear_graph_query)
        print(f"INFO: Graph <{source_graph_uri}> cleared.")

        print(f"INFO: Attempting to delete metadata for source graph: <{source_graph_uri}>")
        delete_metadata_query = f"""
                    SPARQL DELETE FROM <{CONFIG.virtuoso_graph_uri}>
                    WHERE {{
                        <{source_graph_uri}> ?p ?o .
                    }}
                """
        current_executor.execute_update(delete_metadata_query)
        print(f"INFO: Metadata for source graph <{source_graph_uri}> deleted from default graph.")

        current_executor.commit_transaction()
        print(f"INFO: Cleanup for <{source_graph_uri}> committed.")

    except Exception as e:
        print(f"ERROR: Failed during cleanup for <{source_graph_uri}>: {e}")
        if current_executor.connection_manager and current_executor.connection_manager.transaction_active:
            try:
                current_executor.rollback_transaction()
                print(f"INFO: Cleanup transaction for <{source_graph_uri}> rolled back due to error.")
            except Exception as rb_e:
                print(f"ERROR: Failed to rollback cleanup transaction for <{source_graph_uri}>: {rb_e}")
    finally:
        if temp_manager_created and temp_manager_for_cleanup:
            temp_manager_for_cleanup.disconnect()
            print("INFO: Temporary cleanup manager disconnected.")


def check_entity_exists(executor: SparqlExecutor, entity_uri: str, label: str, attributes_to_check: list, source_graph_uri: str):
    """
    Checks if an entity, its label, and specified attributes exist in the given source graph.
    attributes_to_check is a list of dicts:
    {"property_curie": str, "value": Any, "is_uri": bool, "datatype": Optional[str]}
    """
    print(f"INFO: Checking existence of entity <{entity_uri}> in graph <{source_graph_uri}>")

    entity_type_from_uri_parts = entity_uri.split('/')
    entity_type_local_name = "Unknown"
    if len(entity_type_from_uri_parts) > 2: # Expecting .../resource/EntityType/EntityLabel_UUID
        entity_type_local_name = entity_type_from_uri_parts[-2]


    type_uri = _expand_curie(f"tcm-onto:{entity_type_local_name}", DEFAULT_PREFIXES)
    type_query = f"""
        SPARQL ASK WHERE {{
            GRAPH <{source_graph_uri}> {{ <{entity_uri}> <{_expand_curie("rdf:type", DEFAULT_PREFIXES)}> <{type_uri}> . }}
        }}
    """
    print(f"DEBUG: Type query: {type_query}")
    result = executor.execute_select(type_query)
    assert result and result[0].get('ASK') is True, f"Type <{type_uri}> for entity <{entity_uri}> not found."
    print(f"INFO: Type for entity <{entity_uri}> confirmed as <{type_uri}>.")

    formatted_label_obj = format_literal(label, datatype="string")
    label_query = f"""
        SPARQL ASK WHERE {{
            GRAPH <{source_graph_uri}> {{
                <{entity_uri}> <{_expand_curie("rdfs:label", DEFAULT_PREFIXES)}> {formatted_label_obj} .
            }}
        }}
    """
    print(f"DEBUG: Label query: {label_query}")
    result = executor.execute_select(label_query)
    assert result and result[0].get('ASK') is True, f"Label '{label}' for entity <{entity_uri}> not found. Query: {label_query}"
    print(f"INFO: Label '{label}' for entity <{entity_uri}> confirmed.")

    for attr_to_check in attributes_to_check:
        prop_uri_expanded = _expand_curie(attr_to_check["property_curie"], DEFAULT_PREFIXES)
        if attr_to_check["is_uri"]:
            obj_formatted = format_uri(str(attr_to_check["value"]))
        else:
            obj_formatted = format_literal(attr_to_check["value"], datatype=attr_to_check.get("datatype", "string"))

        attr_query = f"""
            SPARQL ASK WHERE {{
                GRAPH <{source_graph_uri}> {{
                    <{entity_uri}> <{prop_uri_expanded}> {obj_formatted} .
                }}
            }}
        """
        print(f"DEBUG: Attribute query: {attr_query}")
        result = executor.execute_select(attr_query)
        assert result and result[0].get('ASK') is True, \
            f"Attribute {attr_to_check['property_curie']} with value '{attr_to_check['value']}' (formatted: {obj_formatted}) for entity <{entity_uri}> not found. Query: {attr_query}"
        print(f"INFO: Attribute {attr_to_check['property_curie']} for entity <{entity_uri}> with value '{attr_to_check['value']}' confirmed.")
    print(f"INFO: Entity <{entity_uri}> and its attributes successfully verified in graph <{source_graph_uri}>.")


# --- Test Scenarios Data (identical to your previous script) ---
test_scenarios_data = [
    {
        "name_suffix": "SimpleASCII",
        "original_text": "Simple ASCII content.",
        "attributes_payload_for_api": [{"property": "tcm-onto:testPropAPI", "value": "ASCII_Value"}],
        "attributes_for_check": [
            {"property_curie": "tcm-onto:testPropAPI", "value": "ASCII_Value", "is_uri": False, "datatype": "string"}
        ],
        "raw_attributes_for_core_add_entity": [
            {"property": "tcm-onto:testPropAPI", "value": "ASCII_Value"}
        ]
    },
    {
        "name_suffix": "ChineseText",
        "original_text": "人参，味甘，微寒，主补五脏。",
        "attributes_payload_for_api": [
            {"property": "tcm-onto:hasTaste", "value": "甘"},
            {"property": "tcm-onto:hasNature", "value": "微寒"}
        ],
        "attributes_for_check": [
            {"property_curie": "tcm-onto:hasTaste", "value": "甘", "is_uri": False, "datatype": "string"},
            {"property_curie": "tcm-onto:hasNature", "value": "微寒", "is_uri": False, "datatype": "string"}
        ],
        "raw_attributes_for_core_add_entity": [
            {"property": "tcm-onto:hasTaste", "value": "甘"},
            {"property": "tcm-onto:hasNature", "value": "微寒"}
        ]
    },
    {
        "name_suffix": "QuotesNewlinesTabs",
        "original_text": 'Text with "double quotes" and a \nnewline and a tab\t character.',
        "attributes_payload_for_api": [
            {"property": "tcm-onto:description", "value": 'A "quoted" description.'},
            {"property": "tcm-onto:notes", "value": "First line.\nSecond line with tab\there."}
        ],
        "attributes_for_check": [
            {"property_curie": "tcm-onto:description", "value": 'A "quoted" description.', "is_uri": False, "datatype": "string"},
            {"property_curie": "tcm-onto:notes", "value": "First line.\nSecond line with tab\there.", "is_uri": False, "datatype": "string"}
        ],
        "raw_attributes_for_core_add_entity": [
            {"property": "tcm-onto:description", "value": 'A "quoted" description.'},
            {"property": "tcm-onto:notes", "value": "First line.\nSecond line with tab\there."}
        ]
    },
    {
        "name_suffix": "MultiValAndURI",
        "original_text": "Testing multi-valued attributes (e.g., synonyms) and URI object values.",
        "attributes_payload_for_api": [
            {"property": "tcm-onto:altLabel", "value": ["Synonym1", "别名2"]},
            {"property": "rdfs:seeAlso", "value": "http://example.org/resource/RelatedHerbMulti"}
        ],
        "attributes_for_check": [
            {"property_curie": "tcm-onto:altLabel", "value": "Synonym1", "is_uri": False, "datatype": "string"},
            {"property_curie": "tcm-onto:altLabel", "value": "别名2", "is_uri": False, "datatype": "string"},
            {"property_curie": "rdfs:seeAlso", "value": "http://example.org/resource/RelatedHerbMulti", "is_uri": True}
        ],
        "raw_attributes_for_core_add_entity": [
            {"property": "tcm-onto:altLabel", "value": ["Synonym1", "别名2"]},
            {"property": "rdfs:seeAlso", "value": "http://example.org/resource/RelatedHerbMulti"}
        ]
    }
]


# --- Main Test Logic Function (called by pytest) ---
def execute_full_test_scenario(
        test_name_suffix: str,
        original_text_content: str,
        attributes_payload_for_api: list,
        attributes_for_check: list,
        raw_attributes_for_core_add_entity: list
    ):
    """
    This function contains the actual test logic, separated for clarity.
    It's called by the pytest parametrized test function.
    """
    base_unique_id = str(uuid.uuid4())[:8]
    entity_type = "TestHerb"

    # === API Test Part ===
    api_test_name = f"API_{test_name_suffix}_{base_unique_id}"
    print(f"\n--- Running Test Scenario: {api_test_name} ---")
    api_entity_label = f"ApiLabel_{test_name_suffix}_{base_unique_id}"
    api_doc_id = f"ApiDoc_{base_unique_id}"
    api_source_citation = f"API Test Citation for {api_entity_label}"
    api_payload = {
        "type": entity_type, "label": api_entity_label, "attributes": attributes_payload_for_api,
        "source": {"citation": api_source_citation, "originalText": original_text_content, "documentIdentifier": api_doc_id}
    }
    entity_uri_api = None
    source_graph_uri_api = None
    try:
        print(f"INFO ({api_test_name}): Sending POST request to {BASE_API_URL}/entities")
        print(f"INFO ({api_test_name}): Payload: {json.dumps(api_payload, ensure_ascii=False, indent=2)}")
        response = requests.post(f"{BASE_API_URL}/entities", json=api_payload)
        print(f"INFO ({api_test_name}): Response status code: {response.status_code}")
        if response.status_code >= 400:
            try: print(f"ERROR_DETAIL ({api_test_name}): {response.json()}")
            except json.JSONDecodeError: print(f"ERROR_DETAIL ({api_test_name}): {response.text}")
        response.raise_for_status()
        response_data = response.json()
        entity_uri_api = response_data.get("entity_uri")
        assert entity_uri_api, f"API ({api_test_name}) did not return an entity_uri."
        print(f"INFO ({api_test_name}): API entity creation successful. URI: {entity_uri_api}")
        source_graph_uri_api = actual_mint_source_uri("APIDataCreation", api_doc_id, entity_type, api_entity_label)
        print(f"INFO ({api_test_name}): Predicted source_graph_uri for API test: {source_graph_uri_api}")
        executor_api, manager_api = get_virtuoso_executor_and_manager()
        try:
            time.sleep(1)
            check_entity_exists(executor_api, entity_uri_api, api_entity_label, attributes_for_check, source_graph_uri_api)
            print(f"SUCCESS: API Test for {api_test_name} passed.")
        finally:
            if source_graph_uri_api: cleanup_test_data(executor_api, source_graph_uri_api)
            if manager_api: manager_api.disconnect()
    except Exception as e_api:
        print(f"FAILURE: API Test for {api_test_name} failed: {e_api}")
        if entity_uri_api and source_graph_uri_api:
            print(f"INFO ({api_test_name}): Attempting cleanup despite API failure...")
            executor_f_api, manager_f_api = get_virtuoso_executor_and_manager()
            try: cleanup_test_data(executor_f_api, source_graph_uri_api)
            finally:
                if manager_f_api: manager_f_api.disconnect()
        raise

    # === Direct Core Logic Test Part ===
    core_test_name = f"Core_{test_name_suffix}_{base_unique_id}"
    print(f"\n--- Running Test Scenario: {core_test_name} ---")
    core_entity_label = f"CoreLabel_{test_name_suffix}_{base_unique_id}"
    core_doc_id = f"CoreDoc_{base_unique_id}"
    core_source_citation = f"Core Test Citation for {core_entity_label}"
    core_entity_data_payload = {
        "entity_type_name": entity_type, "entity_label": core_entity_label,
        "attributes_list": raw_attributes_for_core_add_entity,
        "source_details": {
            "citation": core_source_citation, "original_text": original_text_content,
            "document_identifier": core_doc_id, "source_type": "DirectCoreRun",
            "source_section": "CoreTestSection", "source_subsection": "CoreTestSubSection"
        }, "entity_id_args": None
    }
    entity_uri_core = None
    source_graph_uri_core = None
    executor_core, manager_core = get_virtuoso_executor_and_manager()
    try:
        sd = core_entity_data_payload["source_details"]
        source_graph_uri_core = actual_mint_source_uri(
            sd["source_type"], sd["document_identifier"], sd["source_section"], sd["source_subsection"]
        )
        print(f"INFO ({core_test_name}): Predicted source_graph_uri for core test: {source_graph_uri_core}")
        print(f"INFO ({core_test_name}): Calling core add_entity for {core_entity_label}")
        print(f"INFO ({core_test_name}): Core Payload: {json.dumps(core_entity_data_payload, ensure_ascii=False, indent=2)}")
        entity_uri_core = add_entity(entity_data=core_entity_data_payload, conn_manager=manager_core)
        assert entity_uri_core, f"Core add_entity ({core_test_name}) did not return an entity_uri."
        print(f"INFO ({core_test_name}): Core add_entity successful. URI: {entity_uri_core}")
        time.sleep(1)
        check_entity_exists(executor_core, entity_uri_core, core_entity_label, attributes_for_check, source_graph_uri_core)
        print(f"SUCCESS: Direct Core Logic Test for {core_test_name} passed.")
    except Exception as e_core:
        print(f"FAILURE: Direct Core Logic Test for {core_test_name} failed: {e_core}")
        raise
    finally:
        if source_graph_uri_core: cleanup_test_data(executor_core, source_graph_uri_core)
        if manager_core: manager_core.disconnect()

# --- Pytest Discoverable Test Function ---
@pytest.mark.parametrize(
    "scenario_data",
    test_scenarios_data,
    ids=[s['name_suffix'] for s in test_scenarios_data]
)
def test_entity_creation_scenarios(scenario_data):
    """
    Pytest discoverable test function.
    It calls the main scenario execution logic with parametrized data.
    """
    print(f"\n<<<<<<<<<< PYTEST: Starting Scenario '{scenario_data['name_suffix']}' >>>>>>>>>>")
    # Before running, ensure the prerequisites for the test environment are met
    # (e.g., Virtuoso and FastAPI app are running)
    # This can be mentioned in a README or a global setup/teardown fixture if using advanced pytest.

    execute_full_test_scenario(
        test_name_suffix=scenario_data["name_suffix"],
        original_text_content=scenario_data["original_text"],
        attributes_payload_for_api=scenario_data["attributes_payload_for_api"],
        attributes_for_check=scenario_data["attributes_for_check"],
        raw_attributes_for_core_add_entity=scenario_data["raw_attributes_for_core_add_entity"]
    )
    print(f"<<<<<<<<<< PYTEST: Finished Scenario '{scenario_data['name_suffix']}' >>>>>>>>>>")

# To run this with pytest:
# 1. Ensure Virtuoso and your FastAPI application (tcm_kg_virtuoso_module.main:app) are running.
# 2. Navigate to the directory containing `tcm_kg_virtuoso_module` (i.e., `D:\AI\zstp\zhishi\zhishi` in your case).
# 3. Execute: pytest -vv tcm_kg_virtuoso_module/tests/core/test_real_entity_creation.py
#
# Note: If the tcm_kg_virtuoso_module is not installed in a way that its modules are directly
# importable by Python when running pytest from the root directory, you might need to adjust
# PYTHONPATH or install the module in editable mode (pip install -e .).
# Based on your `(venv) PS D:\AI\zstp\zhishi\zhishi>` prompt, it seems you are running from the project root,
# so imports should work if `tcm_kg_virtuoso_module` is a package directly under this root.