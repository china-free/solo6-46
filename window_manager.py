import ctypes
import win32gui
import win32con
import win32process
import psutil


def _is_alt_tab_window(hwnd):
    if not win32gui.IsWindowVisible(hwnd):
        return False
    if win32gui.GetParent(hwnd) != 0:
        return False
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    if not (style & win32con.WS_VISIBLE):
        return False
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    if ex_style & win32con.WS_EX_TOOLWINDOW:
        return False
    if ex_style & win32con.WS_EX_APPWINDOW:
        return True
    has_owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER) != 0
    if has_owner:
        return False
    return True


def _get_process_name(hwnd):
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return proc.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied, win32gui.error):
        return ""


def _is_cloaked(hwnd):
    try:
        cloaked = ctypes.c_int(0)
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
        )
        return cloaked.value != 0
    except Exception:
        return False


def enumerate_windows():
    windows = []

    def _callback(hwnd, _):
        if not _is_alt_tab_window(hwnd):
            return True
        if _is_cloaked(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        proc_name = _get_process_name(hwnd)
        if proc_name in ("searchhost.exe", "shellexperiencehost.exe",
                         "startmenuexperiencehost.exe", "applicationframehost.exe"):
            return True
        try:
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            placement = win32gui.GetWindowPlacement(hwnd)
            show_cmd = placement[1]
            windows.append({
                "hwnd": hwnd,
                "title": title,
                "process_name": proc_name,
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "width": right - left,
                "height": bottom - top,
                "show_cmd": show_cmd,
            })
        except win32gui.error:
            pass
        return True

    win32gui.EnumWindows(_callback, None)
    return windows


def get_window_info(hwnd):
    try:
        title = win32gui.GetWindowText(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        placement = win32gui.GetWindowPlacement(hwnd)
        show_cmd = placement[1]
        proc_name = _get_process_name(hwnd)
        return {
            "hwnd": hwnd,
            "title": title,
            "process_name": proc_name,
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": right - left,
            "height": bottom - top,
            "show_cmd": show_cmd,
        }
    except win32gui.error:
        return None


def is_window_alive(hwnd):
    try:
        return win32gui.IsWindow(hwnd) != 0 and win32gui.IsWindowVisible(hwnd)
    except win32gui.error:
        return False


def set_window_position(hwnd, left, top, width, height, show_cmd=None):
    try:
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            left, top, width, height,
            win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED
        )
        if show_cmd is not None:
            win32gui.ShowWindow(hwnd, show_cmd)
        return True
    except win32gui.error:
        return False


def capture_layout():
    windows = enumerate_windows()
    layout_windows = []
    for w in windows:
        layout_windows.append({
            "hwnd": w["hwnd"],
            "title": w["title"],
            "process_name": w["process_name"],
            "left": w["left"],
            "top": w["top"],
            "width": w["width"],
            "height": w["height"],
            "show_cmd": w["show_cmd"],
        })
    return layout_windows


def restore_layout(layout_windows):
    restored = 0
    skipped = 0
    for entry in layout_windows:
        hwnd = entry["hwnd"]
        if not is_window_alive(hwnd):
            skipped += 1
            continue
        current_title = win32gui.GetWindowText(hwnd)
        if not current_title and not entry.get("title"):
            skipped += 1
            continue
        ok = set_window_position(
            hwnd,
            entry["left"],
            entry["top"],
            entry["width"],
            entry["height"],
            entry.get("show_cmd"),
        )
        if ok:
            restored += 1
        else:
            skipped += 1
    return restored, skipped
