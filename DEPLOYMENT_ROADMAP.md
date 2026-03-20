# ERR0RS ULTIMATE — Deployment Roadmap
## From Windows Repo → Kali VM → Pi 5 Image

---

## PHASE 1 — Get Repo into Kali VM

### Option A: Shared Folder (VirtualBox/VMware)
1. In your VM settings → Shared Folders → add H:\ERR0RS-Ultimate → mount as /mnt/hgfs/ERR0RS-Ultimate
2. Inside Kali VM:
```bash
cp -r /mnt/hgfs/ERR0RS-Ultimate ~/ERR0RS-Ultimate
cd ~/ERR0RS-Ultimate
```

### Option B: Git Push from Windows → Pull in VM
```powershell
# On Windows (H:\ERR0RS-Ultimate):
git add .
git commit -m "v2.0 UI dashboard + launcher"
git push origin main
```
```bash
# In Kali VM:
git clone https://github.com/GNOSISONE/ERR0RS-Ultimate ~/ERR0RS-Ultimate
cd ~/ERR0RS-Ultimate
```

### Option C: USB Transfer
```bash
# Copy .img or zip to USB, mount in VM, copy over
sudo cp -r /media/usb/ERR0RS-Ultimate ~/ERR0RS-Ultimate
```

---

## PHASE 2 — Deploy on Kali VM

```bash
cd ~/ERR0RS-Ultimate
sudo bash scripts/deploy_kali_vm.sh
```

**What this does automatically:**
- Installs all Kali tools (nmap, metasploit, hydra, sqlmap, etc.)
- Creates Python venv + installs all requirements
- Sets up PostgreSQL + Redis
- Creates .env config file
- Adds desktop launcher entry
- Runs smoke test to confirm everything loaded

**Test the UI immediately after:**
```bash
source venv/bin/activate
python3 src/ui/errorz_launcher.py
```
→ Browser opens at http://127.0.0.1:8765 — you should see ERR0RS dashboard

---

## PHASE 3 — Build Pi 5 Image (run inside Kali VM)

```bash
cd ~/ERR0RS-Ultimate
sudo bash scripts/build_pi_image.sh
```

**What this does:**
- Downloads Raspberry Pi OS Lite ARM64 as the base
- Expands it to 16GB
- Chroot installs all ERR0RS dependencies inside the image
- Copies your entire ERR0RS-Ultimate repo to /opt/ERR0RS-Ultimate
- Adds Hailo PCIe + PCIe splitter config to config.txt
- Creates a systemd service so ERR0RS auto-starts on boot
- Sets hostname to "phoenix"
- Outputs: ERR0RS-Phoenix-Pi5.img

**Output file location:**
```
~/ERR0RS-Ultimate/ERR0RS-Phoenix-Pi5.img  (~16GB)
```

---

## PHASE 4 — Transfer Image to Windows

```bash
# Option A: Copy to shared folder
cp ~/ERR0RS-Ultimate/ERR0RS-Phoenix-Pi5.img /mnt/hgfs/

# Option B: scp to Windows machine
scp ERR0RS-Phoenix-Pi5.img user@windows-ip:H:/
```

---

## PHASE 5 — Flash to Pi 5 NVMe

### Using Raspberry Pi Imager (recommended):
1. Download: https://www.raspberrypi.com/software/
2. Open Raspberry Pi Imager on Windows
3. Choose OS → Use Custom → select ERR0RS-Phoenix-Pi5.img
4. Choose Storage → your NVMe (via USB adapter) or SD card
5. Click Write → confirm

### Using dd (Linux/WSL):
```bash
sudo dd if=ERR0RS-Phoenix-Pi5.img of=/dev/sdX bs=4M status=progress conv=fsync
```

---

## PHASE 6 — First Boot on Pi 5

1. Insert NVMe into Pi 5 (Geekworm X1004 HAT)
2. Power on
3. SSH in or connect display:
```
hostname: phoenix.local
user:     pi
pass:     err0rs
```
4. ERR0RS dashboard auto-starts → http://phoenix.local:8765
5. Verify Hailo NPU:
```bash
hailortcli fw-control identify
```

---

## PHASE 7 — Pi-Specific Post-Boot Config

```bash
# Run this on the Pi after first boot
sudo bash /opt/ERR0RS-Ultimate/scripts/pi5_first_boot.sh
```
*(We'll build this script next — handles Hailo driver install, NVMe optimization, WiFi adapter setup)*

---

## CURRENT STATUS TRACKER

| Phase | Task                              | Status     |
|-------|-----------------------------------|------------|
| ✅    | ERR0RS-Ultimate framework         | DONE       |
| ✅    | Web UI dashboard + mascot         | DONE       |
| ✅    | Python UI launcher + API bridge   | DONE       |
| 🔲    | deploy_kali_vm.sh execution       | NEXT       |
| 🔲    | VM smoke test                     | NEXT       |
| 🔲    | build_pi_image.sh execution       | NEXT       |
| 🔲    | Image flash to Pi 5 NVMe          | NEXT       |
| 🔲    | First boot + Hailo verification   | NEXT       |
| 🔲    | WebSocket live tool streaming     | PLANNED    |
| 🔲    | Voice input (local Whisper)       | PLANNED    |
| 🔲    | Auto-pentest chaining engine      | PLANNED    |
