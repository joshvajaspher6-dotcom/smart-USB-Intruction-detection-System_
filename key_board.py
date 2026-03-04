
import os
import subprocess
import time
import threading

_blocked_ids = []

def is_root():
    return os.geteuid() ==  0

def get_xinput_keyboards(): 
    try:
        output = subprocess.check_output(
            ["xinput", "list", "--short"],
            text=True,
            stderr=subprocess.DEVNULL  # suppress stderr
        )
    except Exception:
        return []

    keyboard_ids = []
    skip_keywords = ["mouse", "pointer", "touchpad", "trackpad", "trackpoint",
                     "tablet", "stylus", "eraser", "cursor", "touch"]

    for line in output.splitlines():
        line_lower = line.lower()
        if any(kw in line_lower for kw in skip_keywords):
            continue
        if "keyboard" not in line_lower:
            continue
        if "id=" not in line_lower:
            continue
        try:
            id_part   = line.split("id=")[1].split()[0].strip()
            device_id = int(id_part)
            name      = line.split("\t")[0].strip().lstrip("⎜⎟⎠⎡⎣↳ ").strip()
            keyboard_ids.append((device_id, name))
        except (IndexError, ValueError):
            continue

    return keyboard_ids

def block_keyboard(seconds=None):
    global _blocked_ids

    keyboards = get_xinput_keyboards()
    if not keyboards:
        return False

    _blocked_ids = []
    for device_id, name in keyboards:
        try:
            subprocess.run(
                ["xinput", "disable", str(device_id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL   # suppress BadAccess X errors
            )
            _blocked_ids.append((device_id, name))
        except Exception:
            pass

    success = len(_blocked_ids) > 0
    if success:
        print("🔒 KEYBOARD LOCKED")
        if seconds:
            threading.Timer(seconds, unblock_keyboard).start()

    return success

def unblock_keyboard():
    global _blocked_ids

    for device_id, name in _blocked_ids:
        try:
            subprocess.run(
                ["xinput", "enable", str(device_id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL   # suppress any X errors
            )
        except Exception:
            pass

    _blocked_ids = []
    print("🔓 KEYBOARD UNLOCKED")
    return True

if __name__ == "__main__":
    block_keyboard(seconds=10)
    time.sleep(12)
=======
import ctypes
import time

def is_admin():
    """Check if running with admin privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def block_keyboard(seconds):
    """
    Block keyboard and mouse input for specified seconds.
    Note: This must be run as Administrator to work!
    """
    if not is_admin():
        print("⚠ WARNING: Not running as Administrator!")
        print("   Keyboard blocking will NOT work.")
        print("   Please run this script as Administrator.")
        return False
    
    print(f"🔒 KEYBOARD BLOCKED for {seconds} seconds...")
    
    try:
        # BlockInput(True) locks both keyboard and mouse
        ctypes.windll.user32.BlockInput(True)
        
        # Wait for the specified time
        time.sleep(seconds)
        
        # BlockInput(False) unlocks them
        ctypes.windll.user32.BlockInput(False)
        print("🔓 KEYBOARD UNLOCKED")
        return True
    except Exception as e:
        print(f"❌ Error blocking keyboard: {e}")
        # Make sure to unblock in case of error
        try:
            ctypes.windll.user32.BlockInput(False)
        except:
            pass
        return False

def unblock_keyboard():
    """
    Immediately unblock keyboard and mouse input.
    Emergency exit function.
    """
    try:
        ctypes.windll.user32.BlockInput(False)
        print("🔓 KEYBOARD FORCE UNLOCKED")
        return True
    except Exception as e:
        print(f"❌ Error unlocking keyboard: {e}")
        return False

if __name__ == "__main__":
    if not is_admin():
        print("\n❌ This script requires Administrator privileges!")
        print("   Please right-click and 'Run as Administrator'\n")
        input("Press Enter to exit...")
    else:
        # Change 10 to however many seconds you want
        block_keyboard(20)

