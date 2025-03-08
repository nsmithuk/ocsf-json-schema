from urllib.parse import urlparse, parse_qs


class OcsfJsonSchema:
    """Class to manage OCSF JSON schema operations."""

    OCSF_SCHEMA_PREFIX = "https://schema.ocsf.io"  # Base URI for OCSF schemas
    JSON_SCHEMA_VERSION = "https://json-schema.org/draft/2020-12/schema"  # JSON Schema version

    # --------------------------------------------------------------
    # Public

    def __init__(self, json_schema: dict):
        """Initialize with a JSON schema dictionary."""
        self.schema = json_schema
        self.version = json_schema.get("version")
        self.class_name_uid_map: dict[int, str] = {}

    def lookup_class_name_from_uid(self, class_uid: int) -> str:
        if len(self.class_name_uid_map) == 0:
            for cls in self.schema['classes'].values():
                self.class_name_uid_map[cls['uid']] = cls['name']

        if class_uid in self.class_name_uid_map:
            return self.class_name_uid_map[class_uid]

        raise ValueError(f"No class found for uid {class_uid}")

    def get_schema_from_uri(self, uri: str) -> dict:
        """Retrieve a schema from a URI."""
        uri = uri.lower()
        parsed_url = urlparse(uri)
        path_parts = parsed_url.path.strip('/').split('/')

        # Validate URI format
        if len(path_parts) != 4:
            raise ValueError(f"Invalid schema URI: {uri}. Expected format is: "
                             "https://schema.ocsf.io/schema/<version>/<classes|objects>/<name>?profiles=<profiles>")

        version, item_type = path_parts[1], path_parts[2]

        # The name is from position 3, until the end of the path.
        # This covers standard naming (e.g. 'authentication')
        # And extension naming (e.g. win/win_service)
        name = '/'.join(path_parts[3:])

        # Check schema version
        if version != self.version:
            raise ValueError(f"Invalid schema URI: {uri}. Expected schema version {self.version}.")

        # Extract profiles from query string
        query_params = parse_qs(parsed_url.query)
        profiles = query_params.get("profiles", [""])[0]
        profiles = profiles.split(",") if profiles else []

        # Return schema based on item type
        match item_type:
            case "classes":
                return self.get_class_schema(name, profiles)
            case "objects":
                return self.get_object_schema(name, profiles)
            case _:
                raise ValueError(f"Invalid schema URI: {uri}. Expects lookup for classes or objects.")

    def get_class_schema(self, class_name: str, profiles: list[str] = []) -> dict:
        """Generate JSON schema for a class with optional profiles."""
        class_name = class_name.lower()

        class_dict: dict | None = self.schema.get("classes", {}).get(class_name, None)

        if class_dict is None:
            raise ValueError(f"Class '{class_name}' is not defined")

        schema_id = f"{self.OCSF_SCHEMA_PREFIX}/schema/{self.version}/classes/{class_name}"
        return self._generate_schema(schema_id, class_dict, profiles)

    def get_object_schema(self, object_name: str, profiles: list[str] = []) -> dict:
        """Generate JSON schema for an object with optional profiles."""
        object_name = object_name.lower()

        object_data: dict | None = self.schema.get("objects", {}).get(object_name, None)

        if object_data is None:
            raise ValueError(f"Object '{object_name}' is not defined")

        schema_id = f"{self.OCSF_SCHEMA_PREFIX}/schema/{self.version}/objects/{object_name}"
        return self._generate_schema(schema_id, object_data, profiles)

    # --------------------------------------------------------------
    # Internal

    def _generate_schema(self, schema_id: str, data: dict, profiles: list[str]) -> dict:
        """Generate a JSON schema from data and profiles."""
        # Prepare profile query string
        profile_query_str = ""
        if len(profiles) > 0:
            # Ensure list only contains unique items.
            profiles = list(set(profiles))
            # Set to lowercase, and sorted alphabetically.
            profiles = sorted(s.lower() for s in profiles)
            profile_query_str = f"?profiles={','.join(profiles)}"

        # Format for object references
        ref_format = f"{self.OCSF_SCHEMA_PREFIX}/schema/{self.version}/objects/%s{profile_query_str}"

        # Build base schema
        json_schema = {
            "$schema": self.JSON_SCHEMA_VERSION,
            "$id": schema_id + profile_query_str,
            "title": data.get('caption'),
            "type": "object"
        }

        # Extract properties and required fields
        properties, required = self._extract_attributes(data.get("attributes", {}), profiles, ref_format)
        json_schema["properties"] = properties

        # Only in the instance that an objects has no defined properties do we allow 'additionalProperties'.
        # e.g. the 'object' object.
        json_schema["additionalProperties"] = False if properties else True

        if required:
            json_schema["required"] = sorted(required)

        # Apply constraints
        if 'constraints' in data:

            constraints = data.get('constraints', {})
            if at_least_one := constraints.get('at_least_one'):
                json_schema["anyOf"] = [{"required": [field]} for field in at_least_one]

            if just_one := constraints.get('just_one'):
                json_schema["oneOf"] = [{"required": [field]} for field in just_one]

            if len(constraints) > 0 and not ('just_one' in constraints or 'at_least_one' in constraints):
                raise NotImplementedError("Not constraints implemented yet: " + ", ".join(constraints.keys()))

        return json_schema

    def _extract_attributes(self, attributes: dict, profiles: list[str], ref_format: str) -> tuple[dict, list]:
        """Extract properties and required fields from attributes, filtering by profiles."""
        properties = {}
        required = []

        for attr_name, attr_data in attributes.items():

            # If an attribute is part of a profile, only include it if that profile is selected.
            # Oddly some attributes have a profile value set to null. We should always include those.
            if 'profile' in attr_data and attr_data['profile'] is not None and attr_data['profile'] not in profiles:
                continue

            properties[attr_name] = self._generate_attribute(attr_data, ref_format)
            if attr_data.get("requirement") == "required":
                required.append(attr_name)

        return properties, required

    def _generate_attribute(self, attribute: dict, ref_format: str) -> dict:
        """Generate JSON schema for an attribute."""
        json_schema = {"title": attribute.get('caption')}

        # ---

        # Mark deprecated
        if '@deprecated' in attribute:
            json_schema["deprecated"] = True

        # ---

        attr_type = attribute.get("type")

        base_types = {
            'boolean_t': 'boolean',
            'integer_t': 'integer',
            'float_t': 'number',
            'long_t': 'integer',
            'string_t': 'string',
            'json_t': ['object', 'string', 'integer', 'number', 'boolean', 'array', 'null']
        }

        if self.version == '1.0.0-rc.2':
            # These two scalars are incorrectly defined in 'types' for this version, so we'll override them here.
            base_types.update({
                'subnet_t': 'string',
                'file_hash_t': 'string',
            })

        item = {}

        if attr_type == 'object_t':
            obj_type = attribute.get("object_type")
            if obj_type is None:
                raise ValueError("Object type is not defined")

            item["$ref"] = ref_format % obj_type

        else:
            if attr_type not in self.schema['types']:
                raise ValueError(f"unknown type found: {attr_type}")

            type_definition = self.schema['types'][attr_type]

            # If it's a base type
            if attr_type in base_types:
                item['type'] = base_types[attr_type]

            else:
                # Else it's a scalar type

                # We get the primitive out of the 'types' dictionary.
                primitive = type_definition.get('type')

                if primitive is None or primitive not in base_types:
                    raise ValueError(f" unknown scalar type: {attr_type}")

                item['type'] = base_types[primitive]

            type_constraints = self._generate_type_constraints(
                attr_type,
                item['type'],
                type_definition,
                attribute.get('enum')
            )

            if type_constraints:
                item.update(type_constraints)

        # ---

        if attribute.get('is_array', False):
            json_schema["type"] = 'array'
            json_schema['items'] = item
        else:
            json_schema.update(item)

        return json_schema

    def _generate_type_constraints(self, type_name:str, json_type: str, type_definition: dict, enum: dict | None) -> dict:
        """
        Applies from type constraints.

        We'll stick to using the regex's defined in the OCSF schema, rather than using the built-in
        JSON Schema types, as the two _might_ not align.
        """

        type_format = {}

        if enum:
            values = list(enum.keys())
            match json_type:
                case 'boolean':
                    # There are no examples of this currently, and saves having to deal with Python's crazy
                    # views on what a 'true' string is.
                    raise NotImplementedError("enum support on a boolean type is not currently supported")
                case 'integer':
                    values = list(map(int, values))
                case 'number':
                    values = list(map(float, values))

            if len(values) == 1:
                type_format["const"] = values[0]
            else:
                type_format["enum"] = values


        # ---

        if 'max_len' in type_definition:
            if json_type != 'string':
                raise ValueError(f"max_len is only valid for string types, not {type_name}/{json_type}")
            type_format["maxLength"] = type_definition['max_len']


        if 'range' in type_definition:
            if json_type not in {'integer', 'number'}:
                raise ValueError(f"range is only valid for integer or number types, not {type_name}/{json_type}")

            type_range = type_definition['range']
            if len(type_range) != 2:
                raise ValueError(f"range must have exactly two values, not {type_range}")

            if type_range[0] > type_range[1]:
                raise ValueError(f"the first value must be less than or equal to the second value, not {type_range}")

            type_format["minimum"] = type_range[0]
            type_format["maximum"] = type_range[1]


        if 'regex' in type_definition:
            if json_type != 'string':
                raise ValueError(f"regex is only valid for string types, not {type_name}/{json_type}")
            type_format['pattern'] = type_definition['regex']

            """
            Some older of OCSF versions include regular expressions that are invalid in JSON Schema.
            We'll deal with the as best as we can.
            """
            if self.version == '1.0.0-rc.2' and type_name == 'path_t':
                '''
                Not a valid JSON Schema regex. See:
                https://schema.ocsf.io/1.0.0-rc.2/data_types
                
                path_t is dropped in later versions. We'll just ship this one. 
                '''
                del type_format['pattern']

            elif type_name == 'ip_t' and self.version in {'1.0.0-rc.2', '1.0.0-rc.3', '1.0.0'}:
                '''
                Not a valid JSON Schema regex. See:
                https://schema.ocsf.io/1.0.0-rc.2/data_types
                
                We'll use the regex form 1.4.0 from:
                https://schema.ocsf.io/1.4.0/data_types
                '''
                type_format['pattern'] = r"((^\s*((([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]).){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\s*$)|(^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$))"

        return type_format
