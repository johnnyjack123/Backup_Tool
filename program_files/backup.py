from datetime import datetime, timedelta
from pathlib import Path
import shutil
import threading
from program_files.logger import logger
from program_files.outsourced_functions import sort_folders, read, save
from program_files.sockets import send_socket
import time

def backup_folders(folder_to_backup, base_backup_dir):
    try:
        folder_to_backup = Path(folder_to_backup).resolve()
        base_backup_dir = Path(base_backup_dir).resolve()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_to_save_backup = base_backup_dir / f"backup_{timestamp}"
        folder_to_save_backup = folder_to_save_backup.resolve()

        # Ignorierfunktion, die den Ordner zum Speichern ggf. ausschließt
        def ignore_backup(current_dir, contents):
            ignored = []
            for item in contents:
                item_path = Path(current_dir) / item
                # Prüfe, ob item_path der Zielordner ist oder darin liegt
                if folder_to_save_backup == item_path.resolve() or folder_to_save_backup.is_relative_to(item_path.resolve()):
                    ignored.append(item)
            return ignored

        shutil.copytree(src=str(folder_to_backup), dst=str(folder_to_save_backup), ignore=ignore_backup)
        logger.info("Successfully stored backup.")
        return True
    except Exception as e:
        logger.info(f"Error by backup: {e}")
        return False

def check_for_backup():
    while True:
        file = read()
        now = datetime.now()
        backup_paths = file["backup_paths"]
        if backup_paths:
            for entry, backup in enumerate(backup_paths):
                status = backup["status"]
                if status == "running":
                    last_backup = backup["last_backup"]
                    if last_backup:
                        backup_frequency = int(backup["backup_frequency"])
                        if now - datetime.fromisoformat(last_backup) >= timedelta(hours=backup_frequency):
                            folder_to_backup = Path(backup["folder_to_backup"])
                            folder_to_save_backup = Path(backup["folder_to_save_backup"])
                            result = backup_folders(folder_to_backup, folder_to_save_backup)
                            if not result:
                                status_message = f"Error in process {backup["name"]}. See logs for more detailed error message."
                                backup["status_message"] = status_message
                            else:
                                status_message = "ok"
                                result_delete = delete_backup(folder_to_save_backup, backup["version_history_length"])

                                if result_delete:
                                    logger.info(f"Successfully deleted the oldest backup version of {backup["name"]}.")

                            send_socket('status_update', {'id': backup["backup_id"], 'status_message': status_message})
                            file["backup_paths"][entry]["status_message"] = status_message
                            file["backup_paths"][entry]["last_backup"] = now.isoformat()
                            save(file)
                            update_backup_times()
                    else:
                        file["backup_paths"][entry]["last_backup"] = now.isoformat()
                        save(file)
                        folder_to_backup = backup["folder_to_backup"]
                        folder_to_save_backup = backup["folder_to_save_backup"]
                        result = backup_folders(folder_to_backup, folder_to_save_backup)
                        if not result:
                            status_message = f"Error in process {backup["name"]}. See logs for more detailed error message."
                            backup["status_message"] = status_message
                        else:
                            status_message = "ok"

                        send_socket('status_update', {'id': backup["backup_id"], 'status_message': status_message})
                        file["backup_paths"][entry]["status_message"] = status_message
                        save(file)
                        update_backup_times()
                else:
                    continue

            time.sleep(60)
        else:
            time.sleep(10)

def start_backup():
    thread = threading.Thread(target=check_for_backup, daemon=True)
    thread.start()

def update_backup_times():
    file = read()
    backup_paths = file["backup_paths"]
    backup_times = []
    for entry in backup_paths:
        content = {"name": entry["name"],
                   "last_backup": entry["last_backup"]}
        backup_times.append(content)
    send_socket('backup_time_update', backup_times)

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