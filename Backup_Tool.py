from datetime import datetime, timedelta
from pathlib import Path
import shutil
import time
import json
import logging
from flask import Flask, render_template, request, redirect, url_for
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

def backup_folders(folder_to_backup, base_backup_dir):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_to_save_backup = base_backup_dir / f"backup_{timestamp}"

        shutil.copytree(src=str(folder_to_backup), dst=str(folder_to_save_backup), ignore=ignore_backup)
        print("Successfully copied.")
        logger.info("Successfully copied.")
        return True
    except Exception as e:
        logger.error(f"Error by backup: {e}", exc_info=True)
        return False

def check_for_backup():
    while True:
        file = read()
        now = datetime.now()
        backup_paths = file["backup_paths"]
        if backup_paths:
            for entry, path in enumerate(backup_paths):
                last_backup = path["last_backup"]
                if last_backup:
                    backup_frequency = path["backup_frequency"]
                    if now - datetime.fromisoformat(last_backup) >= timedelta(hours=backup_frequency):
                        folder_to_backup = path["folder_to_backup"]
                        folder_to_save_backup = path["folder_to_save_backup"]
                        result = backup_folders(folder_to_backup, folder_to_save_backup)
                        if not result:
                            path["status"] = f"Error in process {path["name"]}. See logs for more detailed error message."
                else:
                    file["backup_paths"][entry]["last_backup"] = now.isoformat()
                    save(file)
            time.sleep(60)
        else:
            time.sleep(5)

def start_backup():
    thread = threading.Thread(target=check_for_backup, daemon=True)
    thread.start()

def check_for_data_file():
    global data_file_path
    if not data_file_path.exists():
        default_content = {
            "backup_paths": []
        }
        with open(data_file_path, 'w', encoding='utf-8') as f:
            json.dump(default_content, f, indent=4)

@app.route("/")
def home():
    file = read()
    backup_paths = file["backup_paths"]
    return render_template("index.html", backup_paths=backup_paths)

@app.route("/create_backup_task", methods=["POST"])
def create_backup_task():
    name = request.form.get("name")
    folder_to_backup = request.form.get("folder_to_backup")
    folder_to_save_backup = request.form.get("folder_to_save_backup")
    backup_frequency = request.form.get("backup_frequency")
    entry = {
        "folder_to_backup": folder_to_backup,
        "folder_to_save_backup": folder_to_save_backup,
        "name": name,
        "last_backup": "",
        "backup_frequency": backup_frequency,
        "status": "ok"
    }
    file = read()
    file["backup_paths"].append(entry)
    save(file)
    return redirect(url_for("home"))

@app.route("/edit_backup_task", methods=["POST"])
def edit_backup_task():
    name = request.form.get("name")
    folder_to_backup = request.form.get("folder_to_backup")
    folder_to_save_backup = request.form.get("folder_to_save_backup")
    backup_frequency = request.form.get("backup_frequency")
    file = read()
    for x, entry in enumerate(file["backup_paths"]):
        if entry["name"] == name:
            last_backup = entry["last_backup"]
            status = entry["status"]
            entry = {
                "folder_to_backup": folder_to_backup,
                "folder_to_save_backup": folder_to_save_backup,
                "name": name,
                "last_backup": last_backup,
                "backup_frequency": backup_frequency,
                "status": status
            }

            file["backup_paths"][x] = entry
            save(file)

if __name__ == "__main__":
    check_for_data_file()
    start_backup()
    app.run(host="0.0.0.0", port=5000, debug=True)

#TODO: checken, ob Pfad valid ist, wenn ich, in status pushen