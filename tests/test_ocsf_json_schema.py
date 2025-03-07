import pytest
from ocsf_json_schema import OcsfJsonSchema

SAMPLE_SCHEMA = {
    "version": "1.0.0",
    "classes": {
        "authentication": {
            "uid": 1001,
            "name": "Authentication",
            "caption": "Authentication Event",
            "attributes": {
                "user": {"caption": "User", "type": "string_t", "requirement": "required"},
                "success": {"caption": "Success", "type": "boolean_t"}
            }
        }
    },
    "objects": {
        "user": {
            "caption": "User Object",
            "attributes": {"id": {"caption": "ID", "type": "integer_t"}}
        }
    },
    "types": {
        "string_t": {"type": "string_t"},
        "boolean_t": {"type": "boolean_t"},
        "integer_t": {"type": "integer_t"},
        "float_t": {"type": "float_t"},
        "long_t": {"type": "long_t"},
        "json_t": {"type": "json_t"},
        "custom_scalar_t": {"type": "string_t"},
        "subnet_t": {"type": "subnet_t"},
        "file_hash_t": {"type": "file_hash_t"},
        "ip_t": {"type": "string_t", "regex": ".*"},
        "path_t": {"type": "string_t", "regex": "invalid["}
    }
}

@pytest.fixture
def ocsf_schema():
    return OcsfJsonSchema(SAMPLE_SCHEMA)

@pytest.fixture
def ocsf_schema_rc2():
    schema = SAMPLE_SCHEMA.copy()
    schema["version"] = "1.0.0-rc.2"
    return OcsfJsonSchema(schema)

def test_init():
    schema = OcsfJsonSchema(SAMPLE_SCHEMA)
    assert schema.version == "1.0.0"
    assert schema.class_name_uid_map == {}

def test_lookup_class_name_from_uid(ocsf_schema):
    assert ocsf_schema.lookup_class_name_from_uid(1001) == "Authentication"
    assert ocsf_schema.class_name_uid_map[1001] == "Authentication"
    with pytest.raises(ValueError, match="No class found for uid 999"):
        ocsf_schema.lookup_class_name_from_uid(999)

def test_get_schema_from_uri(ocsf_schema):
    uri = "https://schema.ocsf.io/schema/1.0.0/classes/authentication"
    result = ocsf_schema.get_schema_from_uri(uri)
    assert result["$id"] == uri
    assert result["title"] == "Authentication Event"

    uri = "https://schema.ocsf.io/schema/1.0.0/objects/user?profiles=web"
    result = ocsf_schema.get_schema_from_uri(uri)
    assert result["$id"] == uri
    assert result["title"] == "User Object"

    with pytest.raises(ValueError, match="Invalid schema URI"):
        ocsf_schema.get_schema_from_uri("https://schema.ocsf.io/invalid")
    with pytest.raises(ValueError, match="Invalid schema URI.*Expected schema version"):
        ocsf_schema.get_schema_from_uri("https://schema.ocsf.io/schema/2.0.0/classes/authentication")
    with pytest.raises(ValueError, match="Invalid schema URI.*Expects lookup"):
        ocsf_schema.get_schema_from_uri("https://schema.ocsf.io/schema/1.0.0/invalid/authentication")

def test_get_class_schema(ocsf_schema):
    result = ocsf_schema.get_class_schema("authentication")
    assert result["$id"] == "https://schema.ocsf.io/schema/1.0.0/classes/authentication"
    assert result["properties"]["user"]["type"] == "string"
    assert "user" in result["required"]
    with pytest.raises(ValueError, match="Class 'invalid' is not defined"):
        ocsf_schema.get_class_schema("invalid")

def test_get_object_schema(ocsf_schema):
    result = ocsf_schema.get_object_schema("user", ["web"])
    assert result["$id"] == "https://schema.ocsf.io/schema/1.0.0/objects/user?profiles=web"
    assert result["properties"]["id"]["type"] == "integer"
    with pytest.raises(ValueError, match="Object 'invalid' is not defined"):
        ocsf_schema.get_object_schema("invalid")

def test_generate_schema(ocsf_schema):
    data = {"caption": "Test", "attributes": {"field": {"caption": "Field", "type": "string_t"}}}
    result = ocsf_schema._generate_schema("test_id", data, ["profile"])
    assert result["$id"] == "test_id?profiles=profile"
    assert result["title"] == "Test"
    assert result["type"] == "object"
    assert not result["additionalProperties"]

def test_extract_attributes(ocsf_schema):
    attributes = {
        "field1": {"caption": "Field1", "type": "string_t", "requirement": "required"},
        "field2": {"caption": "Field2", "type": "boolean_t", "profile": "web"},
        "field3": {"caption": "Field3", "type": "integer_t", "profile": None}
    }
    properties, required = ocsf_schema._extract_attributes(attributes, ["web"], "ref_format")
    assert "field1" in properties
    assert "field2" in properties
    assert "field3" in properties
    assert required == ["field1"]

    properties, required = ocsf_schema._extract_attributes(attributes, [], "ref_format")
    assert "field2" not in properties
    assert "field1" in properties
    assert "field3" in properties

def test_generate_attribute_all_types(ocsf_schema):
    ref_format = "ref_format/%s"
    base_type_tests = [
        ("boolean_t", {"type": "boolean"}),
        ("integer_t", {"type": "integer"}),
        ("float_t", {"type": "number"}),
        ("long_t", {"type": "integer"}),
        ("string_t", {"type": "string"}),
        ("json_t", {"type": ["object", "string", "integer", "number", "boolean", "array", "null"]})
    ]
    for type_name, expected in base_type_tests:
        attr = {"caption": f"Test {type_name}", "type": type_name}
        result = ocsf_schema._generate_attribute(attr, ref_format)
        assert result["type"] == expected["type"], f"Failed for {type_name}"
        assert result["title"] == f"Test {type_name}"

    attr = {"caption": "Test Object", "type": "object_t", "object_type": "user"}
    result = ocsf_schema._generate_attribute(attr, ref_format)
    assert result["$ref"] == "ref_format/user"

    attr = {"caption": "Test Array", "type": "integer_t", "is_array": True}
    result = ocsf_schema._generate_attribute(attr, ref_format)
    assert result["type"] == "array"
    assert result["items"]["type"] == "integer"

    attr = {"caption": "Test Object Array", "type": "object_t", "object_type": "user", "is_array": True}
    result = ocsf_schema._generate_attribute(attr, ref_format)
    assert result["type"] == "array"
    assert result["items"]["$ref"] == "ref_format/user"

    attr = {"caption": "Deprecated", "type": "string_t", "@deprecated": True}
    result = ocsf_schema._generate_attribute(attr, ref_format)
    assert result["deprecated"] is True

def test_generate_attribute_rc2_special_cases(ocsf_schema_rc2):
    ref_format = "ref_format/%s"
    attr = {"caption": "Subnet", "type": "subnet_t"}
    result = ocsf_schema_rc2._generate_attribute(attr, ref_format)
    assert result["type"] == "string"

    attr = {"caption": "File Hash", "type": "file_hash_t"}
    result = ocsf_schema_rc2._generate_attribute(attr, ref_format)
    assert result["type"] == "string"

def test_generate_attribute_error_cases(ocsf_schema):
    ref_format = "ref_format/%s"
    with pytest.raises(ValueError, match="Object type is not defined"):
        ocsf_schema._generate_attribute({"type": "object_t"}, ref_format)
    with pytest.raises(ValueError, match="unknown type found: invalid_t"):
        ocsf_schema._generate_attribute({"type": "invalid_t"}, ref_format)
    invalid_schema = SAMPLE_SCHEMA.copy()
    invalid_schema["types"]["bad_scalar_t"] = {"type": "invalid_base"}
    bad_ocsf = OcsfJsonSchema(invalid_schema)
    with pytest.raises(ValueError, match="unknown scalar type: bad_scalar_t"):
        bad_ocsf._generate_attribute({"type": "bad_scalar_t"}, ref_format)

def test_generate_type_constraints_all_variations(ocsf_schema):
    enum_tests = [
        ("string", {"val1": "desc1", "val2": "desc2"}, {"enum": ["val1", "val2"]}),
        ("integer", {"1": "one", "2": "two"}, {"enum": [1, 2]}),
        ("number", {"1.5": "one", "2.5": "two"}, {"enum": [1.5, 2.5]}),
        ("string", {"single": "desc"}, {"const": "single"}),
        ("integer", {"42": "desc"}, {"const": 42})
    ]
    for json_type, enum, expected in enum_tests:
        result = ocsf_schema._generate_type_constraints("test_t", json_type, {"type": "test_t"}, enum)
        assert result == expected, f"Failed for {json_type} enum: expected {expected}, got {result}"

    with pytest.raises(NotImplementedError, match="enum support on a boolean type is not currently supported"):
        ocsf_schema._generate_type_constraints("boolean_t", "boolean", {"type": "boolean_t"}, {"0": "false", "1": "true"})

    max_len_constraints = {"max_len": 100}
    result = ocsf_schema._generate_type_constraints("string_t", "string", {"type": "string_t", **max_len_constraints}, None)
    assert result["maximum"] == 100

    range_constraints = {"range": [0, 255]}
    result = ocsf_schema._generate_type_constraints("integer_t", "integer", {"type": "integer_t", **range_constraints}, None)
    assert result["minimum"] == 0
    assert result["maximum"] == 255

    regex_constraints = {"regex": "^test$"}
    result = ocsf_schema._generate_type_constraints("string_t", "string", {"type": "string_t", **regex_constraints}, None)
    assert result["pattern"] == "^test$"

    with pytest.raises(RuntimeError, match="max_len or range should be set, not both"):
        ocsf_schema._generate_type_constraints("string_t", "string", {"type": "string_t", "max_len": 100, "range": [0, 255]}, None)

    # Test ip_t with version-specific override for 1.0.0
    result = ocsf_schema._generate_type_constraints("ip_t", "string", {"type": "string_t", "regex": ".*"}, None)
    assert result["pattern"].startswith(r"((^\s*((([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])")

    # Test path_t fix for 1.0.0-rc.2
    rc2_schema = OcsfJsonSchema({**SAMPLE_SCHEMA, "version": "1.0.0-rc.2"})
    result = rc2_schema._generate_type_constraints("path_t", "string", {"type": "string_t", "regex": "invalid["}, None)
    assert "pattern" not in result

    # Test ip_t fix for early versions
    for version in ["1.0.0-rc.2", "1.0.0-rc.3", "1.0.0"]:
        version_schema = OcsfJsonSchema({**SAMPLE_SCHEMA, "version": version})
        result = version_schema._generate_type_constraints("ip_t", "string", {"type": "string_t", "regex": "invalid"}, None)
        assert result["pattern"].startswith(r"((^\s*((([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])")