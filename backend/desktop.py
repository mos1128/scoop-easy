import socket
import threading
import time

import uvicorn
import webview

from main import app

HOST = "127.0.0.1"
PREFERRED_PORT = 8000


def find_free_port(host: str, preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, preferred))
            return preferred
        except OSError:
            s.bind((host, 0))
            return s.getsockname()[1]


def wait_for_server(host: str, port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main():
    port = find_free_port(HOST, PREFERRED_PORT)
    config = uvicorn.Config(app, host=HOST, port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    if not wait_for_server(HOST, port):
        raise RuntimeError("Server failed to start")

    window = webview.create_window("Scoop Easy", f"http://{HOST}:{port}", width=1200, height=800)
    window.events.closed += lambda: setattr(server, "should_exit", True)
    webview.start()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"启动失败: {e}")
        input("按回车键退出...")
