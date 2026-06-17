import win32api
import win32con


def get_monitors():
    monitors = []
    results = win32api.EnumDisplayMonitors()
    for hmon, hdc, rect in results:
        left, top, right, bottom = rect
        monitors.append({
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


def get_monitor_details():
    monitors = get_monitors()
    details = []
    for i, m in enumerate(monitors):
        detail = {
            "index": i,
            "name": f"显示器 {i + 1}",
            "left": m["left"],
            "top": m["top"],
            "right": m["right"],
            "bottom": m["bottom"],
            "width": m["width"],
            "height": m["height"],
            "resolution": f"{m['width']}x{m['height']}",
            "is_primary": m["is_primary"],
        }
        if m["is_primary"]:
            detail["name"] += " (主)"
        details.append(detail)
    return details
