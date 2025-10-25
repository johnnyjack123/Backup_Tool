import json
import program_files.global_variables as global_variables
from flask import render_template, session
import shutil
from pathlib import Path
from typing import Any, Dict, List

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
        default_content = global_variables.data_file_dict
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
    print(folder_to_save_backup.is_dir())
    files = [f for f in folder_to_save_backup.iterdir() if f.is_dir() and f.name.startswith("backup_")]
    print(f"Total files: {files}")
    sorted_files = sorted(files, key=lambda f: f.name)
    return sorted_files

def delete_backup(folder_to_save_backup, version_history_length):
    print("Delete Backup")
    sorted_files = sort_folders(folder_to_save_backup)
    print(f"folder to save backup: {folder_to_save_backup}")
    print(f"sortet files: {sorted_files}")
    x = True
    delete = False
    print(f"Number of files: {len(sorted_files)}")
    while x:
        if len(sorted_files) > int(version_history_length):
            folder_to_delete = sorted_files.pop(0).name
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


def deep_update_with_defaults(entry: dict, defaults: dict) -> dict:
    """Rekursiv Defaults in Entry mergen, ohne bestehende Werte zu überschreiben."""
    for key, default_value in defaults.items():
        if key not in entry:
            entry[key] = default_value
        elif isinstance(default_value, dict) and isinstance(entry[key], dict):
            deep_update_with_defaults(entry[key], default_value)
    return entry


def update_config_with_defaults(data: dict, defaults: dict) -> dict:
    """
    Aktualisiert JSON-Daten rekursiv:
    - Listen (z. B. userdata, backup_paths) werden über alle Einträge gemerged
    - Dicts (z. B. server_data) werden rekursiv zusammengeführt
    """
    for key, default_schema in defaults.items():
        if key not in data:
            data[key] = default_schema
        elif isinstance(data[key], list) and isinstance(default_schema, dict):
            for entry in data[key]:
                deep_update_with_defaults(entry, default_schema)
        elif isinstance(data[key], dict) and isinstance(default_schema, dict):
            deep_update_with_defaults(data[key], default_schema)
    return data


# === Nutzung ===

def migrate_config(config_path: str):
    """Lädt Config, migriert sie und speichert sie zurück"""

    # Defaults zusammenstellen
    defaults = {
        "backup_paths": global_variables.backup_process_dict,
        "userdata": global_variables.userdata_dict,
        "server_data": global_variables.data_file_dict
    }

    # JSON laden
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Schema-Update durchführen (NEUE Funktion!)
    updated_data = update_config_with_defaults(data, defaults)

    # Zurückschreiben
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, indent=4, ensure_ascii=False)

    print("✓ Config erfolgreich migriert!")
    return updated_data
