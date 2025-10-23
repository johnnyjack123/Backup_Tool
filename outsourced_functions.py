import json
import global_variables
from flask import render_template
data_file_path = global_variables.data_file_path

def save(data):
    global data_file_path
    try:
        with open(data_file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        return render_template("error_page.html", error=f"Error in reading file: {e}")

def read():
    global data_file_path
    try:
        with open(data_file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data
    except Exception as e:
        return render_template("error_page.html", error=f"Error in reading file: {e}")

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

def verify_user_access(username, backup_id):
    file = read()
    # Verify user access
    found = False
    userdata = file["userdata"]
    for user in userdata:
        if user["username"] == username:
            for backup in user["backup_processes"]:
                if backup == backup_id:
                    found = True
    return found