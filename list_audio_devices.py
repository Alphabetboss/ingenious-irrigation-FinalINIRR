# scripts/list_audio_devices.py
import sounddevice as sd

def main():
    print("\n=== Input/Output Audio Devices ===")
    devices = sd.query_devices()
    default_in, default_out = sd.default.device
    for idx, d in enumerate(devices):
        mark_in = " (DEFAULT IN)" if idx == default_in else ""
        mark_out = " (DEFAULT OUT)" if idx == default_out else ""
        io = []
        if d['max_input_channels'] > 0:
            io.append("IN")
        if d['max_output_channels'] > 0:
            io.append("OUT")
        print(f"[{idx:>2}] {d['name']}  [{'&'.join(io)}]{mark_in}{mark_out}")
    print("\nTip:")
    print("  Set II_INPUT_DEVICE to a substring (e.g., 'USB') or an exact index (e.g., '2').")
    print("  PowerShell examples:")
    print('    $env:II_INPUT_DEVICE = "USB"')
    print('    $env:II_INPUT_DEVICE = "2"')

if __name__ == "__main__":
    main()
