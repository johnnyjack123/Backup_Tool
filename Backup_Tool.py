from datetime import datetime, timedelta
from pathlib import Path
import shutil
import time
import logging
import threading
from app import app, socketio
from flask import Flask, render_template, request, redirect, url_for, session
from outsourced_functions import save, read, check_for_data_file
from lib.account import set_cookie_key, login_required, check_log_in, log_user_in, signing_up, log_user_out, validate_passwords
from uuid import uuid4


logging.basicConfig(
    filename="backup_tool.log",      # Name der Logdatei
    level=logging.INFO,           # Minimaler Log-Level (INFO und höher)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Zeitstempel und Log-Level
    datefmt="%Y-%m-%d %H:%M:%S"  # Format des Zeitstempels
)

logger = logging.getLogger()

def ignore_backup(dir, contents):
    return ['backup'] if 'backup' in contents else []

def backup_folders(folder_to_backup, base_backup_dir):
    try:
        folder_to_backup = Path(folder_to_backup)
        base_backup_dir = Path(base_backup_dir)
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
                status = path["status"]
                if status == "running":
                    last_backup = path["last_backup"]
                    if last_backup:
                        backup_frequency = int(path["backup_frequency"])
                        if now - datetime.fromisoformat(last_backup) >= timedelta(hours=backup_frequency):
                            folder_to_backup = Path(path["folder_to_backup"])
                            folder_to_save_backup = Path(path["folder_to_save_backup"])
                            result = backup_folders(folder_to_backup, folder_to_save_backup)
                            if not result:
                                status_message = f"Error in process {path["name"]}. See logs for more detailed error message."
                                path["status_message"] = status_message
                            else:
                                status_message = "ok"

                            socketio.emit('status_update', {'name': path["name"], 'status_message': status_message})
                            file["backup_paths"][entry]["status_message"] = status_message
                            file["backup_paths"][entry]["last_backup"] = now.isoformat()
                            save(file)
                            update_backup_times()
                    else:
                        file["backup_paths"][entry]["last_backup"] = now.isoformat()
                        save(file)
                        folder_to_backup = path["folder_to_backup"]
                        folder_to_save_backup = path["folder_to_save_backup"]
                        result = backup_folders(folder_to_backup, folder_to_save_backup)
                        if not result:
                            status_message = f"Error in process {path["name"]}. See logs for more detailed error message."
                            path["status_message"] = status_message
                        else:
                            status_message = "ok"

                        socketio.emit('status_update', {'name': path["name"], 'status_message': status_message})
                        file["backup_paths"][entry]["status_message"] = status_message
                        save(file)
                        update_backup_times()
                else:
                    continue

            time.sleep(60)
        else:
            time.sleep(5)

def start_backup():
    thread = threading.Thread(target=check_for_backup, daemon=True)
    thread.start()



def update_backup_times():
    print("Update times.")
    file = read()
    backup_paths = file["backup_paths"]
    backup_times = []
    for entry in backup_paths:
        content = {"name": entry["name"],
                   "last_backup": entry["last_backup"]}
        backup_times.append(content)
    socketio.emit('backup_time_update', backup_times)

def validate_filepath(path):
    path = Path(path)
    if path.exists():
        return True
    else:
        return False

@socketio.on('connect')
def handle_connect():
    update_backup_times()

@app.route("/")
@login_required
def home():
    file = read()
    backup_paths = file["backup_paths"]
    userdata = file["userdata"]
    visible_processes = []
    username = session.get("username")
    for user in userdata:
        if user["username"] == username:
            for backup_process_id in user["backup_processes"]:
                for backup in backup_paths:
                    if backup["backup_id"] == backup_process_id:
                        visible_processes.append(backup)
    return render_template("index.html", backup_paths=visible_processes)

@app.route("/create_backup_task", methods=["POST"])
@login_required
def create_backup_task():
    name = request.form.get("name").strip('"').strip("'")
    username = session.get("username")
    folder_to_backup = request.form.get("folder_to_backup")
    folder_to_save_backup = request.form.get("folder_to_save_backup")
    backup_frequency = request.form.get("backup_frequency")
    backup_id = str(uuid4())

    folder_to_backup = folder_to_backup.replace('\\', '\\').strip('"').strip("'")
    folder_to_save_backup = folder_to_save_backup.replace('\\', '\\').strip('"').strip("'")

    result_folder_to_backup = validate_filepath(folder_to_backup)
    result_folder_to_save_backup = validate_filepath(folder_to_save_backup)

    if result_folder_to_backup and result_folder_to_save_backup:
        status_message = "ok"
        status = "running"
    else:
        status_message = "Invalid file path"
        status = "stopped"

    entry = {
        "backup_id": backup_id,
        "folder_to_backup": folder_to_backup,
        "folder_to_save_backup": folder_to_save_backup,
        "name": name,
        "last_backup": "",
        "backup_frequency": int(backup_frequency),
        "status_message": status_message,
        "status": status
    }
    file = read()
    userdata = file["userdata"]
    for x, user in enumerate(userdata):
        if user["username"] == username:
            user["backup_processes"].append(backup_id)
            file["userdata"][x] = user

    file["backup_paths"].append(entry)
    save(file)
    return redirect(url_for("home"))

@app.route("/edit_backup_task", methods=["POST"])
@login_required
def edit_backup_task():
    name = request.form.get("name").strip('"').strip("'")
    folder_to_backup = request.form.get("folder_to_backup").strip('"').strip("'")
    folder_to_save_backup = request.form.get("folder_to_save_backup").strip('"').strip("'")
    backup_frequency = request.form.get("backup_frequency")
    backup_id = request.form.get("backup_id")
    result_folder_to_backup = validate_filepath(folder_to_backup)
    result_folder_to_save_backup = validate_filepath(folder_to_save_backup)

    if result_folder_to_backup and result_folder_to_save_backup:
        status_message = "ok"
        status = "running"
    else:
        status_message = "Invalid file path"
        status = "stopped"
    file = read()
    for x, entry in enumerate(file["backup_paths"]):
        if entry["backup_id"] == backup_id:
            last_backup = entry["last_backup"]
            entry = {
                "backup_id": backup_id,
                "folder_to_backup": folder_to_backup,
                "folder_to_save_backup": folder_to_save_backup,
                "name": name,
                "last_backup": last_backup,
                "backup_frequency": int(backup_frequency),
                "status_message": status_message,
                "status": status
            }

            file["backup_paths"][x] = entry
            save(file)
    return redirect(url_for("home"))

@app.route("/delete_backup_task", methods=["POST"])
@login_required
def delete_backup_task():
    backup_id = request.form.get("backup_id")
    username = session.get("username")
    print(f"Backup id: {backup_id}")
    file = read()
    for x, entry in enumerate(file["backup_paths"]):
        if entry["backup_id"] == backup_id:
            del file["backup_paths"][x]
            break
    for x, entry in enumerate(file["userdata"]):
        if entry["username"] == username:
            del entry["backup_processes"][x]
    save(file)
    return redirect(url_for("home"))

@app.route("/toggle_process_status", methods=["POST"])
@login_required
def toggle_process_status():
    backup_id = request.form.get("backup_id")
    file = read()
    for x, entry in enumerate(file["backup_paths"]):
        if entry["backup_id"] == backup_id:
            if entry["status"] != "stopped":
                if entry["status"] == "running":
                    entry["status"] = "paused"
                else:
                    entry["status"] = "running"
                file["backup_paths"][x] = entry
                save(file)
            else:
                logging.info(f"Process {entry["name"]} can't resumed, because there is an unknown error.")
            break
    return redirect(url_for("home"))

@app.route("/log_in_page")
def log_in_page():
    print("Login page")
    result = check_log_in()
    if result:
        print("Success")
        return redirect(url_for("home"))
    else:
        print("No success")
        return render_template("log_in.html")

@app.route("/log_in", methods=["POST"])
def log_in():
    print("In log in ")
    username = request.form.get("username")
    password = request.form.get("password")

    result = log_user_in(username, password)
    if result != "success":
        return render_template("login_error_page.html", error=result)
    print("success")
    return redirect(url_for("home"))

@app.route("/sign_up_page", methods=["GET"])
def sign_up_page():
    return render_template("sign_up.html")

@app.route("/sign_up", methods=["POST"])
def sign_up():
    username = request.form.get("username")
    password = request.form.get("password")
    confirmed_password = request.form.get("confirm_password")

    result = signing_up(username, password, confirmed_password)
    if result != "success":
        return render_template("login_error_page.html", error=result)
    return render_template("log_in.html")

@app.route("/log_out")
def log_out():
    log_user_out()
    return redirect(url_for("log_in_page"))

@app.route("/settings_page")
def settings_page():
    return render_template("settings.html")

@app.route("/settings", methods=["POST"])
def settings():
    password = request.form.get("password")
    confirmed_password = request.form.get("confirmed_password")
    username = session.get("username")
    new_username = request.form.get("new_username")
    file = read()
    userdata = file["userdata"]
    if password and confirmed_password:
        for x, user in enumerate(userdata):
            if user["username"] == session.get("username"):
                salt = user["salt"]
                if not salt:
                    return render_template("login_error_page", error="No salt found.")

                hashed_password, success = validate_passwords(password, confirmed_password, salt, username, "password only")
                if success:
                    user["password_hash"] = hashed_password
                    file["userdata"][x] = user
                    save(file)
    if new_username:
        for x, user in enumerate(userdata):
            if user["username"] == session.get("username"):
                user["username"] = new_username
                file["userdata"][x] = user
                save(file)
    return redirect(url_for("home"))

if __name__ == "__main__":
    check_for_data_file()
    start_backup()
    set_cookie_key()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)