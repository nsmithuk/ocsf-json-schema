import json
import pickle
from pathlib import Path


def load_ocsf_schema_json(path: str) -> dict:
    """Load OCSF schema from a JSON file."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_ocsf_schema_pickle(path: str) -> dict:
    """Load OCSF schema from a Pickle file."""
    with open(path, 'rb') as file:
        return pickle.load(file)


def get_ocsf_schema(version: str) -> dict:
    """Get OCSF schema for a version, preferring Pickle if available, else JSON."""
    script_dir = Path(__file__).parent  # Get directory of this script
    path_prefix = f"{script_dir}/ocsf/{version}"  # Build path to schema files

    if Path(f"{path_prefix}.pkl").exists():  # Check if Pickle file exists
        return load_ocsf_schema_pickle(f"{path_prefix}.pkl")

    return load_ocsf_schema_json(f"{path_prefix}.json")  # Fallback to JSON


def get_packaged_versions() -> set:
    """Get a set of the packaged versions of OCSF."""
    script_dir = Path(__file__).parent
    path_prefix = f"{script_dir}/ocsf/"
    return set(
        [file.stem for file in Path(path_prefix).glob("*.json")] +
        [file.stem for file in Path(path_prefix).glob("*.pkl")]
    )
