# LAN Discovery

Adds local network gate discovery and LAN address-book integration.

This repository is private while it is being checked and verified.

## Install

```bash
cd /home/pi/Stargate-Final_Patches
rm -rf LAN-Discovery
git clone https://github.com/matelv-x/LAN-Discovery.git
cd LAN-Discovery
chmod +x *.sh
sudo ./install.sh /home/pi/sg1_v4
sudo systemctl restart stargate.service
```

## Restore / uninstall

```bash
cd /home/pi/Stargate-Final_Patches/LAN-Discovery
chmod +x restore.sh
sudo ./restore.sh /home/pi/sg1_v4
sudo systemctl restart stargate.service
```

## What it changes

- Adds LAN gate category behavior.
- Adds LAN scanning/discovery support.
- Updates address-book and subspace/address-manager integration.

## Attribution and originality

Original base project: StargateProject SG1 software from the BuildAStargate/Jordan/Kristian/Jonnerd project lineage.

Additional source/idea credit: Feature idea by Marcin/Codex, built over StargateProject address-book and subspace code.

How much is copied or changed: Medium patch. It modifies address-book, address-manager and subspace-related files.

The included `*.patch` file, when present, shows the exact text-level changes against the base software used while packaging.
