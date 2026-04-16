from datetime import datetime, timedelta
from pathlib import Path
import shutil
import threading
from program_files.logger import logger
from program_files.outsourced_functions import sort_folders
from program_files.sockets import send_socket
import time
from program_files.file_handler import load_file, save_file
from pathlib import Path
from program_files.scheduled_scripts import check_for_script

def backup_folders(folder_to_backup, base_backup_dir, backup, now):
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
        status_message = "ok"
        result_delete = delete_backup(folder_to_save_backup, backup.version_history_length)

        if result_delete:
            logger.info(f"Successfully deleted the oldest backup version of {backup.name}.")

    except Exception as e:
        logger.info(f"Error by backup: {e}")
        status_message = f"Error in process {backup.name}. See logs for more detailed error message."
        backup.status_message = status_message

    send_socket('status_update', {'id': backup.backup_id, 'status_message': status_message})
    file = load_file()
    for x, user in enumerate(file.userdata):
        for y, entry in enumerate(user.backup_processes):
            if entry.backup_id == backup.backup_id:
                file.userdata[x].backup_processes[y].status_message = status_message
                file.userdata[x].backup_processes[y].last_backup = now.isoformat()
    save_file(file)
    return

def check_for_backup(backup_process, now):
    status = backup_process.status
    if status == "running":
        last_backup = backup_process.last_backup
        folder_to_backup = Path(backup_process.folder_to_backup)
        folder_to_save_backup = Path(backup_process.folder_to_save_backup)
        if last_backup:
            backup_frequency = int(backup_process.backup_frequency)
            if now - datetime.fromisoformat(last_backup) >= timedelta(hours=backup_frequency):
                backup_folders(folder_to_backup, folder_to_save_backup, backup_process, now)
        else: # Only, if backup process is new (first time)
            backup_folders(folder_to_backup, folder_to_save_backup, backup_process, now)
        # update_backup_times()
    return

# Worker to coordinate the check, whether an backup or script process is need to being executet
def intervall_worker():
    while True:
        file = load_file()
        now = datetime.now()
        for user in file.userdata:
            if user.backup_processes:
                for entry in user.backup_processes:
                    check_for_backup(entry, now)
            elif user.script_processes:
                for entry in user.backup_processes:
                    check_for_script(entry, now)
            else:
                time.sleep(10)
                continue
        time.sleep(60)

def start_intervall_worker():
    thread = threading.Thread(target=intervall_worker, daemon=True)
    thread.start()

"""
def update_backup_times():
    file = load_file()
    backup_paths = file.backup_paths
    backup_times = []
    for entry in backup_paths:
        content = {"name": entry.name,
                   "last_backup": entry.last_backup}
        backup_times.append(content)
    send_socket('backup_time_update', backup_times)
"""

#TODO: an neue Struktur anpassen
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