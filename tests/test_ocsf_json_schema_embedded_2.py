import pytest
from ocsf_json_schema.schema import OcsfJsonSchema
from ocsf_json_schema.embedded import OcsfJsonSchemaEmbedded
from ocsf_json_schema.utility import entity_name_from_uri

# Sample schema for testing
test_schema = {
    "version": "1.0.0",
    "classes": {
        "test_class": {
            "caption": "Test Class",
            "attributes": {
                "string_attr": {"type": "string_t", "requirement": "required"},
                "int_attr": {"type": "integer_t", "enum": {"1": "One", "2": "Two"}},
                "object_attr": {"type": "object_t", "object_type": "test_object"},
                "nested_object_attr": {"type": "object_t", "object_type": "nested_object"},
                "deprecated_attr": {"type": "string_t", "@deprecated": True},
                "array_int_attr": {"type": "integer_t", "is_array": True},
                "profile_attr": {"type": "string_t", "profile": "profile1"}
            },
            "constraints": {
                "at_least_one": ["string_attr", "int_attr"]
            }
        }
    },
    "objects": {
        "test_object": {
            "caption": "Test Object",
            "attributes": {
                "bool_attr": {"type": "boolean_t"},
                "array_attr": {"type": "string_t", "is_array": True},
                "profile_obj_attr": {"type": "string_t", "profile": "profile2"}
            }
        },
        "nested_object": {
            "caption": "Nested Object",
            "attributes": {
                "nested_attr": {"type": "object_t", "object_type": "empty_object"}
            }
        },
        "empty_object": {
            "caption": "Empty Object",
            "attributes": {}
        }
    }
}

# Fixtures
@pytest.fixture
def ocsf_schema():
    """Fixture providing an OcsfJsonSchema instance with the test schema."""
    return OcsfJsonSchema(test_schema)

@pytest.fixture
def embedded_schema(ocsf_schema):
    """Fixture providing an OcsfJsonSchemaEmbedded instance."""
    return OcsfJsonSchemaEmbedded(ocsf_schema)

# Initialization Tests
def test_init_with_ocsf_schema(ocsf_schema):
    """Test initialization with an OcsfJsonSchema instance."""
    embedded = OcsfJsonSchemaEmbedded(ocsf_schema)
    assert embedded.schema == ocsf_schema

def test_init_with_dict():
    """Test initialization with a dictionary."""
    embedded = OcsfJsonSchemaEmbedded(test_schema)
    assert isinstance(embedded.schema, OcsfJsonSchema)
    assert embedded.schema.version == "1.0.0"

# Tests for get_schema_from_uri
def test_get_schema_from_uri_with_embedding(embedded_schema):
    """Test that get_schema_from_uri embeds referenced objects correctly."""
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/test_class"
    schema = embedded_schema.get_schema_from_uri(uri)

    # Check that $defs is present and contains all referenced objects
    assert "$defs" in schema
    assert set(schema["$defs"].keys()) == {"test_object", "nested_object", "empty_object"}

    # Check that references are rewritten to local paths
    assert schema["properties"]["object_attr"]["$ref"] == "#/$defs/test_object"
    assert schema["properties"]["nested_object_attr"]["$ref"] == "#/$defs/nested_object"

    # Check nested references in embedded objects
    nested_object_schema = schema["$defs"]["nested_object"]
    assert nested_object_schema["properties"]["nested_attr"]["$ref"] == "#/$defs/empty_object"

    # Ensure embedded objects do not have $id
    for obj in schema["$defs"].values():
        assert "$id" not in obj

def test_get_schema_from_uri_with_profiles_embedding(embedded_schema):
    """Test that profiles in the URI affect embedded object schemas."""
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/test_class?profiles=profile2"
    schema = embedded_schema.get_schema_from_uri(uri)

    # Check that test_object includes profile_obj_attr due to profile2
    test_object_schema = schema["$defs"]["test_object"]
    assert "profile_obj_attr" in test_object_schema["properties"]

def test_get_schema_from_uri_without_profiles(embedded_schema):
    """Test that objects exclude profile-specific attributes without profiles."""
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/test_class"
    schema = embedded_schema.get_schema_from_uri(uri)

    # Check that test_object excludes profile_obj_attr
    test_object_schema = schema["$defs"]["test_object"]
    assert "profile_obj_attr" not in test_object_schema["properties"]

# Tests for get_class_schema
def test_get_class_schema_with_embedding(embedded_schema):
    """Test that get_class_schema embeds objects and respects profiles."""
    schema = embedded_schema.get_class_schema("test_class", profiles=["profile2"])

    # Check embedding
    assert "$defs" in schema
    assert set(schema["$defs"].keys()) == {"test_object", "nested_object", "empty_object"}
    assert schema["properties"]["object_attr"]["$ref"] == "#/$defs/test_object"

    # Check that profile2 includes profile_obj_attr in test_object
    test_object_schema = schema["$defs"]["test_object"]
    assert "profile_obj_attr" in test_object_schema["properties"]

# Tests for get_object_schema
def test_get_object_schema_with_embedding(embedded_schema):
    """Test that get_object_schema embeds nested objects."""
    schema = embedded_schema.get_object_schema("nested_object")

    # Check that empty_object is embedded
    assert "$defs" in schema
    assert "empty_object" in schema["$defs"]
    assert schema["properties"]["nested_attr"]["$ref"] == "#/$defs/empty_object"

def test_get_object_schema_no_embedding(embedded_schema):
    """Test that get_object_schema omits $defs when no references exist."""
    schema = embedded_schema.get_object_schema("test_object")

    # Since test_object has no object references, $defs should not be added
    assert "$defs" not in schema

# Tests for _rewrite_references
def test_rewrite_references(embedded_schema):
    """Test that _rewrite_references rewrites $ref to local paths and collects object names."""
    properties = {
        "attr1": {"$ref": "https://schema.ocsf.io/schema/1.0.0/objects/test_object"},
        "attr2": {"type": "array", "items": {"$ref": "https://schema.ocsf.io/schema/1.0.0/objects/nested_object"}}
    }
    rewritten_properties, objects_seen = embedded_schema._rewrite_references(properties)

    # Check rewritten references
    assert rewritten_properties["attr1"]["$ref"] == "#/$defs/test_object"
    assert rewritten_properties["attr2"]["items"]["$ref"] == "#/$defs/nested_object"

    # Check collected object names
    assert objects_seen == {"test_object", "nested_object"}

def test_rewrite_references_no_refs(embedded_schema):
    """Test that _rewrite_references handles properties without references."""
    properties = {
        "attr1": {"type": "string"},
        "attr2": {"type": "array", "items": {"type": "integer"}}
    }
    rewritten_properties, objects_seen = embedded_schema._rewrite_references(properties)

    # Properties should remain unchanged
    assert rewritten_properties == properties
    # No objects should be collected
    assert objects_seen == set()

# Tests for Utility Methods
def test_object_name_from_uri():
    """Test that _object_name_from_uri extracts the object name from a URI."""
    uri = "https://schema.ocsf.io/schema/1.0.0/objects/test_object"
    object_name = entity_name_from_uri(uri)
    assert object_name == "test_object"

def test_profiles_from_uri():
    """Test that _profiles_from_uri extracts profiles from a URI query string."""
    uri_with_profiles = "https://schema.ocsf.io/schema/1.0.0/classes/test_class?profiles=profile1,profile2"
    profiles = OcsfJsonSchemaEmbedded._profiles_from_uri(uri_with_profiles)
    assert profiles == ["profile1", "profile2"]

    uri_no_profiles = "https://schema.ocsf.io/schema/1.0.0/objects/test_object"
    profiles = OcsfJsonSchemaEmbedded._profiles_from_uri(uri_no_profiles)
    assert profiles == []
