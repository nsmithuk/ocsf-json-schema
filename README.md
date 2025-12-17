# OCSF JSON Schema

## Overview

This project provides a tool for generating [JSON Schema](https://json-schema.org/draft/2020-12) files that can
be used for validating instances of events that follow the Open Cybersecurity Schema Framework.

## Project Goal

The goal of this project is to generate OCSF JSON Schema files locally using Python, eliminating the need to download them from [schema.ocsf.io](https://schema.ocsf.io). Given the large number of possible variations across OCSF versions, classes, objects, and profiles, this approach provides a more efficient way to validate events—especially when dealing with diverse inputs. It also reduces reliance on external servers, making validation both faster and more sustainable.

OCSF JSON Schemas are complex, consisting of numerous interrelated classes and objects spanning multiple schema versions. Additionally, the structure must adapt based on the selected OCSF profiles. This tool generates schemas that closely align with those from [schema.ocsf.io](https://schema.ocsf.io) but introduces key differences:

- **Explicit JSON Schema Draft Version**: We explicitly define [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) and validate our outputs against it. The schemas from `schema.ocsf.io` do not specify a draft version.  
- **Extended Features**: We add support for the `deprecated` flag, as well as the `at_least_one` and `just_one` constraints.  
- **Absolute `$id` References**: Classes and objects are assigned absolute `$id` values corresponding to their canonical URIs on `schema.ocsf.io`, ensuring consistency.  

## OCSF Version
The following OCSF versions are packaged for convenience in [ocsf_json_schema/ocsf/](ocsf_json_schema/ocsf/). Please also see 
the [README](ocsf_json_schema/ocsf/README.md) for details on generating the Picket version of the schema files, which 
can give a slight performance boost.

- 1.0.0
- 1.0.0-rc.2
- 1.0.0-rc.3
- 1.1.0
- 1.2.0
- 1.3.0
- 1.4.0
- 1.5.0
- 1.6.0
- 1.7.0

You can also [bring your own schema](#bring-your-own-schema) if required or desired.

## Setup

Requires Python 3.10 or above. There are no other dependencies needed for normal use.

To run the tests, install the dev dependencies (`pytest`, `pytest-cov` & `jsonschema`).
```shell
pip install -e '.[dev]' 
```

Tests can be run with
```shell
pytest
```

## Usage

### Lookup class schemas

This will generate the JSON schema for:
- OCSF Schema 1.4.0
- The 'authentication' class (3002)
- With the 'cloud' and 'datetime' profiles
- Including the schema of all referenced OCSF objects embedded.

```python
import json
from ocsf_json_schema import get_ocsf_schema, OcsfJsonSchemaEmbedded

# Loads the packaged 1.4.0 version of the OCSF Schema
ocsf_schema = OcsfJsonSchemaEmbedded(get_ocsf_schema(version='1.4.0'))

# If you only have the class_uid, you can look up the class_name.
class_name = ocsf_schema.lookup_class_name_from_uid(class_uid=3002)

# Returns the JSON schema for the 'authentication' class, 
# with the 'cloud' and 'datetime' profiles applied.
json_schema = ocsf_schema.get_class_schema(
    class_name=class_name, profiles=['cloud', 'datetime']
)

# See what was generated.
print(json.dumps(json_schema, indent=2))
```

If you don't want objects embedded, i.e. you want the schema only for the class itself, you can 
use the `OcsfJsonSchema` rather than `OcsfJsonSchemaEmbedded`.

### Lookup object schemas

This will generate the JSON schema for:
- OCSF Schema 1.4.0
- The 'metadata' object
- With the 'cloud' and 'datetime' profiles
- Including the schema of all referenced OCSF objects embedded.

```python
import json
from ocsf_json_schema import get_ocsf_schema, OcsfJsonSchemaEmbedded

# Loads the packaged 1.4.0 version of the OCSF Schema
ocsf_schema = OcsfJsonSchemaEmbedded(get_ocsf_schema(version='1.4.0'))

# Returns the JSON schema for the 'metadata' object, 
# with the 'cloud' and 'datetime' profiles applied.
json_schema = ocsf_schema.get_object_schema(
    object_name='metadata', profiles=['cloud', 'datetime']
)

# See what was generated.
print(json.dumps(json_schema, indent=2))
```

If you don't want other objects embedded, i.e. you want the schema only for the object itself, you can 
use the `OcsfJsonSchema` rather than `OcsfJsonSchemaEmbedded`.

### Lookup class or object schemas by their URI

Absolute OCSF schema URIs look like:
- https://schema.ocsf.io/schema/1.4.0/classes/authentication?profiles=cloud,datetime
- https://schema.ocsf.io/schema/1.4.0/objects/metadata?profiles=cloud,datetime

This will generate the JSON schema for:
- OCSF Schema 1.4.0
- The 'authentication' class (3002)
- With the 'cloud' and 'datetime' profiles
- Including the schema of all referenced OCSF objects embedded.

```python
import json
from ocsf_json_schema import get_ocsf_schema, OcsfJsonSchemaEmbedded

# Loads the packaged 1.4.0 version of the OCSF Schema
ocsf_schema = OcsfJsonSchemaEmbedded(get_ocsf_schema(version='1.4.0'))

# Returns the JSON schema for the 'authentication' class, 
# with the 'cloud' and 'datetime' profiles applied.
json_schema = ocsf_schema.get_schema_from_uri(
    uri="https://schema.ocsf.io/schema/1.4.0/classes/authentication?profiles=cloud,datetime"
)

# See what was generated.
print(json.dumps(json_schema, indent=2))
```

## Bring your own schema

If you want to use a version of the OCSF schema that's not packaged (`-dev` instances, for example), then you can 
being your own schema.

For example, download the dev schema:
```shell
curl -o 1.8.0-dev.json https://schema.ocsf.io/1.8.0-dev/export/schema
```
Then
```python
import json
from ocsf_json_schema import get_ocsf_schema, OcsfJsonSchemaEmbedded

with open("1.8.0-dev.json", 'r') as file:
    schema_from_file = json.load(file)

# Loads the version of the OCSF Schema from the above file.
ocsf_schema = OcsfJsonSchemaEmbedded(schema_from_file)

# If you only have the class_uid, you can lookup the class_name.
class_name = ocsf_schema.lookup_class_name_from_uid(class_uid=3002)

# Returns the JSON schema for the 'authentication' class, 
# with the 'cloud' and 'datetime' profiles applied.
json_schema = ocsf_schema.get_class_schema(
    class_name=class_name, profiles=['cloud', 'datetime']
)

# See what was generated.
print(json.dumps(json_schema, indent=2))
```

## Validate an OCSF log against the schema

> [!NOTE]
> The validation process itself is outside the scope of this project, but here's an example of how you _could_ do it.
> `jsonschema` isn't a dependency of `ocsf-json-schema`, so you'll need to install it yourself if you wish to use it.

The generated JSON Schema files can be used with any JSON validator that supports 2020-12. Python's `jsonschema`, for example.

Assuming you have an instance of a OCSF event in the file `authentication.log.json`:
```python
import json
from jsonschema import validate, exceptions
from ocsf_json_schema import get_ocsf_schema, OcsfJsonSchemaEmbedded

# Loads the packaged 1.4.0 version of the OCSF Schema
ocsf_schema = OcsfJsonSchemaEmbedded(get_ocsf_schema(version='1.4.0'))

# Returns the JSON schema for the 'authentication' class, 
# with the 'cloud' and 'datetime' profiles applied.
json_schema = ocsf_schema.get_class_schema(
    class_name='authentication', profiles=['cloud', 'datetime']
)

with open("authentication.log.json", 'r') as file:
    log_file = json.load(file)

try:
    # An exception is raised if the log file's schema is not as expected.
    validate(instance=log_file, schema=json_schema)
    print("Log's schema is valid.")
except exceptions.SchemaError as e:
    print(f"Log's schema is invalid: {e}")
```

### Notes on validation

- `null` values are not supported and, if present, will likely result in the validation failing. If a value is `null`, the key/value pair should be removed before validation. This aligns with the JSON Schema files from [schema.ocsf.io](https://schema.ocsf.io).
- If you are validating a file that was previously parquet, be careful of fields that should be a dictionary, but may have been converted to a list of tuples. The validator will expect these fields to be a dictionary. This will most likely occur for fields of type `object`. For example, `unmapped`.

## Build

This repo can be built as a package with the following.
```shell
pip install build
rm ocsf_json_schema/ocsf/*.pkl
python -m build
```

# Licence
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
