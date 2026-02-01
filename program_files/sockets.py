from program_files.app import socketio

def send_socket(channel, message):
    socketio.emit(channel, message)
    return
