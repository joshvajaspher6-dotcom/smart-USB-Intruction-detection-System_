import ctypes, subprocess, shutil, os, wmi
from usbmonitor import USBMonitor
from usbmonitor.attributes import ID_VENDOR_ID, ID_MODEL_ID
from registry_block import registry_block_device, registry_unblock_device


def find_devcon():
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "devcon.exe")
    return local if os.path.isfile(local) else (
        shutil.which("devcon.exe") or shutil.which("devcon")
    )


def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False


def _devcon(command, vid, pid, devcon_path=None):
    """
    Run devcon against the wildcard pattern for a VID/PID.
    Returns True if at least one interface was affected.
    """
    devcon_path = devcon_path or find_devcon()
    if not devcon_path:
        print("   ⚠️ devcon.exe not found — skipping devcon step")
        return False

    pattern = f"USB\\VID_{vid.upper()}&PID_{pid.upper()}*"
    try:
        r = subprocess.run(
            [devcon_path, command, pattern],
            capture_output=True, text=True, timeout=15
        )
        out = r.stdout + r.stderr
        ok = sum(
            1 for line in out.splitlines()
            if ("disabled" in line.lower() or "enabled" in line.lower())
            and "failed" not in line.lower()
        )
        print(f"   devcon {command}: {ok} interface(s) affected")
        return ok > 0
    except Exception as e:
        print(f"   ⚠️ devcon error: {e}")
        return False


def _devcon_by_instance(command, vid, pid, devcon_path=None):
    """Per-instance fallback using exact @DeviceID — catches composite devices."""
    devcon_path = devcon_path or find_devcon()
    if not devcon_path:
        return False

    count = 0
    try:
        for d in wmi.WMI().Win32_PnPEntity():
            if (d.DeviceID
                    and f"VID_{vid.upper()}" in d.DeviceID
                    and f"PID_{pid.upper()}" in d.DeviceID):
                r = subprocess.run(
                    [devcon_path, command, f"@{d.DeviceID}"],
                    capture_output=True, text=True, timeout=10
                )
                if r.returncode == 0:
                    count += 1
    except Exception as e:
        print(f"   ⚠️ devcon instance error: {e}")

    return count > 0


def block_device(vid, pid, devcon_path=None):
    """Block a USB device by VID/PID via registry policy + devcon disable."""
    print(f"🔒 Blocking VID={vid} PID={pid}  (admin={is_admin()})")
    registry_block_device(vid, pid)
    if not _devcon("disable", vid, pid, devcon_path):
        _devcon_by_instance("disable", vid, pid, devcon_path)
    print("   ✅ Block applied..............")


def allow_device(vid, pid, devcon_path=None):
    """Unblock a USB device by VID/PID via registry policy + devcon enable."""
    print(f"✅ Allowing VID={vid} PID={pid}  (admin={is_admin()})")
    registry_unblock_device(vid, pid)
    if not _devcon("enable", vid, pid, devcon_path):
        _devcon_by_instance("enable", vid, pid, devcon_path)
    print("   ✅ Allow applied")