import machine
import network
import time
import gc

from .lib import urequests
from .lib import uota


wifi_config = {}
wlan = None

def load_wifi_config():
    try:
        with open("wifi.cfg", "r") as f:
            wifi_config.update(eval(f.read()))
        return True
    except OSError:
        return False

def do_connect():
    global wlan
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        print("connecting to network...")
        wlan.active(True)
        wlan.connect(wifi_config["network"], wifi_config["password"])
        while not wlan.isconnected():
            pass
    print("network config", wlan.ifconfig())

if load_wifi_config():
    do_connect()
else:
    print("failed to load wifi.cfg")

req = urequests.get("https://mc8051.de/logo.txt")
print(req.text)
gc.collect()

ota = uota.OTA("https://mc8051.de/firmware", quite=False)
if not ota.install_update_if_available():
    print("No Update needed")
else:
    print("Update successful")
    # disconnect from wifi to prevent "pll_cap_ext 10" errors
    if wlan is not None:
        if wlan.isconnected():
            wlan.disconnect()
        wlan.active(False)
    machine.reset()

while True:
    time.sleep_ms(30 * 1000)
    print("sleeping")
