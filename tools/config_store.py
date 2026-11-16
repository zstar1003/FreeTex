"""Writable per-user settings, separate from immutable application resources."""
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import RLock

_LOCK = RLock()


def config_path():
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        if not root.is_absolute():
            root = Path.home() / ".config"
    return root / "FreeTex" / "config.json"


def legacy_config_path():
    root = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    return root / "config.json"


def _read(path):
    if path.is_symlink():
        raise OSError("Refusing a symbolic-link settings file")
    with path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError("Settings must contain a JSON object")
    return config


def _write(path, config, create_only=False):
    # New directories/files are private on POSIX. Existing directory permissions
    # are not changed; Windows retains the user's profile directory ACLs.
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise OSError("Refusing a symbolic-link settings file")
    fd, temporary = tempfile.mkstemp(prefix=".config-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(config, stream, ensure_ascii=False, indent=4)
            stream.flush()
            os.fsync(stream.fileno())
        if create_only:
            # Atomic no-clobber publication even if another instance migrated
            # or saved settings after our initial existence check.
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_config():
    with _LOCK:
        path = config_path()
        if path.exists() or path.is_symlink():
            return _read(path)
        # Migrate once, retaining the original. Never overwrite an existing user
        # config with bundled defaults, or fall back after a parse/write failure.
        config = _read(legacy_config_path())
        try:
            _write(path, config, create_only=True)
        except FileExistsError:
            return _read(path)
        return config


def update_config_section(section, values):
    with _LOCK:
        config = read_config()
        existing = config.get(section, {})
        if not isinstance(existing, dict):
            raise ValueError("Settings section must contain a JSON object")
        config[section] = {**existing, **values}
        _write(config_path(), config)
