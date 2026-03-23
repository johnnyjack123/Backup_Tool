from program_files.logger import logger
from pathlib import Path
import subprocess
import sys
import stat
import os
from datetime import datetime, timedelta
from program_files.file_handler import save_file
from program_files.sockets import send_socket

def execute_script(script) -> int | None:
    path = Path(script.file_path)

    if not path.exists():
        logger.error(f"Error in execute_script: file path {script.file_path} does not exist or is unavailable")
        return None

    suffix = path.suffix.lower()

    try:
        if suffix == ".py":
            result = subprocess.run([sys.executable, str(path)], check=True)
            return result.returncode

        elif os.name == "nt" and suffix in {".bat", ".cmd"}:
            result = subprocess.run(["cmd", "/c", str(path)], check=True)
            return result.returncode

        elif os.name != "nt" and suffix == ".sh":
            if not os.access(path, os.X_OK):
                mode = os.stat(path).st_mode
                mode |= (mode & 0o444) >> 2
                os.chmod(path, mode)

            result = subprocess.run(["bash", str(path)], check=True)
            return result.returncode

        else:
            logger.error(
                f"Script {script.file_path} can't be executed; either the script type is not supported "
                f"or your OS cannot execute it"
            )
            return None

    except subprocess.CalledProcessError as e:
        logger.error(f"Script {script.file_path} failed with exit code {e.returncode}")
        return e.returncode

    except Exception as e:
        logger.error(f"Error while executing script {script.file_path}: {e}")
        return None

def execute_script_handler(file, entry, script, now):
    result = execute_script(script)
    if result == 0:
        logger.info(f"Successfully executed script: {script.file_paths}")
        status_message = "ok"
        file.backup_paths[entry].status_message = status_message
        file.backup_paths[entry].last_backup = now.isoformat()
        save_file(file)
    else:
        logger.error(f"Error in execution of script: {script.paths}")
        status_message = f"Error in process {script.file_paths}. See logs for more detailed error message."
        file.backup_paths[entry].status_message = status_message
        save_file(file)
    send_socket('status_update', {'id': script.script_id, 'status_message': status_message})
    return

def check_for_script(file, now):
    script_paths = file.file_path
    for entry, script in enumerate(script_paths):
        status = script.status
        if status == "running":
            last_execution = script.last_execution
            if last_execution:
                execution_frequency = script.execution_frequency
                if now - datetime.fromisoformat(last_execution) >= timedelta(hours=execution_frequency):
                    result = execute_script_handler(file, entry, script, now)
            else:
                result = execute_script_handler(file, entry, script, now)
            