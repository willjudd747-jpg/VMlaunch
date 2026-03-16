VMlaunch

A clean QEMU frontend for Windows. Pick an ISO, hit launch, done.

---

What is it?

VMlaunch is a simple GUI for QEMU — the open source machine emulator. Instead of memorising long terminal commands, you get a clean dark interface where you browse for an ISO, set your RAM and CPU, and boot a virtual machine in seconds. No Python needed. No installer. Just a single .exe.

---

Download

Grab VMlaunch.exe from the files above or the website.

---

Setup

VMlaunch is a frontend — QEMU does the actual work and needs to be installed separately.

Install QEMU:
winget install QEMU

Or grab the installer from qemu.org/download/#windows

For best performance, enable Windows Hypervisor Platform:
Settings → Apps → Optional Features → More Windows Features → Windows Hypervisor Platform

---

How to use

1. Open VMlaunch.exe
2. Click Browse and pick an ISO or disk image
3. Set RAM and CPU cores with the sliders
4. Press LAUNCH VM

---

Supported image formats

.iso .img .raw .qcow2 .vmdk .vdi .vhd

---

Features

- WHPX hardware acceleration for near-native speed
- RAM from 256 MB to 16 GB
- 1 to 16 CPU cores
- Remembers your last 8 images
- VGA, networking, USB and audio options
- Live colour-coded console log
- Settings auto-saved between sessions

---

Building from source

Double-click build.bat — it handles everything automatically.

Or manually:
pip install pyinstaller
pyinstaller --onefile --windowed --name VMlaunch vmlaunch.py

Output: dist\VMlaunch.exe

---

FAQ

Mac or Linux?
Run the source directly: python3 vmlaunch.py

QEMU not detected?
Set the path to qemu-system-x86_64.exe manually in the QEMU PATH field.

VM running slow?
Enable Windows Hypervisor Platform and turn on Hardware Acceleration in the app.

Reset settings?
Delete C:\Users\YOURNAME\.vmlaunch.json

---

License: MIT
