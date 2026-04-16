import json
import program_files.global_variables as global_variables
from pathlib import Path
from uuid import uuid4
from program_files.logger import logger
from program_files.file_handler import load_file, save_file
from flask import session
count = 0


def verify_user_access(user_id, backup_id):
    file = load_file()
    # Verify user access
    found = False
    userdata = file.userdata
    for user in userdata:
        if user.user_id == user_id:
            for backup in user.backup_processes:
                if backup == backup_id:
                    found = True
                    break
    return found

def sort_folders(folder_to_save_backup):
    print(folder_to_save_backup.is_dir())
    files = [f for f in folder_to_save_backup.iterdir() if f.is_dir() and f.name.startswith("backup_")]
    print(f"Total files: {files}")
    sorted_files = sorted(files, key=lambda f: f.name)
    return sorted_files

def check_rank(user_id, userdata):
    admin = False
    found = False
    for user in userdata:
        if user.user_id == user_id:
            found = True
            if user.rank == "admin":
                admin = True
            else:
                admin = False
    return found, admin


def convert_home_path(file_path):
    home_folder = Path.home()
    #new_paths = []
    for i, x in enumerate(file_path):
        if x.startswith("~"):
            file_path[i] = x.replace("~", str(home_folder), 1)

    return file_path

def add_backup_to_user(backup_id, user_id):
    file = load_file()
    userdata = file.userdata
    found = False
    try:
        for x, user in enumerate(userdata):
            if user.user_id == user_id:
                found = True
                user.backup_processes.append(backup_id)
                file.userdata[x] = user
                save_file(file)
    except Exception as e:
        msg = f"Error in add_backup_to_user(): {e}"
        logger.error(msg)
        return False, msg
    if not found:
        msg = "User not found in add_backup_to_user()"
        logger.error(msg)
        return False, msg
    else:
        return True, ""
    
def add_script_to_user(user_id, script_id):
    file = load_file()
    userdata = file.userdata
    found = False
    try:
        for x, user in enumerate(userdata):
            if user.user_id == user_id:
                found = True
                user.script_processes.append(script_id)
                file.userdata[x] = user
                save_file(file)
    except Exception as e:
        msg = f"Error in add_script_to_user(): {e}"
        logger.error(msg)
        return False, msg
    if not found:
        msg = "User not found in add_script_to_user()"
        logger.error(msg)
        return False, msg
    else:
        return True, ""

# Returns username based on userid
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    file = load_file()
    for user in file.userdata:
        if user.user_id == user_id:
            return user
    return None

"""
def fill_backup_task(folder_to_backup, folder_to_save_backup, name, backup_frequency, status_message, status, version_history_length, username):
    backup_id = str(uuid4())
    entry = {
        "backup_id": backup_id,
        "folder_to_backup": folder_to_backup,
        "folder_to_save_backup": folder_to_save_backup,
        "name": name,
        "backup_frequency": int(backup_frequency),
        "status_message": status_message,
        "status": status,
        "version_history_length": int(version_history_length),
    }

    result, msg = add_backup_to_user(backup_id, username)
    if result:
        return True, entry
    else:
        return False, msg
        """
"""
def fill_script_task(file_path, name, execute_frequency, status_message, status, version_history_length, username):
    script_id = str(uuid4())
    entry = {
        "script_id": script_id,
        "file_path": file_path,
        "name": name,
        "execute_frequency": int(execute_frequency),
        "status_message": status_message,
        "status": status,
        "version_history_length": int(version_history_length),
    }

    result, msg = add_backup_to_user(backup_id, username)
    if result:
        return True, entry
    else:
        return False, msg

"""