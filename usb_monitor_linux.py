import time
import threading
import webbrowser
import os
import sys

try:
    import pyudev
except ImportError:
    print("  ⚠   pyudev not found. Install it with: pip install pyudev")
    sys.exit(1)

import db_linux
import server_linux
from ml_linux import USBRubberDuckyDetector, capture_5_seconds
from allow_block_linux import block_device, allow_device
from usb_verification_handler_linux import verify_device_with_captcha

CAPTCHA_TIMEOUT = 10

# ── Startup ───────────────────────────────────────────────────────────────────
db_linux.initialize_database()

ml_detector = USBRubberDuckyDetector()
if not ml_detector.load_model():
    print("  ⚙  Training ML model..."); ml_detector.train_model()
else:
    print("  ✅  ML model loaded")

SEP = "─" * 52

# Track which devices are currently being processed (thread-safe)
processing_lock = threading.Lock()
currently_processing: set = set()

# ── Helpers ───────────────────────────────────────────────────────────────────
def normalize_serial(s):
    return s.split("&")[0] if s else "NoSerial"

def is_valid_hex_id(v):
    return bool(v) and len(v) == 4 and all(c in "0123456789ABCDEFabcdef" for c in v)

def device_key_for(vid, pid, serial):
    return serial if serial != "NoSerial" else f"{vid}:{pid}"

def get_device_ids(device):
    """Extract VID, PID, serial from a pyudev Device object."""
    vid    = device.get("ID_VENDOR_ID")
    pid    = device.get("ID_MODEL_ID")
    serial = normalize_serial(device.get("ID_SERIAL_SHORT") or device.get("ID_SERIAL"))
    return vid, pid, serial

# ── Core Logic ────────────────────────────────────────────────────────────────
def check_or_insert_device(vid, pid, serial):
    device = db_linux.get_device_by_vid_pid(vid, pid)

    if device:
        device_type = device["device_type"]
        existing    = device["usb_serial"] or ""
        serials = set(existing.split(",")) if existing else set()
        serials.add(serial)
        db_linux.update_device_serial(device["id"], ",".join(serials))

        print(f"  ℹ   Status : {device_type.upper()}")

        if device_type == "blocked":
            print(f"  🔒  Re-enforcing block before analysis...")
            block_device(vid, pid)
    else:
        db_linux.insert_device(vid, pid, serial)
        print(f"  🆕  Status : NEW DEVICE")

    analyze_device_with_ml(vid, pid)

# ── ML + CAPTCHA ─────────────────────────────────────────────────────────────
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
    user_verified = verify_device_with_captcha(vid, pid, timeout=CAPTCHA_TIMEOUT)

    print()
    if user_verified:
        print(f"  ✅  ALLOWED  —  VID={vid}  PID={pid}")
        db_linux.update_device_status(vid, pid, "whitelisted", "low")
        allow_device(vid, pid)
    else:
        print(f"  🚫  BLOCKED  —  VID={vid}  PID={pid}")
        db_linux.update_device_status(vid, pid, "blocked", "high")
        block_device(vid, pid)

def handle_device_in_thread(vid, pid, serial):
    """Runs device processing in a background thread so monitor never blocks."""
    key = device_key_for(vid, pid, serial)
    try:
        print(f"\n{SEP}")
        print(f"  📱  Device Detected")
        print(f"       VID    : {vid}")
        print(f"       PID    : {pid}")
        print(f"       Serial : {serial}")
        print(f"{SEP}")
        check_or_insert_device(vid, pid, serial)
        print(f"\n{SEP}")
        print(f"  ✅  Processing complete  —  {key}")
        print(f"{SEP}\n")
    except Exception as e:
        print(f"\n  ⚠   Error processing {key} : {e}\n")
    finally:
        # Always release so device is re-checked on next plug-in
        with processing_lock:
            currently_processing.discard(key)
        print(f"  🔄  Monitor ready — plug any device to check again\n")

# ── Monitor Loop ──────────────────────────────────────────────────────────────
def usb_monitor_loop():
    print(f"\n{SEP}")
    print(f"  🔄  USB Monitoring Active  (Linux / pyudev)")
    print(f"{SEP}\n")

    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="usb", device_type="usb_device")
    monitor.start()

    while True:
        device = monitor.poll(timeout=1)

        if device is None:
            continue

        action = device.action
        vid, pid, serial = get_device_ids(device)

        if not (is_valid_hex_id(vid) and is_valid_hex_id(pid)):
            continue

        key = device_key_for(vid, pid, serial)

        if action == "remove":
            # On unplug: clear key so next plug-in triggers a fresh check
            with processing_lock:
                currently_processing.discard(key)
            print(f"\n  🔌  Unplugged : {key}  (will re-check on next plug-in)\n")

        elif action == "add":
            with processing_lock:
                if key in currently_processing:
                    print(f"  ⏳  Already processing {key}, skipping duplicate event")
                    continue
                currently_processing.add(key)

            # Spawn a thread per device — monitor loop stays non-blocking
            t = threading.Thread(
                target=handle_device_in_thread,
                args=(vid, pid, serial),
                daemon=True
            )
            t.start()

# ── Dashboard ─────────────────────────────────────────────────────────────────
def start_dashboard():
    threading.Thread(target=server_linux.start_server, daemon=True).start()
    time.sleep(1)
    #print(f"  🌐  Dashboard : http://localhost:8000\n")
    #webbrowser.open("http://localhost:8000/")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if os.geteuid() != 0:
        print(f"\n  ⚠   Warning: Not running as root.")
        print(f"       USB blocking via udev rules may not work without sudo.")
        print(f"       Consider running with: sudo python main.py\n")

    print(f"\n{SEP}")
    print(f"  🛡   USB Rubber Ducky Intrusion Detection System")
    print(f"{SEP}")
    start_dashboard()
    try:
        usb_monitor_loop()
    except KeyboardInterrupt:
        print(f"\n  ⏹   Stopped\n")
        sys.exit(0)
