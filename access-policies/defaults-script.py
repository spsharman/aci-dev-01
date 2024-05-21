# BridgeIT/ChatGPT to create the following script. 

# Here's the prompt:

# I need a python script to parse a yaml file and only leave the lines (and the heirarchy) which have name_suffix:""

# It created the script and also this:

# "This script will go through the YAML structure and recursively find all dictionaries that have a name_suffix key with an empty string value. It will then reconstruct the hierarchy of the original YAML content, but only including the parts of the hierarchy that lead to the name_suffix: "" entries. The filtered result is either saved to a new YAML file or printed to the console, depending on which option you choose."

import yaml

def find_name_suffix_empty(node, path=None, result=None):
    if result is None:
        result = {}
    if path is None:
        path = []
        
    if isinstance(node, dict):
        for key, value in node.items():
            if key == 'name_suffix' and value == "":
                # Add the current path to the result
                d = result
                for p in path:
                    d = d.setdefault(p, {})
                d[key] = value
            else:
                find_name_suffix_empty(value, path + [key], result)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            find_name_suffix_empty(item, path + [i], result)
    return result

def load_yaml(file_path):
    with open(file_path, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

def save_yaml(data, file_path):
    with open(file_path, 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)

# Replace 'input.yaml' with the path to your input YAML file
input_yaml = 'default.yaml'
# Replace 'output.yaml' with the path where you want to save the filtered output
output_yaml = 'defaults-cleaned.yaml'

# Load the YAML file
data = load_yaml(input_yaml)
# Find entries with empty name_suffix
filtered_data = find_name_suffix_empty(data)
# Save the filtered data to a new YAML file or print it
save_yaml(filtered_data, output_yaml)
# Uncomment the line below to print instead of saving to a file
# print(yaml.dump(filtered_data, default_flow_style=False)) 