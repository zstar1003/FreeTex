"""Settings regressions; run with QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QApplication
from tools.model_config_dialog import ModelConfigDialog, resource_path


class ModelConfigDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config_path = Path(self.directory.name) / "config.json"
        self.dialogs = []
        self.addCleanup(lambda: [dialog.close() for dialog in self.dialogs])
        for target in ("InfoBar.success", "InfoBar.error"):
            patcher = patch("tools.model_config_dialog." + target)
            mock = patcher.start()
            self.addCleanup(patcher.stop)
            if target.endswith("success"):
                self.successes = mock
            if target.endswith("error"):
                self.errors = mock
        patcher = patch("tools.model_config_dialog.resource_path",
                        side_effect=lambda path: str(self.config_path) if path == "config.json" else resource_path(path))
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_config(self, provider, **overrides):
        settings = dict(enabled=True, provider=provider, api_url="https://example.invalid/v1",
                        api_key="test-only-key", model_name="saved-vision-model")
        settings.update(overrides)
        self.config_path.write_text(json.dumps({"model_config": settings, "unrelated": 42}))
        return settings

    def open_dialog(self):
        dialog = ModelConfigDialog()
        self.dialogs.append(dialog)
        self.errors.assert_not_called()
        return dialog

    def test_connection_only_checks_model_list_and_explains_scope(self):
        self.write_config("自定义")
        original = self.config_path.read_bytes()
        dialog = self.open_dialog()
        sdk = MagicMock()
        with patch.dict("sys.modules", {"openai": sdk}):
            dialog.testButton.click()
        sdk.OpenAI.assert_called_once_with(api_key="test-only-key", base_url="https://example.invalid/v1")
        client = sdk.OpenAI.return_value
        client.models.list.assert_called_once_with()
        client.chat.completions.create.assert_not_called()
        self.assertIn("尚未验证", self.successes.call_args.kwargs["content"])
        self.assertIn("不发送图片", dialog.testButton.toolTip())
        self.errors.assert_not_called()
        self.assertEqual(self.config_path.read_bytes(), original)

    def test_model_list_failure_does_not_fall_back_to_inference(self):
        self.write_config("自定义")
        dialog = self.open_dialog()
        sdk = MagicMock()
        sdk.OpenAI.return_value.models.list.side_effect = RuntimeError("404 models endpoint")
        with patch.dict("sys.modules", {"openai": sdk}):
            dialog.test_connection()
        sdk.OpenAI.return_value.chat.completions.create.assert_not_called()
        self.successes.assert_not_called()
        self.assertIn("404 models endpoint", self.errors.call_args.kwargs["content"])
        self.assertIn("不代表视觉识别接口不可用", self.errors.call_args.kwargs["content"])

    def test_saved_settings_survive_open_confirm_and_reopen(self):
        for provider in ("硅基流动", "自定义"):
            with self.subTest(provider=provider):
                expected = self.write_config(provider)
                for _ in range(2):
                    dialog = self.open_dialog()
                    self.assertEqual(dialog.modelEdit.text(), expected["model_name"])
                    self.assertEqual(dialog.apiUrlEdit.text(), expected["api_url"])
                    self.assertEqual(dialog.apiKeyEdit.text(), expected["api_key"])
                    self.assertEqual(dialog.apiUrlEdit.isReadOnly(), provider == "硅基流动")
                    dialog.accept()
                    saved = json.loads(self.config_path.read_text())
                    self.assertEqual(saved["unrelated"], 42)
                    for key, value in expected.items():
                        self.assertEqual(saved["model_config"][key], value)

    def test_cancel_does_not_write_edits(self):
        self.write_config("自定义")
        original = self.config_path.read_bytes()
        dialog = self.open_dialog()
        dialog.modelEdit.setText("unsaved-model")
        dialog.reject()
        self.assertEqual(self.config_path.read_bytes(), original)

    def test_provider_switch_still_initializes_fields(self):
        self.write_config("自定义")
        dialog = self.open_dialog()
        dialog.providerComboBox.setCurrentText("硅基流动")
        self.assertTrue(dialog.apiUrlEdit.isReadOnly())
        self.assertEqual(dialog.apiUrlEdit.text(), "https://api.siliconflow.cn/v1")
        self.assertEqual(dialog.modelEdit.text(), "Qwen/Qwen2.5-VL-72B-Instruct")
        dialog.providerComboBox.setCurrentText("自定义")
        self.assertFalse(dialog.apiUrlEdit.isReadOnly())
        self.assertEqual(dialog.apiUrlEdit.text(), "")
        self.assertEqual(dialog.modelEdit.text(), "")

    def test_missing_fields_use_provider_defaults(self):
        for provider in ("硅基流动", "自定义"):
            with self.subTest(provider=provider):
                self.config_path.write_text(json.dumps({"model_config": {"provider": provider}}))
                dialog = self.open_dialog()
                self.assertEqual(dialog.apiUrlEdit.text(), "https://api.siliconflow.cn/v1" if provider == "硅基流动" else "")
                self.assertEqual(dialog.modelEdit.text(), "Qwen/Qwen2.5-VL-72B-Instruct" if provider == "硅基流动" else "")


if __name__ == "__main__":
    unittest.main()
