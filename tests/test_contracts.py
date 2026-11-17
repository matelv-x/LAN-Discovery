import json
import os
import stat
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_embedded_installer():
    text = (ROOT / "langate.sh").read_text(encoding="utf-8")
    start = '"$PYTHON_BIN" - <<\'PY\'\n'
    end = '\nPY\n\nif [ "$RESTART_SERVICE"'
    source = text.split(start, 1)[1].split(end, 1)[0]
    source = source.replace(
        'if __name__ == "__main__":\n    main()',
        'if __name__ == "__main__":\n    pass',
        1,
    )
    namespace = {"__name__": "lan_discovery_contract_test"}
    with tempfile.TemporaryDirectory() as directory:
        old_app_dir = os.environ.get("APP_DIR")
        old_address_file = os.environ.get("ADDRESS_FILE")
        os.environ["APP_DIR"] = directory
        os.environ["ADDRESS_FILE"] = str(Path(directory) / "addresses.json")
        try:
            exec(compile(source, "embedded-langate.py", "exec"), namespace)
        finally:
            if old_app_dir is None:
                os.environ.pop("APP_DIR", None)
            else:
                os.environ["APP_DIR"] = old_app_dir
            if old_address_file is None:
                os.environ.pop("ADDRESS_FILE", None)
            else:
                os.environ["ADDRESS_FILE"] = old_address_file
    return namespace, source


class InstallerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.installer, cls.source = load_embedded_installer()

    def test_supported_addresses_remain_six_to_nine_symbols(self):
        normalize = self.installer["normalize_address"]
        self.assertEqual(normalize([1, 2, 3, 4, 5, 6]), [1, 2, 3, 4, 5, 6])
        self.assertEqual(normalize("[1, 2, 3, 4, 5, 6, 7, 8, 9]"), list(range(1, 10)))
        self.assertEqual(normalize([1, 2, 3, 4]), [])
        self.assertEqual(normalize([1, 2, 3, 4, 5, 40]), [])
        self.assertEqual(normalize([1, 2, 3, 4, 5, True]), [])
        self.assertEqual(normalize({"address": [1, 2, 3, 4, 5, 6]}), [])

    def test_untrusted_gate_names_are_sanitized(self):
        safe_name = self.installer["safe_gate_name"]
        self.assertEqual(safe_name("  Highlander  ", "192.168.1.200"), "Highlander")
        self.assertEqual(safe_name("bad\nname", "192.168.1.200"), "Stargate 192.168.1.200")
        self.assertEqual(safe_name("x" * 81, "192.168.1.200"), "Stargate 192.168.1.200")

    def test_atomic_writer_preserves_permissions(self):
        writer = self.installer["atomic_write_text"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("old", encoding="utf-8")
            path.chmod(0o640)
            writer(path, "new")
            self.assertEqual(path.read_text(encoding="utf-8"), "new")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])

    def test_runtime_uses_probed_ip_and_unique_prefix_routing(self):
        self.assertIn("lan_ip = ip_addr", self.source)
        self.assertNotIn('lan_ip = data.get("lan_ip_address")', self.source)
        self.assertIn("if len(dialed) >= 6:", self.source)
        self.assertIn("matches = exact or compatible", self.source)
        self.assertIn("Ambiguous LAN address prefix", self.source)

    def test_slow_gate_recovery_does_not_remove_transient_misses(self):
        self.assertIn("time.sleep(3.5)", self.source)
        self.assertIn("known_failed_targets", self.source)
        self.assertIn("(ip_addr, port, 8.0)", self.source)
        self.assertIn("(ip_addr, port, 3.0)", self.source)
        self.assertIn("stale_miss_limit = 6", self.source)
        self.assertIn("timeout=(0.6, read_timeout)", self.source)

    def test_stellar_tracks_every_shared_file(self):
        metadata = json.loads((ROOT / "stargate-addon.json").read_text(encoding="utf-8"))
        expected = {
            "classes/stargate_address_book.py",
            "classes/stargate_address_manager.py",
            "classes/web_server.py",
            "web/js/address_book.js",
            "web/main.css",
            "web/retro/address_book.html",
            "web/retro/js/address_book.js",
            "web/retro/css/address_book.css",
        }
        self.assertEqual(set(metadata["archive_integration_files"]), expected)

    def test_uninstaller_does_not_chown_the_whole_sg1_tree(self):
        restore = (ROOT / "restore-langate.sh").read_text(encoding="utf-8")
        self.assertNotIn("chown -R", restore)


if __name__ == "__main__":
    unittest.main()
