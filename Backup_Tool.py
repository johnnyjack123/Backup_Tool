from datetime import datetime, timedelta
from pathlib import Path
import shutil
import time
import logging
import threading
from app import app, socketio
from flask import Flask, render_template, request, redirect, url_for, session
from outsourced_functions import save, read, check_for_data_file, verify_user_access
from lib.account import set_cookie_key, login_required, check_log_in, log_user_in, signing_up, log_user_out, validate_passwords
from uuid import uuid4

# Eigenen Logger erstellen
logger = logging.getLogger("my_backup_logger")
logger.setLevel(logging.INFO)

# File Handler für Datei-Ausgabe konfigurieren
file_handler = logging.FileHandler("backup_tool.log")
file_handler.setLevel(logging.INFO)

# Format für Logs definieren
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)

# Handler dem Logger hinzufügen
logger.addHandler(file_handler)


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
    if not username:
        return render_template("error_page.html", error="Unauthorized user. Try to log in again.")

    found = False
    try:
        for user in userdata:
            if user["username"] == username:
                found = True
                if user["backup_processes"]:
                    for backup_process_id in user["backup_processes"]:
                        for backup in backup_paths:
                            if backup["backup_id"] == backup_process_id:
                                visible_processes.append(backup)
    except Exception as e:
        return render_template("error_page.html", error=f"Internal server error: {e}")

    if not found:
        return render_template("error_page.html", error=f"User not found.")

    return render_template("index.html", backup_paths=visible_processes)

@app.route("/create_backup_task", methods=["POST"])
@login_required
def create_backup_task():
    name = request.form.get("name").strip('"').strip("'")
    username = session.get("username")
    folder_to_backup = request.form.get("folder_to_backup")
    folder_to_save_backup = request.form.get("folder_to_save_backup")
    backup_frequency = request.form.get("backup_frequency")

    if not name or not username or not folder_to_backup or not folder_to_save_backup or not backup_frequency:
        logger.error(f"Some input is missing in create_backup_task")
        return render_template("error_page.html", error=f"Some input is missing in create_backup_task")

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
        logger.error("Invalid file path.")

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
    found = False
    try:
        for x, user in enumerate(userdata):
            if user["username"] == username:
                found = True
                user["backup_processes"].append(backup_id)
                file["userdata"][x] = user
    except Exception as e:
        return render_template("error_page.html", error=f"Internal server error: {e}")
    if not found:
        return render_template("error_page.html", error=f"User not found.")
    file["backup_paths"].append(entry)
    save(file)
    logger.info("Successfully created backup process.")
    return redirect(url_for("home"))

@app.route("/edit_backup_task", methods=["POST"])
@login_required
def edit_backup_task():
    username = session.get("username")
    name = request.form.get("name").strip('"').strip("'")
    folder_to_backup = request.form.get("folder_to_backup").strip('"').strip("'")
    folder_to_save_backup = request.form.get("folder_to_save_backup").strip('"').strip("'")
    backup_frequency = request.form.get("backup_frequency")
    backup_id = request.form.get("backup_id")

    if not name or not folder_to_backup or not folder_to_save_backup or not backup_frequency or not backup_id or not username:
        logger.error(f"Some input is missing in edit_backup_task.")
        return render_template("error_page.html", error=f"Some input is missing in edit_backup_task.")

    file = read()
    result = verify_user_access(username, backup_id)

    if not result:
        return render_template("error_page.html", error=f"You are now allowed to access this backup process.")

    result_folder_to_backup = validate_filepath(folder_to_backup)
    result_folder_to_save_backup = validate_filepath(folder_to_save_backup)

    if result_folder_to_backup and result_folder_to_save_backup:
        status_message = "ok"
        status = "running"
    else:
        status_message = "Invalid file path"
        status = "stopped"
        logger.error("Invalid file path.")

    found = False
    for x, entry in enumerate(file["backup_paths"]):
        if entry["backup_id"] == backup_id:
            found = True
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
            logger.info(f"Successfully edited backup {name}.")
    if not found:
        return render_template("error_page.html", error=f"Backup process not found.")
    return redirect(url_for("home"))

@app.route("/delete_backup_task", methods=["POST"])
@login_required
def delete_backup_task():
    backup_id = request.form.get("backup_id")
    username = session.get("username")
    if not backup_id or not username:
        print("In if")
        logger.error(f"Some input is missing in delete_backup_task.")
        return render_template("error_page.html", error=f"Some input is missing in delete_backup_task.")

    file = read()

    result = verify_user_access(username, backup_id)

    if not result:
        return render_template("error_page.html", error=f"You are now allowed to access this backup process.")

    for x, entry in enumerate(file["backup_paths"]):
        if entry["backup_id"] == backup_id:
            del file["backup_paths"][x]
            break
    for x, entry in enumerate(file["userdata"]):
        if entry["username"] == username:
            for y, entry_id in enumerate(entry["backup_processes"]):
                if entry_id == backup_id:
                    del entry["backup_processes"][y]
    logger.info(f"Successfully deleted backup {backup_id}")
    save(file)
    return redirect(url_for("home"))

@app.route("/toggle_process_status", methods=["POST"])
@login_required
def toggle_process_status():
    username = session.get("username")
    backup_id = request.form.get("backup_id")
    if not backup_id or not username:
        logger.error("Some inputs are missing or you tried to pause an stopped process in toggle_process_status. If the second option is true you have to solve the issue first (probably a wrong file path) before you are able, to pause/continue this process again.")
        return render_template("error_page.html", error="Some inputs are missing in toggle_process_status.")

    file = read()
    result = verify_user_access(username, backup_id)
    if not result:
        return render_template("error_page.html", error=f"You are now allowed to access this backup process.")
    found = False

    for x, entry in enumerate(file["backup_paths"]):
        if entry["backup_id"] == backup_id:
            found = True
            if entry["status"] != "stopped":
                if entry["status"] == "running":
                    entry["status"] = "paused"
                    logger.info(f"Process {entry["name"]} paused")
                else:
                    entry["status"] = "running"
                    logger.info(f"Process {entry["name"]} resumed")
                file["backup_paths"][x] = entry
                save(file)
            else:
                logger.error(f"Process {entry["name"]} can't resumed, because there is an unknown error.")
            break

    if not found:
        return render_template("error_page.html", error=f"Backup process not found.")

    return redirect(url_for("home"))

@app.route("/log_in_page")
def log_in_page():
    result = check_log_in()
    if result:
        logger.info("Successfully logged in.")
        return redirect(url_for("home"))
    else:
        logger.info("Unregistert user")
        return render_template("log_in.html")

@app.route("/log_in", methods=["POST"])
def log_in():
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        logger.error("Some input is missing in log_in.")
        return render_template("error_page.html", error="Some input is missing in log_in.")

    result = log_user_in(username, password)
    if result != "success":
        logger.error("Log in attempt failed.")
        return render_template("error_page.html", error=result)
    logger.info("Successfully logged in.")
    return redirect(url_for("home"))

@app.route("/sign_up_page", methods=["GET"])
def sign_up_page():
    return render_template("sign_up.html")

@app.route("/sign_up", methods=["POST"])
def sign_up():
    username = request.form.get("username")
    password = request.form.get("password")
    confirmed_password = request.form.get("confirm_password")

    if not username or not password or not confirmed_password:
        logger.error("Some input is missing in sign_up.")
        return render_template("error_page.html", error="Some input is missing in sign_up.")

    result = signing_up(username, password, confirmed_password)
    if result != "success":
        logger.error("Failed to create account.")
        return render_template("error_page.html", error=result)
    logger.info("Successfully created an account.")
    return render_template("log_in.html")

@app.route("/log_out")
def log_out():
    log_user_out()
    logger.info("Logged out.")
    return redirect(url_for("log_in_page"))

@app.route("/settings_page")
def settings_page():
    file = read()
    userdata = file["userdata"]
    username = session.get("username")

    if not username:
        logger.error("Some input is missing in settings_page.")
        return render_template("error_page.html", error="Some input is missing in settings_page.")

    admin = False
    found = False
    for user in userdata:
        if user["username"] == username:
            found = True
            if user["rank"] == "admin":
                admin = True
            else:
                admin = False
    if not found:
        return render_template("error_page.html", error=f"User not found.")

    if admin:
        users = []
        for user in userdata:
            users.append(user["username"])
    else:
        users = []
    return render_template("settings.html", users=users)

@app.route("/settings", methods=["POST"])
def settings():
    password = request.form.get("password")
    confirmed_password = request.form.get("confirmed_password")
    username = session.get("username")
    new_username = request.form.get("new_username")

    if not username or not password or not confirmed_password or not new_username:
        logger.error("Some input is missing in settings.")
        return render_template("error_page.html", error="Some input is missing in settings.")

    file = read()
    userdata = file["userdata"]
    if password and confirmed_password:
        found = False
        for x, user in enumerate(userdata):
            if user["username"] == username:
                found = True
                salt = user["salt"]
                if not salt:
                    return render_template("login_error_page", error="No salt found.")

                hashed_password, success = validate_passwords(password, confirmed_password, salt, username, "password only")
                if success:
                    user["password_hash"] = hashed_password
                    file["userdata"][x] = user
                    save(file)
                    logger.info("Successfully changed password.")
        if not found:
            return render_template("error_page.html", error=f"User not found.")

    if new_username:
        found = False
        for x, user in enumerate(userdata):
            if user["username"] == username:
                found = True
                user["username"] = new_username
                file["userdata"][x] = user
                save(file)
                logger.info("Successfully changed username.")
        if not found:
            return render_template("error_page.html", error=f"User not found.")

    return redirect(url_for("home"))

if __name__ == "__main__":
    check_for_data_file()
    start_backup()
    set_cookie_key()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)