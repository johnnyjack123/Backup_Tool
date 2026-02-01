import subprocess
import sys
import platform
from program_files.outsourced_functions import read, save
from program_files.logger import logger
from program_files.sockets import send_socket
from time import perf_counter
import threading
from datetime import datetime, timedelta
import time

def monitor_process(proc, schedule_id):
    start_time = perf_counter()

    # Warten bis Prozess beendet ist
    return_code = proc.wait()

    # Laufzeit berechnen
    elapsed_time = perf_counter() - start_time

    # Daten aktualisieren
    file = read()
    script_data = file["scheduled_scripts"]

    for x, script in enumerate(script_data):
        if script["script_id"] == schedule_id:
            if return_code == 0:
                status = "running"
                message = "ok"
                logger.info(message)
            else:
                status = "failed"
                message = f"Script failed with code {return_code} after {elapsed_time:.2f}s"
                logger.error(message)

            script["status"] = status
            script["status_message"] = message

            send_socket("status", status)
            send_socket('status_update',
                        {'id': script["script_id"], 'status_message': message})

            file["scheduled_scripts"][x] = script
            save(file)
            break

def run_script(script_id):
    file = read()
    script_data = file["scheduled_scripts"]
    for x, script in enumerate(script_data):
        if script["script_id"] == script_id:
            path = script["script_path"]
            try:
                if path.endswith(".bat") and platform.system() == "Windows":
                    proc = subprocess.Popen(["cmd.exe", "/c", path])
                elif path.endswith(".ps1") and platform.system() == "Windows":
                    proc = subprocess.Popen(["powershell.exe", "-File", path])
                elif path.endswith(".sh") and platform.system() == "Linux" or platform.system() == "Darwin":
                    proc = subprocess.Popen(["bash", path])
                elif path.endswith(".py"):
                    proc = subprocess.Popen([sys.executable, path, "arg1", "arg2"])
                else:
                    error = f"Unsupported file suffix in scheduled script {script["name"]}"
                    logger.error(error)
                    script["status_message"] = error
                    send_socket('status_update',
                                {'id': script["script_id"], 'status_message': error})
                    status = "stopped"
                    script["status"] = status
                    send_socket("status", status)
                    file["scheduled_scripts"][x] = script
                    save(file)
                    return False

                monitor_thread = threading.Thread(
                    target=monitor_process,
                    args=(proc, script_id),
                    daemon=True
                )
                monitor_thread.start()
                return True
            except Exception as e:
                error = f"Failed to start {script["script_name"]}: error: {str(e)}"
                logger.error(error)
                script["status"] = "stopped"
                script["status_message"] = error
                send_socket("status", "failed")
                send_socket('status_update',
                            {'id': script["script_id"], 'status_message': error})
                file["scheduled_scripts"][x] = script
                save(file)
                return False

def check_scripts():
    while True:
        file = read()
        now = datetime.now()
        scheduled_scripts = file["scheduled_scripts"]
        if scheduled_scripts:
            for entry, script in enumerate(scheduled_scripts):
                status = script["status"]
                if status == "running":
                    last_execution = script["last_execution"]
                    if last_execution:
                        execution_frequency = int(script["execution_frequency"])
                        if now - datetime.fromisoformat(last_execution) >= timedelta(hours=execution_frequency):
                            result = run_script(script["script_id"])
                            if not result:
                                status_message = f"Error in process {script["name"]}. See logs for more detailed error message."
                                script["status_message"] = status_message
                            else:
                                status_message = "ok"

                            send_socket('status_update',
                                        {'id': script["script_id"], 'status_message': status_message})
                            file["scheduled_scripts"][entry]["status_message"] = status_message
                            new_now = now.isoformat()
                            file["scheduled_scripts"][entry]["last_execution"] = new_now
                            save(file)
                            send_socket("update_script_execution_time", {"name": script["script_id"], "last_execution": new_now})
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
