#!/usr/bin/env python3
"""Reverse only LAN Discovery code changes with a three-way merge.

For every shared file, B is the install-time backup, A is the result of
replaying this package's current patcher on B, and C is the live file.  Merging
C with base A and other B removes this add-on while retaining changes made
after installation.  All merges are prepared before any live file is written.
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


TARGETS = (
    "classes/stargate_address_book.py",
    "classes/stargate_address_manager.py",
    "classes/web_server.py",
    "web/js/address_book.js",
    "web/main.css",
    "web/retro/address_book.html",
    "web/retro/js/address_book.js",
    "web/retro/css/address_book.css",
)

PYTHON_FUNCTIONS = {
    "classes/stargate_address_book.py": (
        "__reset_storage", "get_entry_by_address", "get_all_nonlocal_addresses",
        "get_fan_and_lan_addresses", "get_fan_gates", "set_fan_gate",
        "get_lan_gates", "get_lan_gate_by_address", "set_lan_gate",
    ),
    "classes/stargate_address_manager.py": (
        "__init__", "start_lan_gate_discovery", "update_lan_gates_from_network",
        "_is_lan_api_open", "_probe_lan_stargate", "get_ip_from_stargate_address",
        "get_gate_entry_from_ip", "get_stargate_address_from_ip",
        "get_planet_name_from_ip", "get_summary_from_book",
    ),
}

PROTECTED_METHODS = {
    "classes/stargate_address_manager.py": ("valid_planet", "is_black_hole"),
}


def fail(message):
    raise SystemExit(f"ERROR: {message}")


def latest_backup(path):
    matches = sorted(
        path.parent.glob(path.name + ".bak-langate-*"),
        key=lambda item: item.stat().st_mtime_ns,
        reverse=True,
    )
    return matches[0] if matches else None


def patch_source(installer):
    text = installer.read_text(encoding="utf-8")
    start_marker = '"$PYTHON_BIN" - <<\'PY\'\n'
    end_marker = "\nPY\n\nif [ \"$RESTART_SERVICE\""
    if start_marker not in text or end_marker not in text:
        fail("cannot read the LAN patch program from this maintenance package")
    source = text.split(start_marker, 1)[1].split(end_marker, 1)[0]
    old = 'if __name__ == "__main__":\n    main()'
    new = 'if __name__ == "__main__":\n    patch_app()'
    if old not in source:
        fail("cannot isolate the LAN code patcher")
    return source.replace(old, new, 1)


def method_pattern(name):
    return re.compile(
        rf"(?ms)^(?:    @[^\n]+\n)*    def {re.escape(name)}\(.*?"
        rf"(?=^    (?:@|def )|^class |\Z)"
    )


def verify_protected_methods(relative, before, after):
    for name in PROTECTED_METHODS.get(relative, ()):
        pattern = method_pattern(name)
        original = pattern.search(before)
        candidate = pattern.search(after)
        if original is None:
            fail(f"required core method missing before uninstall: {relative}:{name}")
        if candidate is None or candidate.group(0) != original.group(0):
            fail(f"refusing to alter core method during uninstall: {relative}:{name}")


def surgical_python_fallback(relative, current, backup):
    """Restore only installer-owned methods when line merging overlaps."""
    names = PYTHON_FUNCTIONS.get(relative)
    if not names:
        return None
    output = current
    for name in names:
        pattern = method_pattern(name)
        prior = pattern.search(backup)
        present = pattern.search(output)
        if prior and present:
            output = pattern.sub(prior.group(0), output, count=1)
        elif not prior and present:
            output = pattern.sub("", output, count=1)
    compile(output, relative, "exec")
    return output


def main():
    if len(sys.argv) != 3:
        fail("usage: surgical_restore.py APP_DIR langate.sh")
    app = Path(sys.argv[1]).resolve()
    installer = Path(sys.argv[2]).resolve()
    if not app.is_dir() or not installer.is_file():
        fail("application folder or installer is missing")
    if shutil.which("git") is None:
        fail("git is required for a conflict-safe surgical merge")

    live = {}
    backups = {}
    for rel in TARGETS:
        target = app / rel
        backup = latest_backup(target)
        if not target.is_file():
            fail(f"cannot safely remove LAN Discovery: missing live file for {rel}")
        live[rel] = target
        if backup is not None:
            backups[rel] = backup
    if not backups:
        fail("cannot safely remove LAN Discovery: no install-time code backups were found")

    with tempfile.TemporaryDirectory(prefix="lan-discovery-uninstall-") as name:
        temp = Path(name)
        for rel, target in live.items():
            destination = temp / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backups.get(rel, target), destination)
        for rel in ("config/milkyway-addresses.json", "config/milkyway-config.json"):
            source = app / rel
            destination = temp / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_file():
                shutil.copy2(source, destination)
            else:
                destination.write_text("{}\n", encoding="utf-8")

        env = os.environ.copy()
        env.update({
            "APP_DIR": str(temp),
            "ADDRESS_FILE": str(temp / "config/milkyway-addresses.json"),
            "PATCH_APP": "1",
        })
        replay = subprocess.run(
            [sys.executable, "-c", patch_source(installer)],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
        if replay.returncode:
            fail("could not reconstruct the installed LAN patch: " + replay.stderr[-500:])

        prepared = {}
        conflicts = []
        for rel, backup in backups.items():
            result = subprocess.run(
                ["git", "merge-file", "-p", str(live[rel]), str(temp / rel), str(backup)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode != 0:
                fallback = surgical_python_fallback(
                    rel,
                    live[rel].read_text(encoding="utf-8"),
                    backup.read_text(encoding="utf-8"),
                )
                if fallback is None:
                    conflicts.append(rel)
                else:
                    prepared[rel] = fallback
                    print(f"Resolved overlapping edits by owned Python methods: {rel}")
            else:
                prepared[rel] = result.stdout
        if conflicts:
            fail("surgical merge conflict; no files changed: " + ", ".join(conflicts))

        for rel, content in prepared.items():
            verify_protected_methods(
                rel,
                live[rel].read_text(encoding="utf-8"),
                content,
            )

        for rel, content in prepared.items():
            live[rel].write_text(content, encoding="utf-8")
            print(f"Surgically cleaned: {rel}")

        for rel in TARGETS:
            if rel not in backups:
                print(f"Preserved unchanged-by-installer file: {rel}")

    print("Preserved: config/milkyway-addresses.json (LAN records and user data)")


if __name__ == "__main__":
    main()
