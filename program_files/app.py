#import eventlet
import eventlet.wsgi
#eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
BASE_DIR = Path(__file__).resolve().parent

print(f"Base dir: {BASE_DIR}")

static_folder = str(BASE_DIR / "static")
template_folder = str(BASE_DIR / "templates")

print(f"Static: {static_folder}, template: {template_folder}")
app = Flask(__name__, static_folder=static_folder, template_folder=template_folder)
socketio = SocketIO(app, async_mode='threading')