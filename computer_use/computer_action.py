#!/usr/bin/env python3
"""Computer Action Tool - cross-platform mouse/keyboard executor (Windows / Linux X11).

Mirrors the Anthropic computer_use action vocabulary so a future standalone app
can reuse this executor. Backends: Linux X11 -> xdotool ; Windows -> pyautogui.
Wayland is unsupported. Use --dry-run to print the planned action as JSON without
executing it.

Actions: move click double_click right_click middle_click triple_click
         drag type key scroll wait
"""
import argparse
import json
import os
import subprocess
import sys
import time


class ActionError(Exception):
    pass


def detect_backend(platform=None, env=None):
    """Return 'linux' or 'windows'. Raise ActionError on Wayland/unsupported."""
    platform = platform if platform is not None else sys.platform
    env = env if env is not None else os.environ
    if platform.startswith("win"):
        return "windows"
    if platform.startswith("linux"):
        session = env.get("XDG_SESSION_TYPE", "").lower()
        if env.get("WAYLAND_DISPLAY") or session == "wayland":
            raise ActionError("Wayland session detected; only X11 is supported.")
        if not env.get("DISPLAY"):
            raise ActionError("No DISPLAY set; an X11 session is required.")
        return "linux"
    raise ActionError(f"Unsupported platform: {platform}")


# --- argument helpers -------------------------------------------------------

def _require_xy(args):
    if args.get("x") is None or args.get("y") is None:
        raise ActionError("--x and --y are required for this action")
    return int(args["x"]), int(args["y"])


def _require_to_xy(args):
    if args.get("to_x") is None or args.get("to_y") is None:
        raise ActionError("--to-x and --to-y are required for drag")
    return int(args["to_x"]), int(args["to_y"])


def _require_text(args):
    if args.get("text") is None:
        raise ActionError("--text is required for type")
    return str(args["text"])


def _require_keys(args):
    if not args.get("keys"):
        raise ActionError("--keys is required for key")
    return str(args["keys"])


# --- action planning --------------------------------------------------------

def plan_action(action, args, backend):
    """Return an execution plan dict: {'backend','action','ops':[...]}.

    Linux op:   {'run': [cmd...]}  or  {'sleep': float}
    Windows op: {'call': fn, 'args': [...]}  or  {'sleep': float}
    """
    if backend == "linux":
        return _plan_linux(action, dict(args))
    if backend == "windows":
        return _plan_windows(action, dict(args))
    raise ActionError(f"Unknown backend: {backend}")


_LINUX_CLICK = {
    "click": ("1", 1),
    "double_click": ("1", 2),
    "triple_click": ("1", 3),
    "right_click": ("3", 1),
    "middle_click": ("2", 1),
}


def _plan_linux(action, args):
    if action == "move":
        x, y = _require_xy(args)
        ops = [{"run": ["xdotool", "mousemove", str(x), str(y)]}]
    elif action in _LINUX_CLICK:
        x, y = _require_xy(args)
        button, repeat = _LINUX_CLICK[action]
        cmd = ["xdotool", "mousemove", str(x), str(y), "click"]
        if repeat > 1:
            cmd += ["--repeat", str(repeat)]
        cmd.append(button)
        ops = [{"run": cmd}]
    elif action == "drag":
        x, y = _require_xy(args)
        tx, ty = _require_to_xy(args)
        ops = [{"run": ["xdotool", "mousemove", str(x), str(y), "mousedown", "1",
                        "mousemove", str(tx), str(ty), "mouseup", "1"]}]
    elif action == "type":
        ops = [{"run": ["xdotool", "type", "--clearmodifiers", "--", _require_text(args)]}]
    elif action == "key":
        ops = [{"run": ["xdotool", "key", _require_keys(args)]}]
    elif action == "scroll":
        x, y = _require_xy(args)
        direction = args.get("direction") or "down"
        amount = int(args.get("amount") or 3)
        button = "4" if direction == "up" else "5"
        ops = [{"run": ["xdotool", "mousemove", str(x), str(y),
                        "click", "--repeat", str(amount), button]}]
    elif action == "wait":
        ops = [{"sleep": float(args.get("duration") or 1.0)}]
    else:
        raise ActionError(f"Unknown action: {action}")
    return {"backend": "linux", "action": action, "ops": ops}


_WIN_CLICK = {
    "click": "click",
    "double_click": "doubleClick",
    "right_click": "rightClick",
    "middle_click": "middleClick",
    "triple_click": "tripleClick",
}


def _plan_windows(action, args):
    if action == "move":
        x, y = _require_xy(args)
        ops = [{"call": "moveTo", "args": [x, y]}]
    elif action in _WIN_CLICK:
        x, y = _require_xy(args)
        ops = [{"call": _WIN_CLICK[action], "args": [x, y]}]
    elif action == "drag":
        x, y = _require_xy(args)
        tx, ty = _require_to_xy(args)
        ops = [{"call": "moveTo", "args": [x, y]}, {"call": "dragTo", "args": [tx, ty]}]
    elif action == "type":
        ops = [{"call": "write", "args": [_require_text(args)]}]
    elif action == "key":
        ops = [{"call": "hotkey", "args": _require_keys(args).split("+")}]
    elif action == "scroll":
        x, y = _require_xy(args)
        direction = args.get("direction") or "down"
        amount = int(args.get("amount") or 3)
        clicks = amount if direction == "up" else -amount
        ops = [{"call": "moveTo", "args": [x, y]}, {"call": "scroll", "args": [clicks]}]
    elif action == "wait":
        ops = [{"sleep": float(args.get("duration") or 1.0)}]
    else:
        raise ActionError(f"Unknown action: {action}")
    return {"backend": "windows", "action": action, "ops": ops}


# --- execution --------------------------------------------------------------

def execute(plan):
    """Perform the plan's ops. Windows ops call pyautogui; Linux ops run xdotool."""
    pyautogui = None
    if plan["backend"] == "windows":
        import pyautogui as _pg
        pyautogui = _pg
    for op in plan["ops"]:
        if "run" in op:
            subprocess.run(op["run"], check=True)
        elif "sleep" in op:
            time.sleep(op["sleep"])
        elif "call" in op:
            getattr(pyautogui, op["call"])(*op["args"])


# --- CLI --------------------------------------------------------------------

_ACTIONS = ["move", "click", "double_click", "right_click", "middle_click",
            "triple_click", "drag", "type", "key", "scroll", "wait"]


def _coords(args):
    return {k: args[k] for k in ("x", "y", "to_x", "to_y") if args.get(k) is not None}


def main(argv=None):
    p = argparse.ArgumentParser(description="Cross-platform mouse/keyboard executor")
    p.add_argument("action", choices=_ACTIONS)
    p.add_argument("--x", type=int)
    p.add_argument("--y", type=int)
    p.add_argument("--to-x", dest="to_x", type=int)
    p.add_argument("--to-y", dest="to_y", type=int)
    p.add_argument("--text")
    p.add_argument("--keys")
    p.add_argument("--direction", choices=["up", "down"], default="down")
    p.add_argument("--amount", type=int)
    p.add_argument("--duration", type=float)
    p.add_argument("--dry-run", action="store_true",
                   help="print the planned action as JSON without executing")
    a = p.parse_args(argv)
    args = {"x": a.x, "y": a.y, "to_x": a.to_x, "to_y": a.to_y, "text": a.text,
            "keys": a.keys, "direction": a.direction, "amount": a.amount,
            "duration": a.duration}
    try:
        backend = detect_backend()
        plan = plan_action(a.action, args, backend)
        if a.dry_run:
            print(json.dumps({"ok": True, "dry_run": True, **plan}))
            return 0
        execute(plan)
        print(json.dumps({"ok": True, "action": a.action, "backend": backend,
                          "args": _coords(args)}))
        return 0
    except ActionError as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 2
    except subprocess.CalledProcessError as e:
        print(json.dumps({"ok": False, "error": f"backend command failed: {e}"}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
