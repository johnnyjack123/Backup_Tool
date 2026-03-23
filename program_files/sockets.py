from program_files.app import socketio
from program_files.file_handler import load_file
from flask_socketio import emit

"""
def get_backup_state(username):
    file = load_file()
    backup_processes = []
    script_processes = []
    for user in file.userdata:
        if user.username == username:
            backup_processes = user.backup_processes
            script_processes = user.script_processes
    return {
        "backup_paths": [item.model_dump(mode="json") for item in data.backup_paths]
    }
"""
def send_socket(channel, message):
    socketio.emit(channel, message)
    return
"""
@socketio.on("request_backup_state")
def handle_request_backup_state():
    emit("backup_state", get_backup_state())

def broadcast_backup_state():
    socketio.emit("backup_state", get_backup_state())
"""