import machine
import os
import sys
import gc

FAT_FILE = ".mc8051"
success = False

print("Connecting to SDCard")
bdev = machine.SDCard(slot=1, width=1)
try:
    vfs = os.VfsFat(bdev)

    for i in range(5):
        print("Reading SDCard config")
        try:
            vfs.stat(FAT_FILE)
            print("File exsits - everything is fine")
            success = True
            break
        except OSError as e:
            # errno.ENODEV = unknown FileSystem
            # errno.ENOENT = File not exists
            print("Formatting SDCard")
            os.VfsFat.mkfs(bdev)
            
            with vfs.open(FAT_FILE, "w") as f:
                f.write("\0")
except OSError as e:
    pass

interrupt_pin = machine.Pin(18, machine.Pin.IN, machine.Pin.PULL_UP)

if success:
    if interrupt_pin.value() == 0:
        print("Interrupted mounting - SDCard is now mounted in /sd")
        os.mount(vfs, "/sd")
        sys.exit()
    os.umount("/")
    os.mount(vfs, "/")
else:
    print("Failed to mount SDCard")
    sys.exit()

gc.collect()