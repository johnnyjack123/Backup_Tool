import json
import global_variables
from pathlib import Path

data_file_path = global_variables.data_file_path

def save(data):
    global data_file_path
    with open(data_file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    return

def read():
    global data_file_path
    with open(data_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
        return data

def check_for_data_file():
    global data_file_path
    if not data_file_path.exists():
        default_content = {
            "backup_paths": [],
            "userdata": [],
            "server_data": {}
        }
        with open(data_file_path, 'w', encoding='utf-8') as f:
            json.dump(default_content, f, indent=4)