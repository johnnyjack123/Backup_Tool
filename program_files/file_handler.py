from __future__ import annotations

from pathlib import Path
from threading import RLock
from pydantic import BaseModel, Field
import json
import os
import tempfile


file_path = Path("./data.json")
_lock = RLock()


class Userdata(BaseModel):
    user_id: str = ""
    username: str = ""
    password_hash: str = ""
    salt: str = ""
    rank: str = ""
    backup_processes: list[str] = Field(default_factory=list)


class Serverdata(BaseModel):
    cookie_key: str = ""
    auto_update: str = "yes"


class Backuppaths(BaseModel):
    backup_id: str = ""
    folder_to_backup: str = ""
    folder_to_save_backup: str = ""
    name: str = ""
    last_backup: str = ""
    backup_frequency: str = ""
    status_message: str = ""
    status: str = ""
    version_history_length: int = 0


class Main(BaseModel):
    file_version: float = 0.0
    backup_paths: list[Backuppaths] = Field(default_factory=list)
    userdata: list[Userdata] = Field(default_factory=list)
    serverdata: Serverdata = Field(default_factory=Serverdata)



class UserStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = RLock()

    def ensure_exists(self) -> None:
        with self._lock:
            ensure_file_exists(self.path)

    def load(self) -> Main:
        with self._lock:
            return load_and_migrate(self.path)

    def save(self, data: Main) -> None:
        with self._lock:
            save_file(data, self.path)

    def get_user(self, username: str) -> Userdata | None:
        data = self.load()
        for user in data.userdata:
            if user.username == username:
                return user
        return None

    def add_user(self, user_dict: dict) -> Userdata:
        with self._lock:
            data = load_and_migrate(self.path)
            user = Userdata(**user_dict)
            data.userdata.append(user)
            save_file(data, self.path)
            return user


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")

    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp, path)

        # Directory fsync nur auf Plattformen, wo das sauber unterstützt wird
        if os.name != "nt":
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

    finally:
        try:
            os.remove(tmp)
        except FileNotFoundError:
            pass



def ensure_file_exists(path: Path = file_path) -> None:
    if not path.exists():
        empty_data = Main()
        text = json.dumps(empty_data.model_dump(mode="json"), indent=2, ensure_ascii=False)
        atomic_write_text(path, text)


def load_file(path: Path = file_path) -> Main:
    ensure_file_exists(path)

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return Main()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return Main()

    return Main.model_validate(data)


def save_file(data: Main, path: Path = file_path) -> None:
    text = json.dumps(data.model_dump(mode="json"), indent=2, ensure_ascii=False)
    atomic_write_text(path, text)


def load_and_migrate(path: Path = file_path) -> Main:
    ensure_file_exists(path)

    before = path.read_text(encoding="utf-8")
    model = load_file(path)
    after = json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False)

    if before.strip() != after.strip():
        atomic_write_text(path, after)

    return model

def add_user(userdata):
    data = load_file()
    data.userdata.append(
        Userdata(
            user_id=userdata["user_id"],
            username=userdata["username"],
            password_hash=userdata["password"],
            salt=userdata["salt"],
            rank=userdata["rank"]
        )
    )
    save_file(data)
    return

def add_backup_process(data):
    file = load_file()
    file.backup_paths.append(
        Backuppaths(
            backup_id=data["backup_id"],
            folder_to_backup=data["folder_to_backup"],
            folder_to_save_backup=data["folder_to_save_backup"],
            name=data["name"],
            last_backup=data["last_backup"],
            backup_frequency=data["backup_frequency"],
            status_message=data["status_message"],
            status=data["status"],
            version_history_length=data["version_history_length"]
        )
    )
    return

def edit_backup_process(data, position):
    file = load_file()
    file.backup_paths[position](
        Backuppaths(
            backup_id=data["backup_id"],
            folder_to_backup=data["folder_to_backup"],
            folder_to_save_backup=data["folder_to_save_backup"],
            name=data["name"],
            last_backup=data["last_backup"],
            backup_frequency=data["backup_frequency"],
            status_message=data["status_message"],
            status=data["status"],
            version_history_length=data["version_history_length"]
        )
    )
    return