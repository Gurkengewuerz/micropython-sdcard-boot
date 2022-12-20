import machine
import network
import time
import gc

from .lib import urequests
from .lib import uota


wifi_config = {}

def load_wifi_config():
    try:
        with open("wifi.cfg", "r") as f:
            wifi_config.update(eval(f.read()))
        return True
    except OSError:
        return False

def do_connect():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("connecting to network...")
        sta_if.active(True)
        sta_if.connect(wifi_config["network"], wifi_config["password"])
        while not sta_if.isconnected():
            pass
    print("network config", sta_if.ifconfig())

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
    machine.reset()

while True:
    time.sleep_ms(30 * 1000)
    print("sleeping")
