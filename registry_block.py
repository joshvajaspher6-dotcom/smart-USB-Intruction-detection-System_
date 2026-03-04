import ctypes, time, winreg, subprocess, wmi

RESTRICTIONS_PATH = r"SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions"
DENY_IDS_PATH     = RESTRICTIONS_PATH + r"\DenyDeviceIDs"


def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False


def _ensure_policy_enabled():
    try:
        k = winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE, RESTRICTIONS_PATH, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(k, "DenyDeviceIDs",            0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "DenyDeviceIDsRetroactive", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(k)
        return True
    except Exception as e:
        print(f"   ❌ Policy error: {e}")
        return False


def _refresh_policy():
    """Force Group Policy to re-evaluate registry changes immediately."""
    try:
        subprocess.run(
            ["gpupdate", "/force"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=30
        )
    except Exception as e:
        print(f"   ⚠️ gpupdate failed: {e}")


def get_hardware_ids(vid, pid):
    """Return base hardware ID + any live device instance IDs matching VID/PID."""
    ids = {f"USB\\VID_{vid.upper()}&PID_{pid.upper()}"}
    try:
        for d in wmi.WMI().Win32_PnPEntity():
            if (d.DeviceID
                    and f"VID_{vid.upper()}" in d.DeviceID
                    and f"PID_{pid.upper()}" in d.DeviceID):
                ids.add(d.DeviceID)
    except Exception:
        pass
    return list(ids)


def _trigger_reinstall(vid, pid):
    """
    Disable then re-enable devices via pnputil so the new policy is enforced
    without requiring a physical replug.
    """
    try:
        for d in wmi.WMI().Win32_PnPEntity():
            if (d.DeviceID
                    and f"VID_{vid.upper()}" in d.DeviceID
                    and f"PID_{pid.upper()}" in d.DeviceID):
                dev_id = d.DeviceID
                subprocess.run(
                    ["pnputil", "/disable-device", dev_id],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10
                )
                time.sleep(0.5)
                subprocess.run(
                    ["pnputil", "/enable-device", dev_id],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10
                )
    except Exception as e:
        print(f"   ⚠️ Reinstall trigger failed: {e}")


def registry_block_device(vid, pid):
    if not is_admin():
        print("   ❌ Admin rights required")
        return False
    if not _ensure_policy_enabled():
        return False
    try:
        k = winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE, DENY_IDS_PATH, 0, winreg.KEY_ALL_ACCESS
        )
        # Single pass: collect existing values AND track max numeric index
        existing = set()
        max_idx = 0
        i = 0
        while True:
            try:
                name, val, _ = winreg.EnumValue(k, i)
                existing.add(val.lower())
                if name.isdigit():
                    max_idx = max(max_idx, int(name))
                i += 1
            except OSError:
                break

        added = 0
        for hw in get_hardware_ids(vid, pid):
            if hw.lower() not in existing:
                max_idx += 1
                winreg.SetValueEx(k, str(max_idx), 0, winreg.REG_SZ, hw)
                added += 1

        winreg.CloseKey(k)
        print(f"   🔒 Registry ....... Device added")

        _refresh_policy()       # ← apply policy before touching device
        _trigger_reinstall(vid, pid)
        return True
    except Exception as e:
        print(f"   ❌ Registry block error: {e}")
        return False


def registry_unblock_device(vid, pid):
    if not is_admin():
        print("   ❌ Admin rights required")
        return False
    hw_ids = [h.lower() for h in get_hardware_ids(vid, pid)]
    try:
        k = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, DENY_IDS_PATH, 0, winreg.KEY_ALL_ACCESS
        )
    except FileNotFoundError:
        print("   ℹ️ Registry: not in deny list")
        return True

    removed, i = 0, 0
    while True:
        try:
            name, val, _ = winreg.EnumValue(k, i)
            if val.lower() in hw_ids:
                winreg.DeleteValue(k, name)
                removed += 1
                # Don't increment i — registry re-indexes after delete
            else:
                i += 1
        except OSError:
            break

    winreg.CloseKey(k)
    print(f"   🔓 Registry: Devices entries removed")

    _refresh_policy()           # ← apply policy before re-enabling device
    _trigger_reinstall(vid, pid)
    return True