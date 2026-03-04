"""
USB Device Verification Handler
================================

Integrates keyboard blocking and CAPTCHA verification for USB devices.
When a USB device is detected, this module:
1. Blocks keyboard/mouse input
2. Shows CAPTCHA verification
3. Auto-blocks device and unblocks keyboard after 10 seconds if not verified
"""

import threading
import time
import ctypes
from captcha import show_captcha

# Global state for keyboard blocking
keyboard_blocked = False
keyboard_lock = threading.Lock()


def block_keyboard():
    global keyboard_blocked
    try:
        with keyboard_lock:
            if not keyboard_blocked:
                ctypes.windll.user32.BlockInput(True)
                keyboard_blocked = True
    except Exception as e:
        print(f"⚠ Could not block keyboard: {e}")


def unblock_keyboard():
    global keyboard_blocked
    try:
        with keyboard_lock:
            if keyboard_blocked:
                ctypes.windll.user32.BlockInput(False)
                keyboard_blocked = False
    except Exception as e:
        print(f"⚠ Could not unblock keyboard: {e}")


def verify_device_with_captcha(vid, pid, timeout=10):
    """Show CAPTCHA; return True=allow, False=block."""
    block_keyboard()

    verification_result = None
    captcha_complete = threading.Event()

    def run_captcha():
        nonlocal verification_result
        try:
            verification_result = show_captcha(timeout=timeout)
        except Exception as e:
            print(f"❌ CAPTCHA error: {e}")
            verification_result = False
        finally:
            captcha_complete.set()

    threading.Thread(target=run_captcha, daemon=True).start()
    captcha_complete.wait(timeout=timeout + 5)
    unblock_keyboard()
    return bool(verification_result)


if __name__ == "__main__":
    # Test the verification handler
    print("Testing USB Verification Handler...")
    result = verify_device_with_captcha("1234", "5678", timeout=10)
    print(f"\nFinal result: {'ALLOWED' if result else 'BLOCKED'}")
