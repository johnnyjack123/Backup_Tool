#import eventlet
import eventlet.wsgi
#eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')