import machine
import os

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

if success:
    os.umount("/")
    os.mount(vfs, "/")
else:
    print("Failed to mount SDCard")