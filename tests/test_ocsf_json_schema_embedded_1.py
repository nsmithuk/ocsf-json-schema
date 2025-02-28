import pytest
from ocsf_json_schema.schema import OcsfJsonSchema
from ocsf_json_schema.embedded import OcsfJsonSchemaEmbedded
from ocsf_json_schema.utility import entity_name_from_uri


@pytest.fixture
def sample_schema():
    """Fixture to provide a sample schema for testing."""
    return {
        "version": "1.0.0",
        "classes": {
            "event": {
                "caption": "Event",
                "attributes": {
                    "timestamp": {"type": "timestamp_t", "requirement": "required"},
                    "source": {"type": "string_t"},
                    "user": {"type": "object_t", "object_type": "user"},
                }
            }
        },
        "objects": {
            "user": {
                "caption": "User",
                "attributes": {
                    "username": {"type": "string_t", "requirement": "required"},
                    "email": {"type": "email_t"},
                }
            }
        }
    }


@pytest.fixture
def embedded_schema(sample_schema):
    """Fixture for OcsfJsonSchemaEmbedded with sample data."""
    return OcsfJsonSchemaEmbedded(OcsfJsonSchema(sample_schema))


def test_get_schema_from_uri(embedded_schema):
    """Test retrieving a class schema with embedded objects."""
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/event"

    result = embedded_schema.get_schema_from_uri(uri)

    assert result["$id"] == uri
    assert "user" in result["properties"]
    assert "$ref" in result["properties"]["user"]
    assert result["properties"]["user"]["$ref"] == "#/$defs/user"
    assert "$defs" in result
    assert "user" in result["$defs"]
    assert "properties" in result["$defs"]["user"]
    assert "username" in result["$defs"]["user"]["properties"]


def test_get_class_schema(embedded_schema):
    """Test retrieving an embedded class schema."""
    result = embedded_schema.get_class_schema("event")

    assert "user" in result["properties"]
    assert "$ref" in result["properties"]["user"]
    assert result["properties"]["user"]["$ref"] == "#/$defs/user"
    assert "$defs" in result
    assert "user" in result["$defs"]
    assert "username" in result["$defs"]["user"]["properties"]


def test_get_object_schema(embedded_schema):
    """Test retrieving an object schema with embedding."""
    result = embedded_schema.get_object_schema("user")

    assert "$defs" not in result  # Objects don't have embedded schemas
    assert "username" in result["properties"]


def test_rewrite_references():
    """Test that object references are correctly rewritten."""
    sample_properties = {
        "user": {"$ref": "https://schema.ocsf.io/schema/1.0.0/objects/user"},
        "items_list": {
            "type": "array",
            "items": {"$ref": "https://schema.ocsf.io/schema/1.0.0/objects/item"}
        }
    }
    embedded = OcsfJsonSchemaEmbedded({})  # Mock instance
    new_properties, objects_seen = embedded._rewrite_references(sample_properties)

    assert new_properties["user"]["$ref"] == "#/$defs/user"
    assert new_properties["items_list"]["items"]["$ref"] == "#/$defs/item"
    assert objects_seen == {"user", "item"}


@pytest.mark.parametrize("uri,expected", [
    ("https://schema.ocsf.io/schema/1.0.0/objects/user", "user"),
    ("https://schema.ocsf.io/schema/1.0.0/objects/device", "device"),
    ("https://schema.ocsf.io/schema/1.0.0/classes/event", "event"),
])
def test_object_name_from_uri(uri, expected):
    """Test extracting object names from URIs."""
    assert entity_name_from_uri(uri) == expected


@pytest.mark.parametrize("uri,expected_profiles", [
    ("https://schema.ocsf.io/schema/1.0.0/classes/event?profiles=admin", ["admin"]),
    ("https://schema.ocsf.io/schema/1.0.0/classes/event?profiles=read,write", ["read", "write"]),
    ("https://schema.ocsf.io/schema/1.0.0/classes/event", []),
])
def test_profiles_from_uri(uri, expected_profiles):
    """Test extracting profiles from URIs."""
    assert OcsfJsonSchemaEmbedded._profiles_from_uri(uri) == expected_profiles
