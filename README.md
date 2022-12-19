# SDCard Boot
Minimize accesses to the internal flash by using an external SD-Card as root directory.

## Boot Sequence
The ESP32 initialize the SD-Card with a 1-width SDIO (slot 2) interface. In `boot.py` after the power-up the file system is checked for FAT. If an unknown or uninitialized filesystem was found the SD-Card will be formatted. After an successful initialisation the root `/` will be unmounted and the SD-Card will be mounted as root `/`. After a successful mount the `main.py` from the new root will be executed.

## Flash
1. Flash the `boot.py` to the internal filesystem.
2. Power-up the board with an SD-Card
3. Check if SD-Card was initialised
4. Copy files as normal

To relash the `boot.py` to the internal filesystem simply remove the SD-Card an power-up the board. This prevents the `main.py` from starting and you get a normal REPL.