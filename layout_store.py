import json
import os
from datetime import datetime


LAYOUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "layouts")
LAYOUTS_FILE = os.path.join(LAYOUTS_DIR, "layouts.json")


def _ensure_dir():
    os.makedirs(LAYOUTS_DIR, exist_ok=True)


def _load_all():
    _ensure_dir()
    if not os.path.exists(LAYOUTS_FILE):
        return []
    try:
        with open(LAYOUTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_all(layouts):
    _ensure_dir()
    with open(LAYOUTS_FILE, "w", encoding="utf-8") as f:
        json.dump(layouts, f, ensure_ascii=False, indent=2)


def list_layouts():
    layouts = _load_all()
    return [
        {
            "name": l["name"],
            "created_at": l.get("created_at", ""),
            "updated_at": l.get("updated_at", ""),
            "window_count": len(l.get("windows", [])),
            "hotkey": l.get("hotkey", ""),
        }
        for l in layouts
    ]


def get_layout(name):
    layouts = _load_all()
    for l in layouts:
        if l["name"] == name:
            return l
    return None


def save_layout(name, windows, monitors=None, hotkey=""):
    layouts = _load_all()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = None
    for i, l in enumerate(layouts):
        if l["name"] == name:
            existing = i
            break

    entry = {
        "name": name,
        "created_at": layouts[existing]["created_at"] if existing is not None else now,
        "updated_at": now,
        "windows": windows,
        "monitors": monitors or [],
        "hotkey": hotkey,
    }

    if existing is not None:
        layouts[existing] = entry
    else:
        layouts.append(entry)

    _save_all(layouts)
    return entry


def delete_layout(name):
    layouts = _load_all()
    layouts = [l for l in layouts if l["name"] != name]
    _save_all(layouts)


def rename_layout(old_name, new_name):
    layouts = _load_all()
    for l in layouts:
        if l["name"] == old_name:
            l["name"] = new_name
            break
    _save_all(layouts)


def update_hotkey(name, hotkey):
    layouts = _load_all()
    for l in layouts:
        if l["name"] == name:
            l["hotkey"] = hotkey
            break
    _save_all(layouts)


def get_hotkey_map():
    layouts = _load_all()
    return {l["name"]: l["hotkey"] for l in layouts if l.get("hotkey")}
