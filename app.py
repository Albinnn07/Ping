import os
import socket
import threading
import time
from flask import Flask

app = Flask(__name__)

MC_HOST = os.getenv("MC_HOST", "sg-sgp13.tryaltare.ai")
MC_PORT = int(os.getenv("MC_PORT", "25207"))
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "60"))

last_status = "Starting..."


def ping_server():
    global last_status
    while True:
        try:
            with socket.create_connection((MC_HOST, MC_PORT), timeout=5):
                last_status = f"Reachable ({MC_HOST}:{MC_PORT})"
        except Exception as e:
            last_status = f"Unreachable / Hibernating ({e})"
        time.sleep(PING_INTERVAL)


@app.route("/")
def home():
    return f"Auto Pinger Running | Status: {last_status}\n"


if __name__ == "__main__":
    t = threading.Thread(target=ping_server, daemon=True)
    t.start()
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
  
