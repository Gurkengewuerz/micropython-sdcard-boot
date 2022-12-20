# SDCard Boot with OTA
Minimize accesses to the internal flash by using an external SD-Card as root directory. This way also OTA is available. I would not recommend OTA without an external flash because all these operations can contribute to degrade the flash and get to the maximum writes.  
If no external SD-Card should be used i would recommend eMMC ICs. With some changes also other Memory ICs can be used. Keep in mind that you maybe want to change the filesystem type from `FAT` to `LittleFS`.

## Boot Sequence
The ESP32 initialize the SD-Card with a 1-width SDIO (slot 2) interface. In `boot.py` after the power-up the file system is checked for FAT. If an unknown or uninitialized filesystem was found the SD-Card will be formatted. After an successful initialisation the root `/` will be unmounted and the SD-Card will be mounted as root `/`. After a successful mount the `main.py` from the new root will be executed.

## Flash
1. Flash the `boot.py` to the internal filesystem.
2. Power-up the board with an SD-Card
3. Check if SD-Card was initialised
4. Copy files as normal

To reflash the `boot.py` to the internal filesystem simply remove the SD-Card and power-up the board. This prevents the `main.py` from starting and you get a normal REPL.  
Alternatively pull Pin `18` to GND. This way MicroPython enters the REPL after boot and mounts the SD-Card to `/sd` for browsing.

## OTA
The OTA is heavily inspired by the great work of [mkomon/uota](https://github.com/mkomon/uota) and [rdehuyss/micropython-ota-updater](https://github.com/rdehuyss/micropython-ota-updater). Both projects didn't met my requirements. I wanted some kind of robust system with hash matching, undo on failing, replacing `main.py`, using my own server, etc.  
With my implementation you can do all of that but you need the folder structure like seen in `src/`. Everything can be replaced but only files in `/app` will be deleted if not needed anymore after an update. Any other file outside of `/app` will be replaced if changed to prevent any risk of corruption.

The bootloader (`boot.py`) can't be updated via OTA when booting from an SD-Card. This code must be robust as hell!

### Workflow
When `ota.install_update_if_available()` is called the following workflow is triggered

1. Cleanup previous versions if something went wrong before
2. Download newest version file with latest file name and hash
3. Create folder structure for new version (Default in `next/`)
4. Download latest file tar (Default in `firmware.tar`)
5. Unpack downloaded tar file (start to get critical here - if something outside `/app` changed the file will be replaced and can't rolled back)
6. Delete old `/app` folder
7. Move `/next` to `/app`
8. Cleanup if failed at any stage

### OTA Files
Files are stored on your own webserver. The most important file is `versions` which contains all known versions. The latest version is always on the bottom. 

```csv
0.0.1;0_0_1-firmware.tar;2988860ca0858eca16a795399148fca95b649784
```
Explanation: `Semantic Version;Filename relative to versions;sha1sum of filename`

**Pack files**  
`tar -cvf 0_0_1-firmware.tar app/ main.py # maybe other files`

**Generate SHA1 hash**  
`sha1sum *.tar`



### LTE/GSM Access
Some kind of implementation for LTE/GSM access is possible. For this a class can exists for WiFi and an external modem. A good example would be the OTA updater by [pycom](https://github.com/pycom/pycom-libraries/blob/96af79be7abcfca9f41a240decc6bd50b55bf5c4/examples/OTA/1.0.1/flash/lib/OTA.py).