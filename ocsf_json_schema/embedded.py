from .schema import OcsfJsonSchema
from .utility import entity_name_from_uri, generate_object_name_slug
from urllib.parse import urlparse, parse_qs


class OcsfJsonSchemaEmbedded:
    """Class to manage embedded OCSF JSON schemas, resolving object references internally."""

    # --------------------------------------------------------------
    # Public

    def __init__(self, schema: OcsfJsonSchema | dict):
        """Initialize with a schema object or dictionary."""
        if isinstance(schema, OcsfJsonSchema):
            self.schema = schema
        else:
            self.schema = OcsfJsonSchema(schema)  # Convert dict to OcsfJsonSchema instance

    def lookup_class_name_from_uid(self, class_uid: int) -> str:
        return self.schema.lookup_class_name_from_uid(class_uid)

    def get_schema_from_uri(self, uri: str) -> dict:
        """Retrieve and embed schema from a given URI."""
        return self._embed_objects(self.schema.get_schema_from_uri(uri))

    def get_class_schema(self, class_name: str, profiles: list[str] = []) -> dict:
        """Generate and embed JSON schema for a class with optional profiles."""
        return self._embed_objects(self.schema.get_class_schema(class_name, profiles))

    def get_object_schema(self, object_name: str, profiles: list[str] = []) -> dict:
        """Generate and embed JSON schema for an object with optional profiles."""
        return self._embed_objects(self.schema.get_object_schema(object_name, profiles))

    # --------------------------------------------------------------
    # Internal

    def _embed_objects(self, data: dict) -> dict:
        """Embed referenced objects into the schema under $defs."""
        # Rewrite property references and track seen objects
        data["properties"], objects_seen = self._rewrite_references(data["properties"])

        if not objects_seen:  # Skip if no objects to embed
            return data

        # Extract profiles from the schema's $id URI
        profiles = self._profiles_from_uri(data['$id'])
        data['$defs'] = {}  # Initialize definitions section
        objects_added = set()

        # Process all referenced objects, including nested ones
        while len(objects_seen.difference(objects_added)) > 0:
            objects_to_add = objects_seen.difference(objects_added)
            for obj_name in objects_to_add:
                obj = self.schema.get_object_schema(obj_name, profiles)

                # Objects should not include their own ID, as we need $refs to be relative to the class schema.
                del obj["$id"]

                # Rewrite the ref so it's local.
                obj["properties"], new_objects = self._rewrite_references(obj["properties"])

                object_name_slug = generate_object_name_slug(obj_name)
                data['$defs'][object_name_slug] = obj

                objects_seen.update(new_objects)
                objects_added.add(obj_name)

        return data

    def _rewrite_references(self, properties: dict) -> tuple[dict, set]:
        """Rewrite $ref URIs to local $defs paths and collect referenced object names."""
        objects_seen = set()
        for attr_data in properties.values():
            if '$ref' in attr_data:
                ref = attr_data["$ref"]
                object_name = entity_name_from_uri(ref)
                object_name_slug = generate_object_name_slug(object_name)

                objects_seen.add(object_name)
                attr_data['$ref'] = f"#/$defs/{object_name_slug}"
            elif 'items' in attr_data and '$ref' in attr_data['items']:
                ref = attr_data['items']["$ref"]
                object_name = entity_name_from_uri(ref)
                object_name_slug = generate_object_name_slug(object_name)

                objects_seen.add(object_name)
                attr_data['items']['$ref'] = f"#/$defs/{object_name_slug}"
        return properties, objects_seen

    @staticmethod
    def _profiles_from_uri(uri: str) -> list:
        """Extract profiles from a URI's query string."""
        parsed_url = urlparse(uri)
        query_params = parse_qs(parsed_url.query)
        profiles = query_params.get("profiles", [""])[0]
        return profiles.split(",") if profiles else []
