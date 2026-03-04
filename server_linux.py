# server.py - Flask API server using Neon DB
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import logging
import threading
import socket
import webbrowser

import db_linux

app = Flask(__name__)
CORS(app)

try:
    from allow_block_linux import block_device, allow_device
    print("✅ allow_block functions imported")
except ImportError as e:
    print(f"⚠️ Import warning: {e}")
    def block_device(vid, pid): return False
    def allow_device(vid, pid): return False


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")


@app.route("/devices", methods=["GET"])
def get_devices():
    all_devices = db_linux.get_all_devices_full()
    devices = []
    for d in all_devices:
        interface_count = d.get("interface_count", 1)
        all_serials     = d.get("all_serials", "") or ""
        serials         = [s for s in all_serials.split(",") if s]
        devices.append({
            "id":              str(d["id"]),
            "usb_vid":         d["usb_vid"],
            "usb_pid":         d["usb_pid"],
            "usb_serial":      f"Multiple ({interface_count} interfaces)" if interface_count > 1 else (serials[0] if serials else "Unknown"),
            "device_type":     d.get("device_type",  "unknown"),
            "threat_level":    d.get("threat_level", "unknown"),
            "interface_count": interface_count,
            "serials":         serials,
        })
    return jsonify(devices)


@app.route("/device/<path:device_id>/action", methods=["POST"])
def update_device(device_id):
    data   = request.get_json(force=True)
    action = data.get("action")

    device = db_linux.get_device_by_id(device_id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    vid = device["usb_vid"]
    pid = device["usb_pid"]
    interface_count = db_linux.count_interfaces(vid, pid)
    rows_affected   = 0

    SEP = "─" * 52
    print(f"\n{SEP}")
    print(f"  📊  Dashboard : {action.upper()}")
    print(f"       VID : {vid}   PID : {pid}")
    print(f"{SEP}")

    if action == "allow":
        rows_affected = db_linux.update_device_status(vid, pid, "whitelisted", "low")

        def _allow():
            try:
                allow_device(vid, pid)
                print(f"  ✅  ALLOW done  —  VID={vid} PID={pid}")
            except Exception as e:
                print(f"  ❌  ALLOW error : {e}")

        threading.Thread(target=_allow, daemon=True).start()

    elif action == "block":
        rows_affected = db_linux.update_device_status(vid, pid, "blocked", "high")

        def _block():
            try:
                block_device(vid, pid)
                print(f"  ✅  BLOCK done  —  VID={vid} PID={pid}")
            except Exception as e:
                print(f"  ❌  BLOCK error : {e}")

        threading.Thread(target=_block, daemon=True).start()

    elif action == "remove":
        rows_affected = db_linux.delete_device(vid, pid)
        print(f"  ✅  Removed {rows_affected} entries")

    else:
        return jsonify({"error": "Invalid action"}), 400

    return jsonify({
        "status":     "success",
        "vid":        vid,
        "pid":        pid,
        "interfaces": interface_count,
        "affected":   rows_affected,
        "message":    "Background operation started" if action in ["allow", "block"] else "Completed",
    })


# 🔹 NEW: Dynamic free port finder
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def start_server():
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.logger.setLevel(logging.ERROR)

    port = find_free_port()
    print(f"🚀 Server running at http://127.0.0.1:{port}")

    threading.Timer(
        1.5,
        lambda: webbrowser.open(f"http://127.0.0.1:{port}/")
    ).start()

    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    db_linux.initialize_database()
    print("🔧 Running on Linux")
    start_server()
