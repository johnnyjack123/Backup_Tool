import hashlib
import os
from program_files.app import app
from functools import wraps
from flask import redirect, url_for, session
from uuid import uuid4
from program_files.file_handler import load_file, save_file, add_user
from program_files.logger import logger

def set_cookie_key():
    file = load_file()
    serverdata = file.serverdata

    if serverdata.cookie_key:
        cookie_key = serverdata.cookie_key
    else:
        cookie_key = os.urandom(32).hex()
        serverdata.cookie_key = cookie_key
        file.serverdata = serverdata
        save_file(file)

    app.secret_key = cookie_key

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for("sign_up_page"))
        return f(*args, **kwargs)
    return wrapper

def validate_passwords(password, confirmed_password, salt, username, mode):
    file = load_file()
    userdata = file.userdata
    hashed_password = hashlib.sha256((str(password) + salt).encode()).hexdigest()
    hashed_confirmed_password = hashlib.sha256((str(confirmed_password) + salt).encode()).hexdigest()
    success = False
    if hashed_password != hashed_confirmed_password:
        return "No password match or username already exists.", success
    if mode != "password only":
        for user in userdata:
            if username == user.username:
                return "No password match or username already exists.", success
        if username is None or username == "None":
            return "Username None is not available", success
    success = True
    return hashed_password, success

def check_log_in():
    username = session.get('username')
    file = load_file()
    userdata = file.userdata
    for user in userdata:
        if user.username == username:
            return True
    return False

def log_user_in(username, password):
    file = load_file()
    userdata = file.userdata
    for user in userdata:
        if user.username == username:
            salt = user.salt
            if password:
                hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
                if hashed_password == user.password_hash:
                    session['username'] = username
                    session['user_id'] = user.user_id
                    return "success"
                else:
                    return "Wrong password"
            else:
                return "No password"
    return "User not found"

def signing_up(username, password, confirmed_password):
    file = load_file()
    userdata = file.userdata
    salt = os.urandom(32).hex()
    hashed_password, success = validate_passwords(password, confirmed_password, salt, username, "whole validation")
    user_id = str(uuid4())
    if success:
        if not userdata:
            rank = "admin"
        else:
            rank = "user"

        entry = {
            "user_id": user_id,
            "username": username,
            "password_hash": hashed_password,
            "salt": salt,
            "rank": rank
        }
        add_user(entry)

        return "success"
    else:
        return hashed_password

def log_user_out():
    session.clear()  # oder: session.pop('user_id', None); session.pop('username', None)
    return redirect(url_for("log_in_page"))

def change_password(file, username, password, confirmed_password):
    for x, user in enumerate(file.userdata):
        if user.username == username:
            salt = user.salt
            if not salt:
                return False, "No salt found"

            hashed_password, success = validate_passwords(password, confirmed_password, salt, username, "password only")
            if success:
                user.password_hash = hashed_password
                file.userdata[x] = user
                save_file(file)
                logger.info("Successfully changed password.")
                return True, ""
            else:
                msg = f"Something went wrong by changing the password: {hashed_password}"
                logger.info(msg)
                return False, msg
    return False, "User not found"

def change_username(file, username, new_username):
    found = False
    for x, user in enumerate(file.userdata):
        if user.username == username:
            found = True
            user.username = new_username
            file.userdata[x] = user
            save_file(file)
            logger.info("Successfully changed username.")
            break
        else:
            logger.error("User in change_username not found")
            break
    return found