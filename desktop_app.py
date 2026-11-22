import ctypes
import inspect
import json
import os
import socket
import sys
import threading
import time
import urllib.request

import uvicorn
import webview

WINDOW_TITLE = "FS-XML Interpreter"
HOST = "127.0.0.1"
PORT = 18420


def _ensure_project_cwd() -> str:
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    return root_dir


def _set_windows_app_id() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "doctorgth.fsxml.orchestrator.2"
            )
        except Exception:
            pass


def _apply_windows_icon(window, ico_path: str) -> None:
    if sys.platform != "win32" or not os.path.isfile(ico_path):
        return
    try:
        user32 = ctypes.windll.user32
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE = 0x0040
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        hwnd = None
        try:
            if getattr(window, "native", None) is not None:
                hwnd = int(window.native.Handle.ToInt64())
        except Exception:
            hwnd = None

        if not hwnd:
            hwnd = user32.FindWindowW(None, WINDOW_TITLE)

        if hwnd:
            hicon_big = user32.LoadImageW(
                None, ico_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
            )
            hicon_small = user32.LoadImageW(
                None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
            )
            if hicon_big:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
            if hicon_small:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
    except Exception:
        pass


def _redirect_null_streams() -> None:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _show_fatal_error(message: str) -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.MessageBoxW(None, message, f"{WINDOW_TITLE} — Ошибка", 0x10)
            return
        except Exception:
            pass
    print(f"[FATAL] {message}", file=sys.stderr)


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _is_our_server_running(health_url: str) -> bool:
    try:
        with urllib.request.urlopen(health_url, timeout=1.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("service") == "safe-ai-orchestrator"
    except Exception:
        pass
    return False


def _start_backend_server(error_holder: dict, stop_event: threading.Event) -> None:
    try:
        config = uvicorn.Config(
            "server.main:app",
            host=HOST,
            port=PORT,
            log_level="warning",
            reload=False,
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as exc:
        error_holder["error"] = str(exc)
        stop_event.set()


def _wait_for_server(url: str, stop_event: threading.Event, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if stop_event.is_set():
            return False
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def main() -> None:
    _redirect_null_streams()
    root_dir = _ensure_project_cwd()
    _set_windows_app_id()

    health_url = f"http://{HOST}:{PORT}/health"

    if _is_port_in_use(HOST, PORT):
        if not _is_our_server_running(health_url):
            _show_fatal_error(
                f"Порт {PORT} уже занят другим приложением.\n"
                "Закройте конфликтующую программу и перезапустите FS-XML Interpreter."
            )
            sys.exit(1)
    else:
        error_holder: dict = {}
        server_failed_event = threading.Event()
        server_thread = threading.Thread(
            target=_start_backend_server,
            args=(error_holder, server_failed_event),
            daemon=True,
        )
        server_thread.start()

        if not _wait_for_server(health_url, server_failed_event):
            details = error_holder.get("error") or "Сервер не ответил за отведённое время."
            _show_fatal_error(f"Не удалось запустить локальный сервер:\n{details}")
            sys.exit(1)

    dev_mode = "--dev" in sys.argv or os.environ.get("FS_XML_DEV") == "1"
    target_url = "http://127.0.0.1:18421/" if dev_mode else f"http://{HOST}:{PORT}/"

    ico_path = os.path.join(root_dir, "images", "FS-XML.ico")
    png_path = os.path.join(root_dir, "images", "FS-XML.png")
    icon_arg = ico_path if os.path.isfile(ico_path) else (png_path if os.path.isfile(png_path) else None)

    window = webview.create_window(
        title=WINDOW_TITLE,
        url=target_url,
        width=1360,
        height=860,
        min_size=(1024, 680),
        background_color="#020617",
    )

    def on_shown():
        if os.path.isfile(ico_path):
            _apply_windows_icon(window, ico_path)

    window.events.shown += on_shown

    start_kwargs = {}
    if icon_arg and "icon" in inspect.signature(webview.start).parameters:
        start_kwargs["icon"] = icon_arg

    webview.start(**start_kwargs)


if __name__ == "__main__":
    main()