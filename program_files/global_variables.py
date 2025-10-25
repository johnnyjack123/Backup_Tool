from pathlib import Path

data_file_path = Path("data.json")

backup_process_dict = {
        "backup_id": "",
        "folder_to_backup": "",
        "folder_to_save_backup": "",
        "name": "",
        "last_backup": "",
        "backup_frequency": 24,
        "status_message": "",
        "status": "",
        "version_history_length": 10
    }

data_file_dict = {
            "backup_paths": [],
            "userdata": [],
            "server_data": {
                "cookie_key": "",
                "auto_update": "yes"
            }
        }

userdata_dict = {
            "user_id": "",
            "username": "",
            "password_hash": "",
            "salt": "",
            "rank": "user",
            "backup_processes": []
        }