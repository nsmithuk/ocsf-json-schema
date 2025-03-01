import pytest
import json
import uuid
from ocsf_json_schema import OcsfJsonSchema, get_ocsf_schema
from ocsf_json_schema.embedded import OcsfJsonSchemaEmbedded
from jsonschema import Draft202012Validator, exceptions


@pytest.mark.parametrize("version", [
    "1.0.0-rc.2",
    "1.0.0-rc.3",
    "1.0.0",
    "1.1.0",
    "1.2.0",
    "1.3.0",
    "1.4.0"
])
def test_object_name_from_uri(version):
    data = get_ocsf_schema(version)

    ocsf_schema = OcsfJsonSchemaEmbedded(data)

    # Check all classed 'compile' into valid JSON Schema.
    for name, cls in data['classes'].items():
        try:
            json_schema = None
            json_schema = ocsf_schema.get_class_schema(name, cls.get('profiles', []))

            # This will raise an error if the schema is not valid.
            Draft202012Validator.check_schema(json_schema)
        except exceptions.SchemaError as e:
            if json_schema:
                filename = f"error-{uuid.uuid4()}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(json_schema, f, indent=4, ensure_ascii=False)
                print(f"Error output to: {filename}")
            raise e

    # Check all Objects 'compile' into valid JSON Schema.
    for name, obj in data['objects'].items():
        try:
            json_schema = None
            json_schema = ocsf_schema.get_object_schema(name, obj.get('profiles', []))

            # This will raise an error if the schema is not valid.
            Draft202012Validator.check_schema(json_schema)
        except exceptions.SchemaError as e:
            if json_schema:
                filename = f"error-{uuid.uuid4()}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(json_schema, f, indent=4, ensure_ascii=False)
                print(f"Error output to: {filename}")
            raise e
