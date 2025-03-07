import pytest
from ocsf_json_schema import OcsfJsonSchema, OcsfJsonSchemaEmbedded

# Basic schema with one class, one object, and required types section
SAMPLE_SCHEMA = {
    "classes": {
        "authentication": {
            "attributes": {
                "user": {"type": "object_t", "object_type": "user"}
            }
        }
    },
    "objects": {
        "user": {
            "attributes": {
                "id": {"type": "integer_t"}
            }
        }
    },
    "types": {
        "object_t": {"type": "object_t"},
        "integer_t": {"type": "integer_t"}
    }
}

@pytest.fixture
def embedded_schema():
    schema = OcsfJsonSchema(SAMPLE_SCHEMA)
    return OcsfJsonSchemaEmbedded(schema)

def test_class_merges_with_objects(embedded_schema):
    result = embedded_schema.get_class_schema("authentication")
    # Check the class is there
    assert "properties" in result
    assert "user" in result["properties"]
    # Check the object is merged into $defs
    assert "$defs" in result
    assert "user" in result["$defs"]
    assert "id" in result["$defs"]["user"]["properties"]
    # Check the reference is rewritten
    assert result["properties"]["user"]["$ref"] == "#/$defs/user"
