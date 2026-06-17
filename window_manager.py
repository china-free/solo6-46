import ctypes
import win32gui
import win32con
import win32process
import win32api
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


def get_current_monitors():
    monitors = []
    results = win32api.EnumDisplayMonitors()
    for i, (hmon, hdc, rect) in enumerate(results):
        left, top, right, bottom = rect
        monitors.append({
            "index": i,
            "handle": hmon,
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": right - left,
            "height": bottom - top,
            "is_primary": (left == 0 and top == 0),
        })
    return monitors


def find_monitor_for_window(left, top, monitors):
    for m in monitors:
        if m["left"] <= left < m["right"] and m["top"] <= top < m["bottom"]:
            return m
    if monitors:
        best = None
        best_overlap = -1
        for m in monitors:
            overlap_left = max(left, m["left"])
            overlap_top = max(top, m["top"])
            overlap_right = min(left + 1, m["right"])
            overlap_bottom = min(top + 1, m["bottom"])
            if overlap_right > overlap_left and overlap_bottom > overlap_top:
                area = (overlap_right - overlap_left) * (overlap_bottom - overlap_top)
                if area > best_overlap:
                    best_overlap = area
                    best = m
        if best:
            return best
    for m in monitors:
        if m["is_primary"]:
            return m
    return monitors[0] if monitors else None


def compute_relative_position(window_rect, monitor_rect):
    w_left, w_top, w_right, w_bottom = window_rect
    m_left, m_top, m_right, m_bottom = monitor_rect
    m_width = m_right - m_left
    m_height = m_bottom - m_top

    rel_left = (w_left - m_left) / m_width if m_width > 0 else 0
    rel_top = (w_top - m_top) / m_height if m_height > 0 else 0
    rel_right = (w_right - m_left) / m_width if m_width > 0 else 0
    rel_bottom = (w_bottom - m_top) / m_height if m_height > 0 else 0

    abs_width = w_right - w_left
    abs_height = w_bottom - w_top
    rel_width = abs_width / m_width if m_width > 0 else 0
    rel_height = abs_height / m_height if m_height > 0 else 0

    return {
        "rel_left": rel_left,
        "rel_top": rel_top,
        "rel_right": rel_right,
        "rel_bottom": rel_bottom,
        "rel_width": rel_width,
        "rel_height": rel_height,
        "abs_width": abs_width,
        "abs_height": abs_height,
    }


def compute_absolute_position(rel_pos, target_monitor_rect, strategy="proportional"):
    m_left, m_top, m_right, m_bottom = target_monitor_rect
    m_width = m_right - m_left
    m_height = m_bottom - m_top

    if strategy == "proportional":
        width = int(rel_pos["rel_width"] * m_width)
        height = int(rel_pos["rel_height"] * m_height)
        left = m_left + int(rel_pos["rel_left"] * m_width)
        top = m_top + int(rel_pos["rel_top"] * m_height)
    elif strategy == "fixed_size":
        width = rel_pos["abs_width"]
        height = rel_pos["abs_height"]
        left = m_left + int(rel_pos["rel_left"] * m_width)
        top = m_top + int(rel_pos["rel_top"] * m_height)
    else:
        width = min(rel_pos["abs_width"], int(rel_pos["rel_width"] * m_width))
        height = min(rel_pos["abs_height"], int(rel_pos["rel_height"] * m_height))
        left = m_left + int(rel_pos["rel_left"] * m_width)
        top = m_top + int(rel_pos["rel_top"] * m_height)

    width = max(100, min(width, m_width - 50))
    height = max(100, min(height, m_height - 50))
    left = max(m_left, min(left, m_right - width))
    top = max(m_top, min(top, m_bottom - height))

    return left, top, width, height


def match_monitor(saved_monitor, current_monitors, strategy="smart"):
    if not current_monitors:
        return None, "no_monitors"

    if strategy == "smart":
        if saved_monitor.get("is_primary"):
            for m in current_monitors:
                if m["is_primary"]:
                    if m["width"] == saved_monitor["width"] and m["height"] == saved_monitor["height"]:
                        return m, "primary_exact"
                    return m, "primary_matched"

        saved_idx = saved_monitor.get("index", -1)
        if 0 <= saved_idx < len(current_monitors):
            candidate = current_monitors[saved_idx]
            if candidate["width"] == saved_monitor["width"] and candidate["height"] == saved_monitor["height"]:
                return candidate, "index_exact"
            if candidate["is_primary"] == saved_monitor.get("is_primary", False):
                return candidate, "index_matched"

        for m in current_monitors:
            if m["width"] == saved_monitor["width"] and m["height"] == saved_monitor["height"]:
                if saved_monitor.get("is_primary") == m["is_primary"]:
                    return m, "resolution_exact_primary"
                return m, "resolution_exact"

        for m in current_monitors:
            if saved_monitor.get("is_primary") == m["is_primary"]:
                return m, "primary_fallback"

        if saved_idx >= 0 and saved_idx < len(current_monitors):
            return current_monitors[saved_idx], "index_fallback"

        for m in current_monitors:
            if m["is_primary"]:
                return m, "primary_default"

        return current_monitors[0], "first_default"

    return match_monitor(saved_monitor, current_monitors, strategy="smart")


def capture_layout():
    windows = enumerate_windows()
    monitors = get_current_monitors()

    layout_windows = []
    for w in windows:
        monitor = find_monitor_for_window(w["left"], w["top"], monitors)
        if monitor is None:
            continue

        rel_pos = compute_relative_position(
            (w["left"], w["top"], w["right"], w["bottom"]),
            (monitor["left"], monitor["top"], monitor["right"], monitor["bottom"])
        )

        layout_windows.append({
            "hwnd": w["hwnd"],
            "title": w["title"],
            "process_name": w["process_name"],
            "left": w["left"],
            "top": w["top"],
            "width": w["width"],
            "height": w["height"],
            "show_cmd": w["show_cmd"],
            "monitor": {
                "index": monitor["index"],
                "left": monitor["left"],
                "top": monitor["top"],
                "width": monitor["width"],
                "height": monitor["height"],
                "is_primary": monitor["is_primary"],
            },
            "relative_position": rel_pos,
        })

    monitor_snapshot = []
    for m in monitors:
        monitor_snapshot.append({
            "index": m["index"],
            "left": m["left"],
            "top": m["top"],
            "width": m["width"],
            "height": m["height"],
            "is_primary": m["is_primary"],
        })

    return layout_windows, monitor_snapshot


def restore_layout(layout_windows, saved_monitors=None, resize_strategy="balanced"):
    current_monitors = get_current_monitors()
    restored = 0
    skipped = 0
    remapped = 0
    match_reasons = {}

    for entry in layout_windows:
        hwnd = entry["hwnd"]
        if not is_window_alive(hwnd):
            skipped += 1
            continue

        current_title = win32gui.GetWindowText(hwnd)
        if not current_title and not entry.get("title"):
            skipped += 1
            continue

        abs_left = entry.get("left")
        abs_top = entry.get("top")
        width = entry.get("width")
        height = entry.get("height")
        show_cmd = entry.get("show_cmd")

        rel_pos = entry.get("relative_position")
        saved_monitor = entry.get("monitor")

        if rel_pos and saved_monitor and current_monitors:
            target_monitor, reason = match_monitor(saved_monitor, current_monitors)
            if target_monitor:
                match_reasons[reason] = match_reasons.get(reason, 0) + 1
                if not (saved_monitor.get("index") == target_monitor["index"]
                        and saved_monitor.get("width") == target_monitor["width"]
                        and saved_monitor.get("height") == target_monitor["height"]
                        and saved_monitor.get("left") == target_monitor["left"]
                        and saved_monitor.get("top") == target_monitor["top"]):
                    remapped += 1

                target_rect = (
                    target_monitor["left"],
                    target_monitor["top"],
                    target_monitor["right"],
                    target_monitor["bottom"],
                )
                abs_left, abs_top, width, height = compute_absolute_position(
                    rel_pos, target_rect, strategy=resize_strategy
                )
        else:
            if current_monitors and abs_left is not None and abs_top is not None:
                target_monitor = find_monitor_for_window(abs_left, abs_top, current_monitors)
                if target_monitor and not (
                    target_monitor["left"] <= abs_left < target_monitor["right"]
                    and target_monitor["top"] <= abs_top < target_monitor["bottom"]
                ):
                    abs_left = target_monitor["left"] + 50
                    abs_top = target_monitor["top"] + 50
                    match_reasons["legacy_clamped"] = match_reasons.get("legacy_clamped", 0) + 1

        ok = set_window_position(hwnd, abs_left, abs_top, width, height, show_cmd)
        if ok:
            restored += 1
        else:
            skipped += 1

    return {
        "restored": restored,
        "skipped": skipped,
        "remapped": remapped,
        "match_reasons": match_reasons,
    }
