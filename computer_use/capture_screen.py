#!/usr/bin/env python3
"""
Screen Capture Tool - Cross-platform (Windows/Linux)

Modes:
  list     - Enumerate visible top-level windows as JSON (Windows + Linux/X11)
  monitors - Enumerate monitors + virtual bounds as JSON (multi-monitor inspection)
  active   - Capture the currently focused window
  window   - Capture a specific window by id (--window-id): X11 hex 0x... / Windows hwnd (dec or hex)
  full     - Capture one monitor (--monitor N; see --mode monitors for valid N)
  region   - Capture a rectangle (--left --top --width --height)

Saves to {project}/experiments/capture/YYYYMMDD_HHMMSS_<label>.png
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import warnings
from datetime import datetime

# mss >=10 deprecates the mss.mss() factory but keeps it working; silence the noise
# so JSON/stdout stays clean for callers parsing this tool's output.
warnings.filterwarnings("ignore", message=r".*mss\.mss is deprecated.*")


SAVE_SUBDIR = os.path.join("experiments", "capture")


def get_save_path(project_dir, label):
    """Create capture directory and return timestamped file path."""
    out_dir = os.path.join(project_dir, SAVE_SUBDIR)
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", label).strip("_") or "capture"
    safe = safe[:60]
    return os.path.join(out_dir, f"{ts}_{safe}.png")


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _set_dpi_awareness():
    """Make the process per-monitor DPI aware on Windows.

    Without this, on displays scaled != 100% the OS virtualizes coordinates:
    GetWindowRect / mss would disagree (logical vs physical pixels) and window
    geometry on secondary monitors with different DPI would be wrong. No-op elsewhere.
    """
    if sys.platform != "win32":
        return
    import ctypes
    for attempt in (
        lambda: ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)),  # PER_MONITOR_AWARE_V2
        lambda: ctypes.windll.shcore.SetProcessDpiAwareness(2),                            # PER_MONITOR_AWARE
        lambda: ctypes.windll.user32.SetProcessDPIAware(),                                 # system-DPI (legacy)
    ):
        try:
            attempt()
            return
        except Exception:
            continue


# ---------------------------------------------------------------------------
# X11 window listing / geometry via xwininfo
# ---------------------------------------------------------------------------

_TREE_LINE_RE = re.compile(
    r'^\s*(0x[0-9a-fA-F]+)\s+"([^"]*)"[^\n]*?\s+'
    r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)\s+\+(-?\d+)\+(-?\d+)'
)


def list_windows_x11():
    """Return visible top-level windows.

    Each item: {id, title, x, y, w, h}
    """
    r = _run(["xwininfo", "-root", "-tree"])
    if r.returncode != 0:
        raise RuntimeError(f"xwininfo -root -tree failed: {r.stderr.strip()}")

    seen = set()
    windows = []
    for line in r.stdout.splitlines():
        m = _TREE_LINE_RE.match(line)
        if not m:
            continue
        wid, title, w, h, _rx, _ry, ax, ay = m.groups()
        w, h = int(w), int(h)
        ax, ay = int(ax), int(ay)
        if w < 50 or h < 50:
            continue  # skip tiny (docks, popups, tooltips)
        if not title.strip():
            continue  # skip untitled helpers
        if wid in seen:
            continue
        seen.add(wid)
        windows.append({
            "id": wid, "title": title,
            "x": ax, "y": ay, "w": w, "h": h,
        })
    return windows


def get_window_geometry_x11(wid):
    r = _run(["xwininfo", "-id", wid])
    if r.returncode != 0:
        raise RuntimeError(f"xwininfo -id {wid} failed: {r.stderr.strip()}")
    x = y = w = h = None
    title = ""
    for line in r.stdout.splitlines():
        s = line.strip()
        if s.startswith("xwininfo: Window id:"):
            m = re.search(r'"([^"]*)"', s)
            if m:
                title = m.group(1)
        elif s.startswith("Absolute upper-left X:"):
            x = int(s.split(":")[-1])
        elif s.startswith("Absolute upper-left Y:"):
            y = int(s.split(":")[-1])
        elif s.startswith("Width:"):
            w = int(s.split(":")[-1])
        elif s.startswith("Height:"):
            h = int(s.split(":")[-1])
    if None in (x, y, w, h):
        raise RuntimeError(f"incomplete geometry for {wid}")
    return {"id": wid, "title": title, "x": x, "y": y, "w": w, "h": h}


def get_active_window_id_x11():
    """Resolve the focused X11 window id. Prefer xdotool, fallback to xprop."""
    if shutil.which("xdotool"):
        r = _run(["xdotool", "getactivewindow"])
        if r.returncode == 0 and r.stdout.strip():
            try:
                wid_dec = int(r.stdout.strip())
                return f"0x{wid_dec:x}"
            except ValueError:
                pass
    r = _run(["xprop", "-root", "_NET_ACTIVE_WINDOW"])
    if r.returncode == 0:
        m = re.search(r"0x[0-9a-fA-F]+", r.stdout)
        if m:
            return m.group(0)
    raise RuntimeError(
        "cannot determine active window "
        "(install xdotool or ensure the WM advertises _NET_ACTIVE_WINDOW)"
    )


# ---------------------------------------------------------------------------
# Windows window listing / geometry via Win32 (ctypes + pygetwindow)
# ---------------------------------------------------------------------------

def _parse_window_id(s):
    """Parse a window id string. Windows hwnd may be decimal or 0x-hex."""
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def _win32_window_title(hwnd):
    import ctypes
    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value


def list_windows_win32():
    """Return visible top-level windows on Windows.

    Each item: {id, title, x, y, w, h}  (id = hwnd as decimal string)
    """
    import pygetwindow as gw
    seen = set()
    windows = []
    for win in gw.getAllWindows():
        try:
            hwnd = int(win._hWnd)
            title = win.title or ""
            x, y, w, h = int(win.left), int(win.top), int(win.width), int(win.height)
        except Exception:
            continue
        if not title.strip():
            continue                      # skip untitled helpers
        if getattr(win, "isMinimized", False) or x <= -30000 or y <= -30000:
            continue                      # minimized windows report bogus (-32000) geometry
        if w < 50 or h < 50:
            continue                      # skip tiny (docks, popups, tooltips)
        if hwnd in seen:
            continue
        seen.add(hwnd)
        windows.append({"id": str(hwnd), "title": title, "x": x, "y": y, "w": w, "h": h})
    return windows


def get_window_geometry_win32(hwnd):
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError(f"GetWindowRect failed for hwnd {hwnd}")
    return {
        "id": str(hwnd), "title": _win32_window_title(hwnd),
        "x": rect.left, "y": rect.top,
        "w": rect.right - rect.left, "h": rect.bottom - rect.top,
    }


def _activate_window_win32(hwnd):
    """Restore (if minimized) and bring the window to the foreground."""
    import time
    import ctypes
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)            # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)


# ---------------------------------------------------------------------------
# Cross-platform dispatchers
# ---------------------------------------------------------------------------

def list_windows():
    return list_windows_win32() if sys.platform == "win32" else list_windows_x11()


# ---------------------------------------------------------------------------
# Capture primitives — prefer PIL, fall back to mss
# ---------------------------------------------------------------------------

def _grab_bbox(left, top, width, height, out_path):
    """Capture absolute-coordinate rectangle to PNG (multi-monitor aware)."""
    try:
        from PIL import ImageGrab
        # all_screens=True makes bbox span the whole virtual desktop so windows on
        # secondary monitors (or negative coords) are captured instead of black.
        kwargs = {"all_screens": True} if sys.platform == "win32" else {}
        im = ImageGrab.grab(bbox=(left, top, left + width, top + height), **kwargs)
        im.save(out_path, "PNG")
        return out_path
    except Exception:
        pass
    import mss
    import mss.tools
    with mss.mss() as sct:
        shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
        mss.tools.to_png(shot.rgb, shot.size, output=out_path)
    return out_path


def list_monitors():
    """Enumerate monitors (multi-monitor inspection).

    monitor_arg is the value to pass to `--monitor` for --mode full.
    Also returns the virtual bounding box spanning all monitors.
    """
    import mss
    with mss.mss() as sct:
        mons = sct.monitors  # [0] = virtual union, [1..] = physical monitors
        virtual = mons[0]
        result = {
            "count": len(mons) - 1,
            "virtual": {"left": virtual["left"], "top": virtual["top"],
                        "width": virtual["width"], "height": virtual["height"]},
            "monitors": [],
        }
        for i in range(1, len(mons)):
            m = mons[i]
            result["monitors"].append({
                "monitor_arg": i - 1,  # --monitor value
                "left": m["left"], "top": m["top"],
                "width": m["width"], "height": m["height"],
                "primary": (m["left"] == 0 and m["top"] == 0),
            })
    return result


def capture_full_screen(out_path, monitor_index=0):
    import mss
    import mss.tools
    with mss.mss() as sct:
        count = len(sct.monitors) - 1  # physical monitors
        idx = monitor_index + 1
        if idx < 1 or idx >= len(sct.monitors):
            raise RuntimeError(
                f"--monitor {monitor_index} out of range; available 0..{count - 1} "
                f"({count} monitor(s)). Use --mode monitors to list."
            )
        shot = sct.grab(sct.monitors[idx])
        mss.tools.to_png(shot.rgb, shot.size, output=out_path)
    return out_path


def capture_region(out_path, left, top, width, height):
    return _grab_bbox(left, top, width, height, out_path)


def capture_active_window(out_path):
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return _grab_bbox(
            rect.left, rect.top,
            rect.right - rect.left, rect.bottom - rect.top,
            out_path,
        )
    wid = get_active_window_id_x11()
    g = get_window_geometry_x11(wid)
    return _grab_bbox(g["x"], g["y"], g["w"], g["h"], out_path)


def _activate_window(wid):
    """Raise and focus the window so it is not occluded before capture."""
    import time
    if shutil.which("xdotool"):
        _run(["xdotool", "windowactivate", "--sync", wid])
        time.sleep(1.0)


def capture_window_by_id(out_path, wid):
    if sys.platform == "win32":
        hwnd = _parse_window_id(wid)
        _activate_window_win32(hwnd)
        g = get_window_geometry_win32(hwnd)
    else:
        _activate_window(wid)
        g = get_window_geometry_x11(wid)
    return _grab_bbox(g["x"], g["y"], g["w"], g["h"], out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    # Per-monitor DPI awareness so capture geometry matches physical pixels on scaled displays.
    _set_dpi_awareness()
    # Ensure non-ASCII window titles (e.g. Korean) print correctly regardless of console codepage.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    p = argparse.ArgumentParser(description="Screen Capture Tool")
    p.add_argument("--project", help="Project root directory (required for capture modes)")
    p.add_argument(
        "--mode",
        choices=["full", "active", "region", "window", "list", "monitors"],
        default="active",
        help="Capture mode",
    )
    p.add_argument("--monitor", type=int, default=0, help="Monitor index for --mode full")
    p.add_argument("--left", type=int, default=0)
    p.add_argument("--top", type=int, default=0)
    p.add_argument("--width", type=int, default=800)
    p.add_argument("--height", type=int, default=600)
    p.add_argument("--window-id", dest="window_id",
                   help="Window id for --mode window: X11 hex (0x2800008) or Windows hwnd (decimal/hex)")
    p.add_argument("--label", default="capture",
                   help="Filename label suffix (e.g. firefox, vscode)")

    args = p.parse_args()

    if args.mode == "list":
        windows = list_windows()
        print(json.dumps(windows, ensure_ascii=False, indent=2))
        return

    if args.mode == "monitors":
        print(json.dumps(list_monitors(), ensure_ascii=False, indent=2))
        return

    if not args.project:
        print("--project is required for capture modes", file=sys.stderr)
        sys.exit(2)

    save_path = get_save_path(args.project, args.label)

    if args.mode == "full":
        capture_full_screen(save_path, args.monitor)
    elif args.mode == "active":
        capture_active_window(save_path)
    elif args.mode == "region":
        capture_region(save_path, args.left, args.top, args.width, args.height)
    elif args.mode == "window":
        if not args.window_id:
            print("--window-id is required for --mode window", file=sys.stderr)
            sys.exit(2)
        capture_window_by_id(save_path, args.window_id)

    print(save_path)


if __name__ == "__main__":
    main()
