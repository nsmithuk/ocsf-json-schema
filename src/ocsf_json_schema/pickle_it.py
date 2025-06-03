import glob
import json
import pickle
import os
from pathlib import Path


def pickle_it():
    # Get directory of this script
    script_dir = Path(__file__).parent

    # Loop through all JSON files in the current directory
    for json_file in glob.glob(f"{script_dir}/ocsf/*.json"):
        try:
            # Open and read the JSON file with UTF-8 encoding
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Create the pickle file name by replacing '.json' with '.pkl'
            base_name = os.path.splitext(json_file)[0]
            pickle_file = base_name + '.pkl'

            # Write the data to a pickle file in binary mode
            with open(pickle_file, 'wb') as f:
                pickle.dump(data, f)

            # Print a success message
            print(f"Converted {json_file} to {pickle_file}")

        except json.JSONDecodeError:
            # Handle invalid JSON files
            print(f"Error: Invalid JSON in {json_file}")
        except Exception as e:
            # Handle other potential errors (e.g., file permissions)
            print(f"Error processing {json_file}: {e}")


if __name__ == '__main__':
    pickle_it()
