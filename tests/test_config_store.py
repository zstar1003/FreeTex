import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import config_store as store


class ConfigStoreTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.user = self.root / "user" / "config.json"
        self.legacy = self.root / "bundle" / "config.json"
        self.legacy.parent.mkdir()
        self.original = {"model_config": {"api_key": "synthetic-test-secret", "enabled": True},
                         "shortcuts": {"paste": "Ctrl+V"}, "other": 123}
        self.legacy.write_text(json.dumps(self.original), encoding="utf-8")
        for name, value in [("config_path", self.user), ("legacy_config_path", self.legacy)]:
            patcher = patch.object(store, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_migrates_once_without_modifying_bundle_and_survives_upgrade(self):
        before = self.legacy.read_bytes()
        self.assertEqual(store.read_config(), self.original)
        self.assertEqual(self.legacy.read_bytes(), before)
        store.update_config_section("model_config", {"model_name": "chosen"})
        self.legacy.write_text('{"model_config": {"api_key": "new-bundle-default"}}')
        saved = store.read_config()
        self.assertEqual(saved["model_config"]["api_key"], "synthetic-test-secret")
        self.assertEqual(saved["model_config"]["model_name"], "chosen")
        self.assertEqual(saved["shortcuts"], self.original["shortcuts"])
        self.assertEqual(saved["other"], 123)
        if os.name == "posix":
            self.assertEqual(self.user.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.user.parent.stat().st_mode & 0o777, 0o700)

    def test_atomic_write_failure_preserves_previous_config(self):
        store.read_config()
        before = self.user.read_bytes()
        with patch.object(store.os, "replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                store.update_config_section("shortcuts", {"paste": "Alt+V"})
        self.assertEqual(self.user.read_bytes(), before)
        self.assertEqual(list(self.user.parent.glob("*.tmp")), [])

    def test_migration_failure_does_not_modify_legacy_or_report_success(self):
        before = self.legacy.read_bytes()
        with patch.object(store.os, "link", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                store.read_config()
        self.assertFalse(self.user.exists())
        self.assertEqual(self.legacy.read_bytes(), before)
        self.assertEqual(list(self.user.parent.glob("*.tmp")), [])

    def test_concurrent_migration_never_overwrites_existing_user_file(self):
        def competing_writer(source, destination):
            Path(destination).write_text('{"concurrent": true}')
            raise FileExistsError("already created")
        with patch.object(store.os, "link", side_effect=competing_writer):
            self.assertEqual(store.read_config(), {"concurrent": True})
        self.assertEqual(json.loads(self.user.read_text()), {"concurrent": True})

    def test_invalid_existing_settings_never_fall_back_or_get_overwritten(self):
        self.user.parent.mkdir()
        for bad in ("broken json", "[]"):
            self.user.write_text(bad)
            with self.assertRaises(ValueError):
                store.update_config_section("shortcuts", {"paste": "Alt+V"})
            self.assertEqual(self.user.read_text(), bad)

    def test_invalid_legacy_does_not_create_user_config(self):
        self.legacy.write_text("broken json")
        with self.assertRaises(ValueError):
            store.read_config()
        self.assertFalse(self.user.exists())

    def test_section_updates_preserve_other_sections_and_unknown_keys(self):
        store.update_config_section("model_config", {"model_name": "new-model"})
        store.update_config_section("shortcuts", {"paste": "Alt+V"})
        saved = store.read_config()
        self.assertEqual(saved["model_config"]["model_name"], "new-model")
        self.assertEqual(saved["model_config"]["api_key"], "synthetic-test-secret")
        self.assertEqual(saved["other"], 123)

    @unittest.skipUnless(os.name == "posix", "symlinks need platform support")
    def test_existing_symlink_is_rejected(self):
        self.user.parent.mkdir()
        self.user.symlink_to(self.legacy)
        with self.assertRaises(OSError):
            store.read_config()
        self.assertTrue(self.user.is_symlink())


class ConfigPathTest(unittest.TestCase):
    def test_platform_user_paths(self):
        with patch.object(store.Path, "home", return_value=Path("/synthetic-home")):
            with patch.object(store.sys, "platform", "darwin"):
                self.assertEqual(store.config_path(), Path("/synthetic-home/Library/Application Support/FreeTex/config.json"))
            with patch.object(store.sys, "platform", "linux"), patch.dict(os.environ, {"XDG_CONFIG_HOME": "/synthetic-xdg"}):
                self.assertEqual(store.config_path(), Path("/synthetic-xdg/FreeTex/config.json"))
            with patch.object(store.sys, "platform", "win32"), patch.dict(os.environ, {"APPDATA": "/synthetic-appdata"}):
                self.assertEqual(store.config_path(), Path("/synthetic-appdata/FreeTex/config.json"))

    def test_frozen_legacy_location_only(self):
        with patch.object(store.sys, "frozen", True, create=True), patch.object(store.sys, "_MEIPASS", "/synthetic-bundle", create=True):
            self.assertEqual(store.legacy_config_path(), Path("/synthetic-bundle/config.json"))


if __name__ == "__main__":
    unittest.main()
