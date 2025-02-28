import pytest
from ocsf_json_schema import OcsfJsonSchema

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
                "array_attr": {"type": "string_t", "is_array": True}
            }
        },
        "empty_object": {
            "caption": "Empty Object",
            "attributes": {}
        }
    }
}

# Fixture to provide an instance of OcsfJsonSchema
@pytest.fixture
def ocsf_schema():
    """Fixture providing an OcsfJsonSchema instance initialized with test_schema."""
    return OcsfJsonSchema(test_schema)

# Test initialization
def test_init(ocsf_schema):
    """Test that the schema version is correctly set during initialization."""
    assert ocsf_schema.version == "1.0.0"

# Tests for get_schema_from_uri method
def test_get_schema_from_uri_class(ocsf_schema):
    """Test retrieving a class schema from a valid URI."""
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/test_class"
    schema = ocsf_schema.get_schema_from_uri(uri)
    assert schema["$id"] == uri
    assert schema["title"] == "Test Class"
    assert "properties" in schema
    assert "string_attr" in schema["properties"]
    assert "required" in schema and "string_attr" in schema["required"]

def test_get_schema_from_uri_object(ocsf_schema):
    """Test retrieving an object schema from a valid URI."""
    uri = "https://schema.ocsf.io/schema/1.0.0/objects/test_object"
    schema = ocsf_schema.get_schema_from_uri(uri)
    assert schema["$id"] == uri
    assert schema["title"] == "Test Object"
    assert "properties" in schema
    assert "bool_attr" in schema["properties"]

def test_get_schema_from_uri_with_profiles(ocsf_schema):
    """Test retrieving a schema with profiles included in the URI."""
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/test_class?profiles=profile1,profile2"
    schema = ocsf_schema.get_schema_from_uri(uri)
    assert schema["$id"] == uri
    assert "profile_attr" in schema["properties"]  # profile1 is included

def test_get_schema_from_uri_invalid_format(ocsf_schema):
    """Test that an invalid URI format raises a ValueError."""
    with pytest.raises(ValueError, match="Invalid schema URI"):
        ocsf_schema.get_schema_from_uri("https://schema.ocsf.io/schema/1.0.0/invalid/test")

def test_get_schema_from_uri_wrong_version(ocsf_schema):
    """Test that a URI with an incorrect version raises a ValueError."""
    with pytest.raises(ValueError, match="Invalid schema URI"):
        ocsf_schema.get_schema_from_uri("https://schema.ocsf.io/schema/2.0.0/classes/test_class")

def test_get_schema_from_uri_nonexistent_class(ocsf_schema):
    """Test that a URI for a non-existent class raises a ValueError."""
    with pytest.raises(ValueError, match="Class 'nonexistent' is not defined"):
        ocsf_schema.get_schema_from_uri("https://schema.ocsf.io/schema/1.0.0/classes/nonexistent")

# Tests for get_class_schema and get_object_schema methods
def test_get_class_schema(ocsf_schema):
    """Test retrieving a class schema directly."""
    schema = ocsf_schema.get_class_schema("test_class")
    assert schema["title"] == "Test Class"
    assert "properties" in schema

def test_get_object_schema(ocsf_schema):
    """Test retrieving an object schema directly."""
    schema = ocsf_schema.get_object_schema("test_object")
    assert schema["title"] == "Test Object"
    assert "properties" in schema

def test_get_class_schema_nonexistent(ocsf_schema):
    """Test that a non-existent class raises a ValueError."""
    with pytest.raises(ValueError, match="Class 'nonexistent' is not defined"):
        ocsf_schema.get_class_schema("nonexistent")

def test_get_object_schema_nonexistent(ocsf_schema):
    """Test that a non-existent object raises a ValueError."""
    with pytest.raises(ValueError, match="Object 'nonexistent' is not defined"):
        ocsf_schema.get_object_schema("nonexistent")

# Test for constraints handling
def test_constraints_at_least_one(ocsf_schema):
    """Test that the 'at_least_one' constraint is correctly implemented."""
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/test_class"
    schema = ocsf_schema.get_schema_from_uri(uri)
    assert "anyOf" in schema
    assert schema["anyOf"] == [{"required": ["string_attr"]}, {"required": ["int_attr"]}]

# Tests for attribute types and properties
def test_attribute_types(ocsf_schema):
    """Test that attribute types and properties are correctly mapped."""
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/test_class"
    schema = ocsf_schema.get_schema_from_uri(uri)
    properties = schema["properties"]
    assert properties["string_attr"]["type"] == "string"
    assert properties["int_attr"]["type"] == "integer"
    assert "enum" in properties["int_attr"] and properties["int_attr"]["enum"] == [1, 2]
    assert "$ref" in properties["object_attr"]
    assert properties["deprecated_attr"]["deprecated"] == True
    assert properties["array_int_attr"]["type"] == "array"
    assert properties["array_int_attr"]["items"]["type"] == "integer"

def test_object_attributes(ocsf_schema):
    """Test that object attribute types and properties are correctly mapped."""
    uri = "https://schema.ocsf.io/schema/1.0.0/objects/test_object"
    schema = ocsf_schema.get_schema_from_uri(uri)
    properties = schema["properties"]
    assert properties["bool_attr"]["type"] == "boolean"
    assert properties["array_attr"]["type"] == "array"
    assert properties["array_attr"]["items"]["type"] == "string"

# Test for profile filtering
def test_profile_filtering(ocsf_schema):
    """Test that profile filtering includes or excludes attributes correctly."""
    uri_no_profile = "https://schema.ocsf.io/schema/1.0.0/classes/test_class"
    schema_no_profile = ocsf_schema.get_schema_from_uri(uri_no_profile)
    assert "profile_attr" not in schema_no_profile["properties"]

    uri_with_profile = "https://schema.ocsf.io/schema/1.0.0/classes/test_class?profiles=profile1"
    schema_with_profile = ocsf_schema.get_schema_from_uri(uri_with_profile)
    assert "profile_attr" in schema_with_profile["properties"]

# Test for additional properties
def test_additional_properties(ocsf_schema):
    """Test that additionalProperties is set correctly for objects."""
    uri_empty = "https://schema.ocsf.io/schema/1.0.0/objects/empty_object"
    schema_empty = ocsf_schema.get_schema_from_uri(uri_empty)
    assert schema_empty["additionalProperties"] == True

    uri_class = "https://schema.ocsf.io/schema/1.0.0/classes/test_class"
    schema_class = ocsf_schema.get_schema_from_uri(uri_class)
    assert schema_class["additionalProperties"] == False
