# LAN Gates / LAN Discovery

[![Downloads](https://img.shields.io/github/downloads/matelv-x/LAN-Discovery/total?label=downloads)](https://github.com/matelv-x/LAN-Discovery/releases)

Adds LAN gate scanning and local address-book integration.

After a complete scan, records for LAN gates that are no longer visible are
removed from the local address book.

## Install,

Clone or unzip this add-on into `/home/pi`, then run:

```bash
cd /home/pi
rm -rf LAN-Discovery
git clone https://github.com/matelv-x/LAN-Discovery.git
cd LAN-Discovery
chmod +x langate.sh restore-langate.sh
sudo ./langate.sh
sudo systemctl restart stargate.service
```

## Restore / uninstall

```bash
cd /home/pi/LAN-Discovery
sudo APP_DIR=/home/pi/sg1_v4 ./restore-langate.sh
sudo systemctl restart stargate.service
```

## What it changes

- Patches LAN gate support into address book/address manager code.
- Shows LAN Gates in both the original Address Book and Retro Address Book
  when Retro is installed.
- Colors LAN gates green in the original Address Book.
- Colors Black Hole addresses red in the original Address Book.
- Scans the local `/24` network for gates on ports 8080 and 80.
- Uses a guarded, low-worker LAN scan so Pi 3 systems do not stack scanner threads.
- Gives already-known slow gates a delayed eight-second recovery probe after
  the fast scan without extending retries for unrelated LAN services.
- Removes stale LAN records only after six consecutive missed scans.
- Supports `./langate.sh --scan-only` for later scans.
- Treats the IP address that answered the probe as authoritative, preventing a
  stale address advertised by a gate from poisoning the local route.
- Accepts standard SG1 addresses containing 6 to 9 symbols. Four-symbol custom
  protocols are intentionally outside this add-on's scope.
- Uses exact or uniquely resolvable address prefixes for LAN routing instead of
  silently choosing the first colliding two-symbol prefix. LAN resolution does
  not begin before the sixth symbol; Fan/Subspace routing remains unchanged.

## Attribution and originality

Original base project: StargateProject SG1 software from the BuildAStargate/Jordan/Kristian/Jonnerd project lineage.

Additional source/idea credit: Feature idea by matelv-x/Codex over StargateProject address-book and subspace code.

How much is copied or changed: Script-based patch and scanner; it does not copy the whole project.
