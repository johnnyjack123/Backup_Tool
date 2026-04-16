from program_files.app import socketio
from program_files.file_handler import load_file
from flask_socketio import emit, join_room, leave_room
from flask import request, session
from program_files.logger import logger
from program_files.outsourced_functions import get_current_user

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
def send_backup_processes():
    user_id = session.get("user_id")
    if not user_id:
        logger.error("User id not found in send_backup_processes.")
        return False
    file = load_file()
    for user in file.userdata:
        if user.user_id == user_id:
            payload = [item.model_dump(mode="json") for item in user.backup_processes]
            socketio.emit("available_backup_processes", payload, to=f"user_{user_id}")
            break
    return

def send_socket(channel, message):
    socketio.emit(channel, message)
    return

@socketio.on("connect")
def handle_connect(auth=None):
    # Authentifizierung prüfen – Beispiel mit Flask-Session
    user_id = session.get("user_id")
    if not user_id:
        logger.error("User id not found in handle_connect.")
        return False

    # User in seinen privaten Raum stecken
    join_room(f"user_{user_id}")
    logger.info(f"{get_current_user()} verbunden, Raum: user_{user_id}")
    send_backup_processes()
    return

@socketio.on("disconnect")
def handle_disconnect():
    user_id = session.get("user_id")
    if user_id:
        leave_room(f"user_{user_id}")
    return

"""
@socketio.on("request_backup_state")
def handle_request_backup_state():
    emit("backup_state", get_backup_state())

def broadcast_backup_state():
    socketio.emit("backup_state", get_backup_state())
"""