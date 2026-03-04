import time
import threading
import webbrowser
import os
import sys

from usbmonitor import USBMonitor
from usbmonitor.attributes import ID_MODEL_ID, ID_VENDOR_ID, ID_SERIAL

import db
import server
from ml import USBRubberDuckyDetector, capture_5_seconds
from allow_block import block_device, allow_device, find_devcon
from usb_verification_handler import verify_device_with_captcha

# ── Startup ───────────────────────────────────────────────────────────────────
db.initialize_database()

ml_detector = USBRubberDuckyDetector()
if not ml_detector.load_model():
    print("  ⚙  Training ML model..."); ml_detector.train_model()
else:
    print("  ✅  ML model loaded")

devcon_path = find_devcon()
print(f"  ✅  DevCon : {devcon_path}" if devcon_path else "  ⚠   DevCon : not found — physical blocking disabled")

SEP = "─" * 52

# ── Helpers ───────────────────────────────────────────────────────────────────
def normalize_serial(s):
    return s.split("&")[0] if s else "NoSerial"

def is_valid_hex_id(v):
    return bool(v) and len(v) == 4 and all(c in "0123456789ABCDEFabcdef" for c in v)

def device_key_for(vid, pid, serial):
    return serial if serial != "NoSerial" else f"{vid}:{pid}"

# ── Core Logic ────────────────────────────────────────────────────────────────
def check_or_insert_device(vid, pid, serial):
    device = db.get_device_by_vid_pid(vid, pid)

    if device:
        device_type = device["device_type"]
        existing    = device["usb_serial"] or ""
        serials = set(existing.split(",")) if existing else set()
        serials.add(serial)
        db.update_device_serial(device["id"], ",".join(serials))

        print(f"  ℹ   Status : {device_type.upper()}")

        if device_type == "blocked":
            print(f"  🔒  Re-enforcing block before analysis...")
            if devcon_path:
                block_device(vid, pid, devcon_path)
    else:
        db.insert_device(vid, pid, serial)
        print(f"  🆕  Status : NEW DEVICE")

    analyze_device_with_ml(vid, pid)

# ── ML + CAPTCHA ──────────────────────────────────────────────────────────────
def analyze_device_with_ml(vid, pid):
    print(f"\n  🤖  ML Analysis")
    print(f"  {'·'*48}")
    print(f"       Capturing keystrokes for 5 seconds...")

    keystrokes = capture_5_seconds()
    features   = ml_detector.extract_features(keystrokes)

    if not features:
        print(f"       Result   : Non-HID / no keystrokes")
    else:
        result, confidence, reasons = ml_detector.predict(features)
        total_keys = features.get("total_keys_5sec", 0)
        speed      = features.get("avg_speed", 0.0)
        print(f"       Result   : {result}")
        print(f"       Confidence : {confidence:.0f}%")
        print(f"       Keys (5s)  : {total_keys}   Speed: {speed:.1f} k/s")
        if reasons:
            print(f"       ⚠  Threats : {', '.join(reasons)}")

    print(f"\n  🔐  CAPTCHA Verification")
    print(f"  {'·'*48}")
    user_verified = verify_device_with_captcha(vid, pid, timeout=10)

    print()
    if user_verified:
        print(f"  ✅  ALLOWED  —  VID={vid}  PID={pid}")
        db.update_device_status(vid, pid, "whitelisted", "low")
        if devcon_path:
            allow_device(vid, pid, devcon_path)
    else:
        print(f"  🚫  BLOCKED  —  VID={vid}  PID={pid}")
        db.update_device_status(vid, pid, "blocked", "high")
        if devcon_path:
            block_device(vid, pid, devcon_path)

# ── Monitor Loop ──────────────────────────────────────────────────────────────
def usb_monitor_loop():
    print(f"\n{SEP}")
    print(f"  🔄  USB Monitoring Active")
    print(f"{SEP}\n")

    monitor = USBMonitor()
    currently_connected: set = set()
    processed_devices:   set = set()

    while True:
        _, added = monitor.changes_from_last_check(update_last_check_devices=True)

        connected_now: set = set()
        for info in monitor.get_available_devices().values():
            vid    = info.get(ID_VENDOR_ID)
            pid    = info.get(ID_MODEL_ID)
            serial = normalize_serial(info.get(ID_SERIAL))
            if is_valid_hex_id(vid) and is_valid_hex_id(pid):
                connected_now.add(device_key_for(vid, pid, serial))

        for key in currently_connected - connected_now:
            processed_devices.discard(key)
            print(f"\n  🔌  Unplugged : {key}  (will re-verify on next plug-in)\n")

        currently_connected = connected_now

        for info in added.values():
            vid    = info.get(ID_VENDOR_ID)
            pid    = info.get(ID_MODEL_ID)
            serial = normalize_serial(info.get(ID_SERIAL))

            if not (is_valid_hex_id(vid) and is_valid_hex_id(pid)):
                continue

            key = device_key_for(vid, pid, serial)
            if key in processed_devices:
                continue

            processed_devices.add(key)

            print(f"\n{SEP}")
            print(f"  📱  Device Detected")
            print(f"       VID    : {vid}")
            print(f"       PID    : {pid}")
            print(f"       Serial : {serial}")
            print(f"{SEP}")

            try:
                check_or_insert_device(vid, pid, serial)
                print(f"\n{SEP}")
                print(f"  ✅  Processing complete  —  resuming monitor...")
                print(f"{SEP}\n")
            except Exception as e:
                processed_devices.discard(key)
                print(f"\n  ⚠   Error : {e}  —  resuming...\n")

        time.sleep(1)

# ── Dashboard ─────────────────────────────────────────────────────────────────
def start_dashboard():
    threading.Thread(target=server.start_server, daemon=True).start()
    time.sleep(1)
    print(f"  🌐  Dashboard : http://localhost:8000\n")
    webbrowser.open("http://localhost:8000/")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{SEP}")
    print(f"  🛡   USB Rubber Ducky Intrusion Detection System")
    print(f"{SEP}")
    start_dashboard()
    try:
        usb_monitor_loop()
    except KeyboardInterrupt:
        print(f"\n  ⏹   Stopped\n")
        sys.exit(0)