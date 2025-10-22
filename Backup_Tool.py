from datetime import datetime, timedelta
from pathlib import Path
import shutil
import time
import json
import logging
from flask import Flask, render_template
import threading

app = Flask(__name__)


logging.basicConfig(
    filename="backup_tool.log",      # Name der Logdatei
    level=logging.INFO,           # Minimaler Log-Level (INFO und höher)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Zeitstempel und Log-Level
    datefmt="%Y-%m-%d %H:%M:%S"  # Format des Zeitstempels
)

logger = logging.getLogger()

data_file_path = Path("data.json")

#backup_paths = [
#    {"folder_to_backup": Path(r"C:\Users\jonat\Documents\Programmieren\Backup_Tool\Test_backups"),
#     "folder_to_save_backup": Path(r"C:\Users\jonat\Documents\Programmieren\Backup_Tool\backup")} # Do as many backup and store locations as you want, separated by a comma.
#                                        # Make sure that folder_to_save_backup is noch in folder_to_backup
#]

def save(data):
    with open(data_file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    return

def read():
    with open(data_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
        return data

def ignore_backup(dir, contents):
    return ['backup'] if 'backup' in contents else []

def backup_folders(folder_to_backup, folder_to_save_backup):
    file = read()
    backup_paths = file["backup_paths"]
    for path in backup_paths:
        folder_to_backup = path["folder_to_backup"]
        base_backup_dir = path["folder_to_save_backup"]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_to_save_backup = base_backup_dir / f"backup_{timestamp}"

        shutil.copytree(src=str(folder_to_backup), dst=str(folder_to_save_backup), ignore=ignore_backup)
        print("Successfully copied.")
        logger.info("Successfully copied.")

def backup():
    try:
        print("Backup Tool running.")
        logger.info("Backup Tool running.")
        while True:
            file = read()
            last_backup = file["last_backup"]
            now = datetime.now()
            if last_backup:
                last_backup = datetime.fromisoformat(last_backup)
                if datetime.now() - last_backup >= timedelta(days=1):
                    backup_folders()
                    file["last_backup"] = now.isoformat()
                    save(file)
                    print("Successfully did a Backup")
                    logger.info("Successfully did a Backup")
                time.sleep(86401.0)
            else:
                file["last_backup"] = now.isoformat()
                save(file)
                backup_folders()
                print("Successfully did a Backup")
                logger.info("Successfully did a Backup")
    except Exception as e:
        logger.error(f"Error by backup: {e}", exc_info=True)

if not data_file_path.exists():
    default_content = {
        "last_backup": ""
    }
    with open(data_file_path, 'w', encoding='utf-8') as f:
        json.dump(default_content, f, indent=4)

def check_for_backup():
    while True:
        file = read()
        now = datetime.now()
        backup_paths = file["backup_paths"]
        for entry, path in enumerate(backup_paths):
            last_backup = path["last_backup"]
            if last_backup:
                if now - last_backup >= timedelta(days=1):

            else:
                file["backup_paths"][entry]["last_backup"] = now.isoformat()
                save(file)
        time.sleep(60)

def start_backup():
    thread = threading.Thread(target=backup, daemon=True)
    thread.start()

@app.route("/")
def home():
    file = read()
    backup_paths = file["backup_paths"]
    return render_template("index.html", backup_paths=backup_paths)

if __name__ == "__main__":
    start_backup()
    app.run(host="0.0.0.0", port=5000, debug=True)
