import json
import program_files.global_variables as global_variables
from flask import render_template, session
import shutil
from pathlib import Path

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
            "server_data": {
                "cookie_key": "",
                "auto_update": "yes"
            }
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

def sort_folders(folder_to_save_backup):
    files = [f for f in folder_to_save_backup.iterdir() if f.is_file() and f.name.startswith("backup_")]
    sorted_files = sorted(files, key=lambda f: f.name)
    return sorted_files

def delete_backup(folder_to_save_backup, version_history_length):
    sorted_files = sort_folders(folder_to_save_backup)
    x = True
    delete = False
    while x:
        if len(sorted_files) > int(version_history_length):
            folder_to_delete = sorted_files[0].name
            backup_folder = Path(folder_to_save_backup)
            absolute_path = backup_folder / folder_to_delete
            shutil.rmtree(absolute_path)
            delete = True
        else:
            x = False
    return delete

def check_rank(username, userdata):
    admin = False
    found = False
    for user in userdata:
        if user["username"] == username:
            found = True
            if user["rank"] == "admin":
                admin = True
            else:
                admin = False
    return found, admin