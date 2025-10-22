import json
import global_variables

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