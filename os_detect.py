import platform
import subprocess
import signal
import sys

def run_script(script_name):
    process = subprocess.Popen(["python3", script_name])

    def signal_handler(sig, frame):
        print(f"Interrupt received, terminating {script_name}...")
        process.terminate()
        process.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    print(f"Running {script_name} on {platform.system()}... Press Ctrl+C to stop.")

    process.wait()

def main():
    current_os = platform.system()
    print(f"Detected OS: {current_os}")

    if current_os == "Windows":
        run_script("usb_monitor.py")
    elif current_os == "Linux":
        run_script("usb_monitor_linux.py")
    else:
        print("No matching script to run for this OS.")

if __name__ == "__main__":
    main()