#!/usr/bin/env python3
"""Remove only residual LAN Discovery code after the three-way uninstall."""

import re
import sys
from pathlib import Path


PROTECTED_METHODS = ("valid_planet", "is_black_hole")
LAN_METHODS = (
    "start_lan_gate_discovery",
    "update_lan_gates_from_network",
    "_is_lan_api_open",
    "_probe_lan_stargate",
    "is_lan_stargate",
)
RESIDUE_MARKERS = (
    "get_lan_gates",
    "get_fan_and_lan_addresses",
    "update_lan_gates_from_network",
    "start_lan_gate_discovery",
    "is_lan_stargate",
    "_lan_gate_misses",
)


def method_pattern(name):
    return re.compile(
        rf"(?ms)^(?:    @[^\n]+\n)*    def {re.escape(name)}\(.*?"
        rf"(?=^    (?:@|def )|^class |\Z)"
    )


def protected_blocks(text, path):
    blocks = {}
    for name in PROTECTED_METHODS:
        match = method_pattern(name).search(text)
        if match is None:
            raise SystemExit(f"ERROR: required core method missing in {path}: {name}")
        blocks[name] = match.group(0)
    return blocks


def verify_protected(text, expected, path):
    for name, block in expected.items():
        match = method_pattern(name).search(text)
        if match is None or match.group(0) != block:
            raise SystemExit(f"ERROR: refusing to alter core method in {path}: {name}")


def remove_method(text, name):
    return method_pattern(name).sub("", text, count=1)


def clean_manager(path):
    text = path.read_text(encoding="utf-8")
    protected = protected_blocks(text, path)
    if not any(marker in text for marker in RESIDUE_MARKERS):
        print(f"Already clean of LAN Discovery residue: {path}")
        return

    for line in (
        "from concurrent.futures import ThreadPoolExecutor, as_completed\n",
        "import ipaddress as lan_discovery_ipaddress\n",
        "from ipaddress import ip_network\n",
        "import socket\n",
        "from threading import Lock, Thread\n",
    ):
        text = text.replace(line, "", 1)

    init_patterns = (
        r"^\s*self\.lan_discovery_interval\s*=.*\n",
        r"^\s*self\._lan_discovery_lock\s*=.*\n",
        r"^\s*self\._lan_gate_misses\s*=.*\n",
        r"^\s*stargate\.app\.schedule\..*self\.start_lan_gate_discovery.*\n",
        r"^\s*self\.start_lan_gate_discovery\(\)\s*\n",
    )
    for pattern in init_patterns:
        text = re.sub(pattern, "", text, count=1, flags=re.MULTILINE)

    for name in LAN_METHODS:
        text = remove_method(text, name)

    remote_pattern = method_pattern("is_remote_stargate")
    remote_match = remote_pattern.search(text)
    if remote_match and "is_lan_stargate" in remote_match.group(0):
        text = remote_pattern.sub(
            """    def is_remote_stargate(self, dialed_address):
        return self.is_fan_made_stargate(dialed_address)

""",
            text,
            count=1,
        )

    text = re.sub(
        r"    def get_gate_entry_from_ip\(self, remote_ip\):.*?"
        r"(?=    def get_stargate_address_from_ip\(self, remote_ip\):)",
        """    def get_gate_entry_from_ip(self, remote_ip):
        \"\"\"Find a fan gate entry by the source IP seen by the Subspace socket.\"\"\"
        remote_ip = str(remote_ip)
        for stargate_config in self.address_book.get_fan_gates().values():
            if str(stargate_config.get('ip_address')) == remote_ip:
                return stargate_config
        return None

""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"    def get_ip_from_stargate_address\(self, stargate_address\):.*?"
        r"(?=    def get_planet_name_from_ip\(self, remote_ip\):)",
        """    def get_ip_from_stargate_address(self, stargate_address):
        \"\"\"Return the IP address matching the first two fan-gate symbols.\"\"\"
        if len(stargate_address) > 1:
            for stargate_config in self.address_book.get_fan_gates().values():
                if stargate_address[0:2] == stargate_config['gate_address'][0:2]:
                    return stargate_config['ip_address']

        self.log.log(f'Unable to get IP for {stargate_address}')
        return None

""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = text.replace("        summary['lan'] = 0\n", "", 1)

    verify_protected(text, protected, path)
    remaining = [marker for marker in RESIDUE_MARKERS if marker in text]
    if remaining:
        raise SystemExit(
            f"ERROR: LAN manager residue remains in {path}: {remaining}"
        )
    compile(text, str(path), "exec")
    path.write_text(text, encoding="utf-8")


def clean_web_server(path):
    text = path.read_text(encoding="utf-8")
    if "get_lan_gates" not in text and "get_fan_and_lan_addresses" not in text:
        print(f"Already clean of LAN Discovery residue: {path}")
        return
    text = text.replace(
        "get_book().get_fan_and_lan_addresses()",
        "get_book().get_fan_gates()",
    )
    text, count = re.subn(
        r"^\s*\"lan_gate_count\":\s+len\(self\.stargate\.addr_manager\.get_book\(\)\.get_lan_gates\(\)\),\n",
        "",
        text,
        flags=re.MULTILINE,
    )
    if count > 1:
        raise SystemExit(f"ERROR: multiple LAN system-info counts in {path}")
    if "get_lan_gates" in text or "get_fan_and_lan_addresses" in text:
        raise SystemExit(f"ERROR: LAN web-server residue remains in {path}")
    compile(text, str(path), "exec")
    path.write_text(text, encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: clean_residue.py SG1_ROOT")
    root = Path(sys.argv[1]).resolve()
    targets = (
        (root / "classes/stargate_address_manager.py", clean_manager, True),
        (root / "classes/web_server.py", clean_web_server, True),
        (root / "web/.stellar-archive-addon/managed/stargate_address_manager.py", clean_manager, False),
        (root / "web/.stellar-archive-addon/managed/web_server.py", clean_web_server, False),
        (root / "web/.stellar-archive-addon/originals/stargate_address_manager.py", clean_manager, False),
        (root / "web/.stellar-archive-addon/originals/web_server.py", clean_web_server, False),
    )
    for path, cleaner, required in targets:
        if not path.is_file():
            if required:
                raise SystemExit(f"ERROR: missing required live file: {path}")
            print(f"Optional Stellar Archive snapshot absent: {path}")
            continue
        cleaner(path)
        print(f"Cleaned LAN Discovery residue: {path}")


if __name__ == "__main__":
    main()
