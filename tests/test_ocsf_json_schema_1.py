import pytest
from ocsf_json_schema import OcsfJsonSchema


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


def test_get_schema_from_uri_valid_class(sample_schema):
    """Test retrieving a valid class schema from a URI."""
    ocsf = OcsfJsonSchema(sample_schema)
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/event"

    result = ocsf.get_schema_from_uri(uri)

    assert result["$id"] == uri
    assert result["title"] == "Event"
    assert "timestamp" in result["properties"]
    assert "source" in result["properties"]
    assert "required" in result
    assert "timestamp" in result["required"]


def test_get_schema_from_uri_valid_object(sample_schema):
    """Test retrieving a valid object schema from a URI."""
    ocsf = OcsfJsonSchema(sample_schema)
    uri = "https://schema.ocsf.io/schema/1.0.0/objects/user"

    result = ocsf.get_schema_from_uri(uri)

    assert result["$id"] == uri
    assert result["title"] == "User"
    assert "username" in result["properties"]
    assert "email" in result["properties"]
    assert "required" in result
    assert "username" in result["required"]


@pytest.mark.parametrize("invalid_uri", [
    "https://schema.ocsf.io/schema/1.0.0/wrongtype/event",  # Invalid type
    "https://schema.ocsf.io/schema/2.0.0/classes/event",  # Wrong version
    "https://schema.ocsf.io/schema/1.0.0/classes/",  # Missing class name
    "https://schema.ocsf.io/schema/1.0.0/",  # Incomplete path
])
def test_get_schema_from_uri_invalid_uris(sample_schema, invalid_uri):
    """Test that invalid URIs raise a ValueError."""
    ocsf = OcsfJsonSchema(sample_schema)

    with pytest.raises(ValueError, match="Invalid schema URI"):
        ocsf.get_schema_from_uri(invalid_uri)


@pytest.mark.parametrize("ocsf_type,json_type,extra_fields", [
    ("boolean_t", "boolean", {}),
    ("float_t", "number", {}),
    ("integer_t", "integer", {}),
    ("long_t", "integer", {}),
    ("string_t", "string", {}),
    ("json_t", None, {}),  # json_t should not be mapped to a type
    ("datetime_t", "string", {"format": "date-time"}),
    ("ip_t", "string", {"format": "ipv4"}),
    ("mac_t", "string", {"pattern": "^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"}),
    ("port_t", "integer", {"minimum": 0, "maximum": 65535}),
    ("timestamp_t", "integer", {"minimum": 0}),
    ("url_t", "string", {"format": "uri"}),
    ("email_t", "string", {"format": "email"}),
    ("fqdn_t", "string", {"format": "hostname"}),
])
def test_type_mapping(ocsf_type, json_type, extra_fields):
    """Test that OCSF types correctly map to JSON schema types and formats."""
    schema_data = {
        "version": "1.0.0",
        "classes": {
            "sample_class": {
                "caption": "Sample",
                "attributes": {
                    "test_attr": {"type": ocsf_type}
                }
            }
        }
    }

    ocsf = OcsfJsonSchema(schema_data)
    result = ocsf.get_class_schema("sample_class")

    assert "test_attr" in result["properties"]
    attr_schema = result["properties"]["test_attr"]

    if json_type is None:
        assert "type" not in attr_schema
    else:
        assert attr_schema["type"] == json_type

    for key, value in extra_fields.items():
        assert attr_schema.get(key) == value


def test_get_schema_from_uri_profiles(sample_schema):
    """Test retrieving a class schema with profiles."""
    ocsf = OcsfJsonSchema(sample_schema)
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/event?profiles=custom"

    result = ocsf.get_schema_from_uri(uri)

    assert result["$id"] == uri
    assert result["title"] == "Event"
    assert "timestamp" in result["properties"]
    assert "source" in result["properties"]


def test_generate_schema_with_constraints():
    """Test the `_generate_schema` method with constraints."""
    schema_data = {
        "version": "1.0.0",
        "classes": {
            "sample_class": {
                "caption": "Sample",
                "attributes": {
                    "field1": {"type": "string_t"},
                    "field2": {"type": "integer_t"},
                },
                "constraints": {
                    "at_least_one": ["field1", "field2"]
                }
            }
        }
    }
    ocsf = OcsfJsonSchema(schema_data)
    result = ocsf.get_class_schema("sample_class")

    assert "anyOf" in result
    assert {"required": ["field1"]} in result["anyOf"]
    assert {"required": ["field2"]} in result["anyOf"]


def test_generate_schema_with_invalid_constraint():
    """Test that an unsupported constraint raises a NotImplementedError."""
    schema_data = {
        "version": "1.0.0",
        "classes": {
            "sample_class": {
                "caption": "Sample",
                "attributes": {
                    "field1": {"type": "string_t"}
                },
                "constraints": {
                    "unknown_constraint": ["field1"]
                }
            }
        }
    }
    ocsf = OcsfJsonSchema(schema_data)

    with pytest.raises(NotImplementedError, match="Not constraints implemented yet: unknown_constraint"):
        ocsf.get_class_schema("sample_class")
