import hashlib
import os
from app import app
from outsourced_functions import read, save
from functools import wraps
from flask import redirect, url_for, session, request

def set_cookie_key():
    file = read()
    server_data = file["server_data"]

    if server_data["cookie_key"]:
        cookie_key = server_data["cookie_key"]
    else:
        cookie_key = os.urandom(32).hex()
        server_data["cookie_key"] = cookie_key
        file["server_data"] = server_data
        save(file)

    app.secret_key = cookie_key

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for("sign_up_page"))
        return f(*args, **kwargs)
    return wrapper

def validate_passwords(password, confirmed_password, salt, username, mode):
    file = read()
    userdata = file["userdata"]
    hashed_password = hashlib.sha256((str(password) + salt).encode()).hexdigest()
    hashed_confirmed_password = hashlib.sha256((str(confirmed_password) + salt).encode()).hexdigest()
    success = False
    if hashed_password != hashed_confirmed_password:
        return "No password match", success
    if mode != "password only":
        for user in userdata:
            if username == user["username"]:
                return "This user already exists!", success
        if username is None or username == "None":
            return "Username None is not available", success
    success = True
    return hashed_password, success

def check_log_in():
    username = session.get('username')
    file = read()
    userdata = file["userdata"]
    for user in userdata:
        if user["username"] == username:
            return True
    return False

def log_user_in(username, password):
    file = read()
    userdata = file["userdata"]
    for user in userdata:
        if user["username"] == username:
            salt = user["salt"]
            if password:
                hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
                if hashed_password == user["password_hash"]:
                    session['username'] = username
                    return "success"
                else:
                    return "Wrong password"
            else:
                return "No password"
    return "User not found"

def signing_up(username, password, confirmed_password):
    file = read()
    userdata = file["userdata"]
    salt = os.urandom(32).hex()
    hashed_password, success = validate_passwords(password, confirmed_password, salt, username, "whole validation")
    if success:
        entry = {
            "username": username,
            "password_hash": hashed_password,
            "salt": salt
        }
        userdata.append(entry)
        file["userdata"] = userdata
        save(file)
        return "success"
    else:
        return hashed_password

def log_user_out():
    session.clear()  # oder: session.pop('user_id', None); session.pop('username', None)
    return redirect(url_for("log_in_page"))