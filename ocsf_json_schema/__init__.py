"""
ocsf_json_schema
----------------
A Python library for handling OCSF JSON schemas.

Exports:
- OcsfJsonSchema: The main class for schema processing.
- load_ocsf_schema_json: Function to load schema from a JSON file.
- load_ocsf_schema_pickle: Function to load schema from a Pickle file.
- get_ocsf_schema: Function to retrieve schema based on version.
"""

from .schema import OcsfJsonSchema
from .embedded import OcsfJsonSchemaEmbedded
from .loader import load_ocsf_schema_json, load_ocsf_schema_pickle, get_ocsf_schema, get_packaged_versions
from .pickle_it import pickle_it

__all__ = [
    "OcsfJsonSchema",
    "OcsfJsonSchemaEmbedded",
    "load_ocsf_schema_json",
    "load_ocsf_schema_pickle",
    "get_ocsf_schema",
    "pickle_it",
    "get_packaged_versions"
]
