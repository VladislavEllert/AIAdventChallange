import os
import sys
import webbrowser
import threading

import uvicorn


def main():
    host = os.getenv("AGENT_WEB_HOST", "0.0.0.0")
    port = int(os.getenv("AGENT_WEB_PORT", "8765"))
    # Reload defaults off: this is meant to run as a standing service (day 30),
    # not just a dev convenience — `uvicorn ... --reload` directly is still the
    # right tool while actively developing.
    reload = os.getenv("AGENT_WEB_RELOAD", "0") == "1"
    open_browser = os.getenv("AGENT_WEB_OPEN_BROWSER", "1") == "1"

    if open_browser:
        def _open():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(
        "agent_web.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
