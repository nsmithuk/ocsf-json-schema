from urllib.parse import urlparse, parse_qs


def entity_name_from_uri(uri: str) -> str:
    """Extract the class or object name from a URI path."""
    parsed_url = urlparse(uri)
    path_parts = parsed_url.path.strip('/').split('/')

    # The name is from position 3, until the end of the path.
    # This covers standard naming (e.g. 'authentication')
    # And extension naming (e.g. win/win_service)
    return '/'.join(path_parts[3:])


def generate_object_name_slug(object_name: str) -> str:
    return object_name.replace('/', '_')
