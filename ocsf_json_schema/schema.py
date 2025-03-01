from urllib.parse import urlparse, parse_qs


class OcsfJsonSchema:
    """Class to manage OCSF JSON schema operations."""

    OCSF_SCHEMA_PREFIX = "https://schema.ocsf.io"  # Base URI for OCSF schemas
    JSON_SCHEMA_VERSION = "https://json-schema.org/draft/2020-12/schema"  # JSON Schema version

    OCSF_SCHEMA_TYPE_MAPPING = {  # Maps OCSF types to JSON Schema types
        "boolean_t": "boolean",
        "float_t": "number",
        "integer_t": "integer",
        "long_t": "integer",
        "string_t": "string",
        "json_t": None,
        "object_t": None,
        "datetime_t": "string",
        "ip_t": "string",
        "mac_t": "string",
        "port_t": "integer",
        "timestamp_t": "integer",
        "url_t": "string",
        "email_t": "string",
        "fqdn_t": "string"
    }

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
        attr_type = attribute.get("type")
        json_type = self.OCSF_SCHEMA_TYPE_MAPPING.get(attr_type)

        if json_type:
            json_schema["type"] = json_type

        # Add type-specific formats or constraints
        match attr_type:
            case "datetime_t":
                json_schema["format"] = "date-time"
            case "ip_t":
                json_schema["format"] = "ipv4"
            case "mac_t":
                json_schema["pattern"] = "^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
            case "port_t":
                json_schema["minimum"] = 0
                json_schema["maximum"] = 65535
            case "timestamp_t":
                json_schema["minimum"] = 0
            case "url_t":
                json_schema["format"] = "uri"
            case "email_t":
                json_schema["format"] = "email"
            case "fqdn_t":
                json_schema["format"] = "hostname"

        # Handle enums
        if "enum" in attribute:
            enum_values = [int(k) if attr_type in ["integer_t", "long_t", "port_t", "timestamp_t"] else k
                           for k in attribute["enum"].keys()]
            if len(enum_values) == 1:
                json_schema["const"] = enum_values[0]
            else:
                json_schema["enum"] = enum_values

        # Reference objects
        if attr_type == "object_t":
            obj_type = attribute.get("object_type", None)
            if obj_type is None:
                raise ValueError("Object type is not defined")
            json_schema["$ref"] = ref_format % obj_type

        # Handle arrays
        if attribute.get("is_array", False):
            item_schema = {k: v for k, v in json_schema.items() if k not in ["title", "type"]}
            json_schema = {
                "title": attribute.get('caption'),
                "type": "array",
                "items": item_schema or {"type": json_type} if json_type else {}
            }

        # Mark deprecated
        if '@deprecated' in attribute:
            json_schema["deprecated"] = True

        return json_schema
