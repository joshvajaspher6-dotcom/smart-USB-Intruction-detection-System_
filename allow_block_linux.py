import os
import subprocess

def is_root():
    """Check if running with root privileges on Linux"""
    return os.geteuid() == 0

def block_device(vid, pid):
    """Block device on Linux using udev and sysfs."""
    print(f"🔒 Blocking VID={vid} PID={pid}  (root={is_root()})")
    if not is_root():
        print("   ❌ Root rights required")
        return False
    
    # 1. Add udev rule
    rule_path = "/etc/udev/rules.d/99-usb-block.rules"
    rule_content = f'ACTION=="add", SUBSYSTEM=="usb", ATTR{{idVendor}}=="{vid.lower().zfill(4)}", ATTR{{idProduct}}=="{pid.lower().zfill(4)}", ATTR{{authorized}}="0"\n'
    
    try:
        rules = []
        if os.path.exists(rule_path):
            with open(rule_path, "r") as f:
                rules = f.readlines()
        
        if rule_content not in rules:
            rules.append(rule_content)
            with open(rule_path, "w") as f:
                f.writelines(rules)
            subprocess.run(["udevadm", "control", "--reload-rules"], capture_output=True)
        print("   🔒 udev ....... Rule added")
    except Exception as e:
        print(f"   ❌ udev block error: {e}")

    # 2. Disable existing via sysfs
    sys_usb = "/sys/bus/usb/devices/"
    try:
        if os.path.exists(sys_usb):
            for dev in os.listdir(sys_usb):
                dev_path = os.path.join(sys_usb, dev)
                vid_path = os.path.join(dev_path, "idVendor")
                pid_path = os.path.join(dev_path, "idProduct")
                if os.path.exists(vid_path) and os.path.exists(pid_path):
                    with open(vid_path, "r") as f:
                        dev_vid = f.read().strip()
                    with open(pid_path, "r") as f:
                        dev_pid = f.read().strip()
                    
                    if dev_vid.zfill(4).lower() == vid.lower() and dev_pid.zfill(4).lower() == pid.lower():
                        auth_path = os.path.join(dev_path, "authorized")
                        if os.path.exists(auth_path):
                            with open(auth_path, "w") as f:
                                f.write("0")
    except Exception as e:
        print(f"   ❌ sysfs block error: {e}")
    
    print("   ✅ Block applied..............")
    return True

def allow_device(vid, pid):
    """Unblock device on Linux using udev and sysfs."""
    print(f"✅ Allowing VID={vid} PID={pid}  (root={is_root()})")
    if not is_root():
        print("   ❌ Root rights required")
        return False
    
    # 1. Remove udev rule
    rule_path = "/etc/udev/rules.d/99-usb-block.rules"
    rule_content = f'ACTION=="add", SUBSYSTEM=="usb", ATTR{{idVendor}}=="{vid.lower().zfill(4)}", ATTR{{idProduct}}=="{pid.lower().zfill(4)}", ATTR{{authorized}}="0"\n'
    
    try:
        if os.path.exists(rule_path):
            with open(rule_path, "r") as f:
                rules = f.readlines()
            
            if rule_content in rules:
                rules.remove(rule_content)
                with open(rule_path, "w") as f:
                    f.writelines(rules)
                subprocess.run(["udevadm", "control", "--reload-rules"], capture_output=True)
            print("   🔓 udev ....... Rule removed")
    except Exception as e:
        print(f"   ❌ udev unblock error: {e}")

    # 2. Enable existing via sysfs
    sys_usb = "/sys/bus/usb/devices/"
    try:
        if os.path.exists(sys_usb):
            for dev in os.listdir(sys_usb):
                dev_path = os.path.join(sys_usb, dev)
                vid_path = os.path.join(dev_path, "idVendor")
                pid_path = os.path.join(dev_path, "idProduct")
                if os.path.exists(vid_path) and os.path.exists(pid_path):
                    with open(vid_path, "r") as f:
                        dev_vid = f.read().strip()
                    with open(pid_path, "r") as f:
                        dev_pid = f.read().strip()
                    
                    if dev_vid.zfill(4).lower() == vid.lower() and dev_pid.zfill(4).lower() == pid.lower():
                        auth_path = os.path.join(dev_path, "authorized")
                        if os.path.exists(auth_path):
                            with open(auth_path, "w") as f:
                                f.write("1")
    except Exception as e:
        print(f"   ❌ sysfs unblock error: {e}")
    
    print("   ✅ Allow applied")
    return True