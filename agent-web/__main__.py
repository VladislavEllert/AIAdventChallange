import sys
import webbrowser
import threading

import uvicorn


def main():
    host = "127.0.0.1"
    port = 8765

    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://{host}:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "agent_web.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
