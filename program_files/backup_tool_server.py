from pathlib import Path
import time
from program_files.app import app, socketio
from flask import render_template, request, redirect, url_for, session
from program_files.outsourced_functions import verify_user_access, check_rank, migrate_config, convert_home_path, fill_backup_task
from program_files.lib.account import set_cookie_key, login_required, check_log_in, log_user_in, signing_up, log_user_out, change_password, change_username
from uuid import uuid4
from program_files.logger import logger
from program_files.backup import update_backup_times, start_backup
from program_files.file_handler import load_file, save_file, add_backup_process, edit_backup_process

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
    file = load_file()
    backup_paths = file.backup_paths
    userdata = file.userdata
    visible_processes = []
    username = session.get("username")
    if not username:
        return render_template("error_page.html", error="Unauthorized user. Try to log in again.")

    found = False
    try:
        for user in userdata:
            if user.username == username:
                found = True
                if user.backup_processes:
                    for backup_process_id in user.backup_processes:
                        for backup in backup_paths:
                            if backup.backup_id == backup_process_id:
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
    version_history_length = request.form.get("version_history_length")

    if not name or not username or not folder_to_backup or not folder_to_save_backup or not backup_frequency or not version_history_length:
        logger.error(f"Some input is missing in create_backup_task")
        return render_template("error_page.html", error=f"Some input is missing in create_backup_task")

    folder_to_backup, folder_to_save_backup = convert_home_path(folder_to_backup, folder_to_save_backup)


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

    
    result, entry = fill_backup_task(folder_to_backup, folder_to_save_backup, name, backup_frequency, status_message, status, version_history_length, username)
    
    if not result:
        return render_template("error_page.html", error=entry)
    
    add_backup_process(entry)
    
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
    version_history_length = request.form.get("version_history_length")

    if not name or not folder_to_backup or not folder_to_save_backup or not backup_frequency or not backup_id or not username or not backup_id or not version_history_length:
        logger.error(f"Some input is missing in edit_backup_task.")
        return render_template("error_page.html", error=f"Some input is missing in edit_backup_task.")

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
    
    file = load_file()

    found = False
    for x, entry in enumerate(file.backup_paths):
        if entry.backup_id == backup_id:
            found = True

            new_entry = {
                "username": username,
                "name": name,
                "folder_to_backup": folder_to_backup,
                "folder_to_save_backup": folder_to_save_backup,
                "backup_frequency": backup_frequency,
                "backup_id": backup_id,
                "version_history_length": version_history_length,
                "last_backup": entry.last_backup,
                "status_message": status_message,
                "status": status
                }
            edit_backup_process(new_entry, x)

            logger.info(f"Successfully edited backup {name}.")
            break
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

    result = verify_user_access(username, backup_id)

    if not result:
        return render_template("error_page.html", error=f"You are now allowed to access this backup process.")
    
    file = load_file()
    for x, entry in enumerate(file.backup_paths):
        if entry.backup_id == backup_id:
            del file.backup_paths[x]
            break
    for x, entry in enumerate(file.userdata):
        if entry.username == username:
            for y, entry_id in enumerate(entry.backup_processes):
                if entry_id == backup_id:
                    del entry.backup_processes[y]
    logger.info(f"Successfully deleted backup {backup_id}")
    save_file(file)
    return redirect(url_for("home"))

@app.route("/toggle_process_status", methods=["POST"])
@login_required
def toggle_process_status():
    username = session.get("username")
    backup_id = request.form.get("backup_id")
    print(f"Username: {username}, backup id: {backup_id}")
    if not backup_id or not username:
        logger.error("Some inputs are missing or you tried to pause an stopped process in toggle_process_status. If the second option is true you have to solve the issue first (probably a wrong file path) before you are able, to pause/continue this process again.")
        return render_template("error_page.html", error="Some inputs are missing in toggle_process_status.")

    result = verify_user_access(username, backup_id)
    if not result:
        return render_template("error_page.html", error=f"You are now allowed to access this backup process.")
    
    found = False
    file = load_file()

    for x, entry in enumerate(file.backup_paths):
        if entry.backup_id == backup_id:
            found = True
            if entry.status != "stopped":
                if entry.status == "running":
                    entry.status = "paused"
                    logger.info(f"Process {entry.name} paused")
                else:
                    entry.status = "running"
                    logger.info(f"Process {entry.name} resumed")
                file.backup_paths[x] = entry
                save_file(file)
            else:
                logger.error(f"Process {entry.name} can't resumed, due to an unknown error.")
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
    file = load_file()
    userdata = file.userdata
    if not userdata:
        return render_template("sign_up.html")
    else:
        return redirect(url_for("log_in_page"))

@app.route("/sign_up", methods=["POST"])
def sign_up():
    file = load_file()
    userdata = file.userdata
    if not userdata:
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
    else:
        return redirect(url_for("log_in_page"))

@app.route("/log_out")
def log_out():
    log_user_out()
    logger.info("Logged out.")
    return redirect(url_for("log_in_page"))

@app.route("/settings_page")
def settings_page():
    file = load_file()
    userdata = file.userdata
    username = session.get("username")

    if not username:
        logger.error("Some input is missing in settings_page.")
        return render_template("error_page.html", error="Some input is missing in settings_page.")

    found, admin = check_rank(username, userdata)
    if not found:
        return render_template("error_page.html", error=f"User not found.")

    if admin:
        users = []
        for user in userdata:
            users.append(user.username)
    else:
        users = []
    return render_template("settings.html", users=users)

@app.route("/settings", methods=["POST"])
def settings():
    password = request.form.get("password")
    confirmed_password = request.form.get("confirmed_password")
    username = session.get("username")
    new_username = request.form.get("new_username")
    add_user_name = request.form.get("add_user_name")
    add_user_password = request.form.get("add_user_password")
    add_user_confirmed_password = request.form.get("add_user_confirmed_password")

    file = load_file()
    did_change = False

    if password and confirmed_password:
        result, msg = change_password(file, username, password, confirmed_password)
        if not result:
            return render_template("error_page.html", error=msg)
        did_change = True

    if new_username:
        did_change = True
        result = change_username(file, username, new_username)
        if not result:
            return render_template("error_page.html", error=f"User not found.")

    if add_user_name and add_user_password and add_user_confirmed_password:
        did_change = True
        result = signing_up(add_user_name, add_user_password, add_user_confirmed_password)
        if result == "success":
            pass
        else:
            logger.error(f"Something went wrong by creating the new user: {result}")
            return render_template("error_page.html", error=f"Something went wrong by creating the new user: {result}")
    if not did_change:
        logger.info("Nothing changed because some inputs are missing.")
    return redirect(url_for("settings_page"))

if __name__ == "__main__":
    #check_for_data_file()
    #config = migrate_config(global_variables.data_file_path)
    file = load_file()
    print(f"Userdata: {file.userdata}")
    start_backup()
    set_cookie_key()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)