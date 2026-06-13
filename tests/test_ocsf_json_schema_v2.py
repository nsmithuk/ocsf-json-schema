import pytest
from ocsf_json_schema import OcsfJsonSchema

SAMPLE_SCHEMA_V2 = {
    "version": "1.8.0",
    "compile_version": "1.8.0",
    "classes": {
        "authentication": {
            "uid": 1001,
            "name": "Authentication",
            "caption": "Authentication Event",
            "attributes": {
                "user": {"caption": "User", "type": "string_t", "requirement": "required", "profiles": []},
                "success": {"caption": "Success", "type": "boolean_t", "profiles": []},
                "cloud_account": {"caption": "Cloud Account", "type": "string_t", "profiles": ["cloud"]},
            }
        }
    },
    "objects": {
        "user": {
            "caption": "User Object",
            "attributes": {"id": {"caption": "ID", "type": "integer_t", "profiles": []}}
        }
    },
    "dictionary": {
        "types": {
            "attributes": {
                "string_t": {"type": "string_t"},
                "boolean_t": {"type": "boolean_t"},
                "integer_t": {"type": "integer_t"},
                "float_t": {"type": "float_t"},
                "long_t": {"type": "long_t"},
                "json_t": {"type": "json_t"},
                "ip_t": {"type": "string_t", "regex": ".*"},
                "custom_scalar_t": {"type": "string_t"},
            }
        }
    }
}


@pytest.fixture
def ocsf_schema_v2():
    return OcsfJsonSchema(SAMPLE_SCHEMA_V2)


def test_v2_detected():
    schema = OcsfJsonSchema(SAMPLE_SCHEMA_V2)
    assert schema._is_v2 is True


def test_v1_not_detected():
    v1_schema = {
        "version": "1.7.0",
        "classes": {},
        "objects": {},
        "types": {}
    }
    schema = OcsfJsonSchema(v1_schema)
    assert schema._is_v2 is False


def test_types_from_dictionary(ocsf_schema_v2):
    types = ocsf_schema_v2._types
    assert "string_t" in types
    assert "integer_t" in types


def test_lookup_class_name_from_uid(ocsf_schema_v2):
    assert ocsf_schema_v2.lookup_class_name_from_uid(1001) == "Authentication"
    with pytest.raises(ValueError, match="No class found for uid 999"):
        ocsf_schema_v2.lookup_class_name_from_uid(999)


def test_get_class_schema(ocsf_schema_v2):
    result = ocsf_schema_v2.get_class_schema("authentication")
    assert result["$id"] == "https://schema.ocsf.io/schema/1.8.0/classes/authentication"
    assert result["properties"]["user"]["type"] == "string"
    assert "user" in result["required"]
    # cloud_account has profiles=['cloud'], not selected — should be excluded
    assert "cloud_account" not in result["properties"]


def test_get_class_schema_with_profile(ocsf_schema_v2):
    result = ocsf_schema_v2.get_class_schema("authentication", profiles=["cloud"])
    assert "cloud_account" in result["properties"]
    assert "user" in result["properties"]


def test_get_object_schema(ocsf_schema_v2):
    result = ocsf_schema_v2.get_object_schema("user", ["web"])
    assert result["$id"] == "https://schema.ocsf.io/schema/1.8.0/objects/user?profiles=web"
    assert result["properties"]["id"]["type"] == "integer"


def test_get_schema_from_uri(ocsf_schema_v2):
    uri = "https://schema.ocsf.io/schema/1.8.0/classes/authentication"
    result = ocsf_schema_v2.get_schema_from_uri(uri)
    assert result["$id"] == uri
    assert result["title"] == "Authentication Event"

    uri = "https://schema.ocsf.io/schema/1.8.0/objects/user?profiles=web"
    result = ocsf_schema_v2.get_schema_from_uri(uri)
    assert result["$id"] == uri

    with pytest.raises(ValueError, match="Invalid schema URI.*Expected schema version"):
        ocsf_schema_v2.get_schema_from_uri("https://schema.ocsf.io/schema/1.7.0/classes/authentication")


def test_profile_filtering_empty_list_always_included(ocsf_schema_v2):
    # Attributes with profiles=[] must always be included, regardless of selected profiles
    result = ocsf_schema_v2.get_class_schema("authentication", profiles=[])
    assert "user" in result["properties"]
    assert "success" in result["properties"]
    assert "cloud_account" not in result["properties"]


def test_profile_filtering_excludes_when_no_match(ocsf_schema_v2):
    result = ocsf_schema_v2.get_class_schema("authentication", profiles=["datetime"])
    assert "cloud_account" not in result["properties"]


def test_generate_attribute_types(ocsf_schema_v2):
    ref_format = "ref_format/%s"
    base_type_tests = [
        ("boolean_t", "boolean"),
        ("integer_t", "integer"),
        ("float_t", "number"),
        ("long_t", "integer"),
        ("string_t", "string"),
        ("json_t", ["object", "string", "integer", "number", "boolean", "array", "null"]),
    ]
    for type_name, expected_type in base_type_tests:
        attr = {"caption": f"Test {type_name}", "type": type_name}
        result = ocsf_schema_v2._generate_attribute(attr, ref_format)
        assert result["type"] == expected_type, f"Failed for {type_name}"

    attr = {"caption": "Test Object", "type": "object_t", "object_type": "user"}
    result = ocsf_schema_v2._generate_attribute(attr, ref_format)
    assert result["$ref"] == "ref_format/user"

    attr = {"caption": "Test Array", "type": "integer_t", "is_array": True}
    result = ocsf_schema_v2._generate_attribute(attr, ref_format)
    assert result["type"] == "array"
    assert result["items"]["type"] == "integer"
