import json
import os
import socket
import struct
import threading
import time
from flask import Flask

app = Flask(__name__)

MC_HOST = os.getenv("MC_HOST", "sg-sgp13.tryaltare.ai")
MC_PORT = int(os.getenv("MC_PORT", "25207"))
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "60"))
PROTOCOL_VERSION = int(os.getenv("PROTOCOL_VERSION", "767"))

last_status = "Starting..."


def write_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        temp = value & 0x7F
        value >>= 7
        if value != 0:
            out.append(temp | 0x80)
        else:
            out.append(temp)
            break
    return bytes(out)


def read_varint(sock: socket.socket) -> int:
    num_read = 0
    result = 0
    while True:
        raw = sock.recv(1)
        if not raw:
            raise ConnectionError("Connection closed while reading VarInt")
        byte = raw[0]
        result |= (byte & 0x7F) << (7 * num_read)
        num_read += 1
        if num_read > 5:
            raise ValueError("VarInt is too big")
        if (byte & 0x80) == 0:
            break
    return result


def make_packet(packet_id: int, data: bytes) -> bytes:
    body = write_varint(packet_id) + data
    return write_varint(len(body)) + body


def slp_status(host: str, port: int, protocol_version: int, timeout: float = 5.0) -> dict:
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)

        host_bytes = host.encode("utf-8")
        handshake_data = (
            write_varint(protocol_version)
            + write_varint(len(host_bytes))
            + host_bytes
            + struct.pack(">H", port)
            + write_varint(1)
        )
        sock.sendall(make_packet(0x00, handshake_data))
        sock.sendall(make_packet(0x00, b""))

        _packet_len = read_varint(sock)
        resp_id = read_varint(sock)
        if resp_id != 0x00:
            raise ValueError(f"Unexpected packet ID: {resp_id}")

        json_len = read_varint(sock)
        chunks = bytearray()
        while len(chunks) < json_len:
            chunk = sock.recv(json_len - len(chunks))
            if not chunk:
                raise ConnectionError("Incomplete JSON payload from server")
            chunks.extend(chunk)

        return json.loads(chunks.decode("utf-8"))


def ping_server():
    global last_status
    while True:
        try:
            info = slp_status(MC_HOST, MC_PORT, PROTOCOL_VERSION)
            version = info.get("version", {}).get("name", "Unknown")
            players = info.get("players", {})
            online = players.get("online", 0)
            max_p = players.get("max", 0)
            last_status = f"Online ({version}) | Players: {online}/{max_p}"
        except Exception as e:
            last_status = f"Offline / Hibernating ({e})"
        time.sleep(PING_INTERVAL)


@app.route("/")
def home():
    return f"SLP Pinger Running | Status: {last_status}\n"


if __name__ == "__main__":
    t = threading.Thread(target=ping_server, daemon=True)
    t.start()
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
    
