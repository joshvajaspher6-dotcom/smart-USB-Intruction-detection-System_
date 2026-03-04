# server.py - Flask API server using Firebase Firestore
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import logging
import shutil
import threading
import pythoncom  # needed for WMI in background threads

import db

app = Flask(__name__)
CORS(app)

def find_devcon():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(script_dir, "devcon.exe")
    if os.path.isfile(local_path):
        return local_path
    return shutil.which("devcon.exe") or shutil.which("devcon")

try:
    from allow_block import block_device, allow_device
    print("✅ allow_block functions imported")
except ImportError as e:
    print(f"⚠️ Import warning: {e}")
    def block_device(vid, pid, devcon_path=None): return False
    def allow_device(vid, pid, devcon_path=None): return False

devcon_path = find_devcon()


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")


@app.route("/devices", methods=["GET"])
def get_devices():
    all_devices = db.get_all_devices_full()
    devices = []
    for d in all_devices:
        interface_count = d.get("interface_count", 1)
        all_serials     = d.get("all_serials", "") or ""
        serials         = [s for s in all_serials.split(",") if s]
        devices.append({
            "id":              str(d["id"]),   # ← string ID for Firebase
            "usb_vid":         d["usb_vid"],
            "usb_pid":         d["usb_pid"],
            "usb_serial":      f"Multiple ({interface_count} interfaces)" if interface_count > 1 else (serials[0] if serials else "Unknown"),
            "device_type":     d.get("device_type",  "unknown"),
            "threat_level":    d.get("threat_level", "unknown"),
            "interface_count": interface_count,
            "serials":         serials,
        })
    return jsonify(devices)


# ← path:device_id allows slashes and strings (Firebase doc IDs)
@app.route("/device/<path:device_id>/action", methods=["POST"])
def update_device(device_id):
    data   = request.get_json(force=True)
    action = data.get("action")

    device = db.get_device_by_id(device_id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    vid = device["usb_vid"]
    pid = device["usb_pid"]
    interface_count = db.count_interfaces(vid, pid)
    rows_affected   = 0

    SEP = "─" * 52
    print(f"\n{SEP}")
    print(f"  📊  Dashboard : {action.upper()}")
    print(f"       VID : {vid}   PID : {pid}")
    print(f"{SEP}")

    if action == "allow":
        rows_affected = db.update_device_status(vid, pid, "whitelisted", "low")

        def _allow():
            pythoncom.CoInitialize()
            try:
                allow_device(vid, pid, devcon_path)
                print(f"  ✅  ALLOW done  —  VID={vid} PID={pid}")
            except Exception as e:
                print(f"  ❌  ALLOW error : {e}")
            finally:
                pythoncom.CoUninitialize()

        threading.Thread(target=_allow, daemon=True).start()

    elif action == "block":
        rows_affected = db.update_device_status(vid, pid, "blocked", "high")

        def _block():
            pythoncom.CoInitialize()
            try:
                block_device(vid, pid, devcon_path)
                print(f"  ✅  BLOCK done  —  VID={vid} PID={pid}")
            except Exception as e:
                print(f"  ❌  BLOCK error : {e}")
            finally:
                pythoncom.CoUninitialize()

        threading.Thread(target=_block, daemon=True).start()

    elif action == "remove":
        rows_affected = db.delete_device(vid, pid)
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


def start_server():
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.logger.setLevel(logging.ERROR)
    app.run(port=8000, debug=False)


if __name__ == "__main__":
    db.initialize_database()
    print(f"🔧 DevCon: {devcon_path or 'Not found'}")
    start_server()
