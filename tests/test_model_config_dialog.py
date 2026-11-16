"""Settings regressions; run with QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests."""
import json
import tempfile
import unittest
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from PyQt5.QtTest import QTest
from PyQt5.QtCore import QThreadPool, QTimer, QCoreApplication, QEvent
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

    def wait_for(self, predicate, timeout=3000):
        deadline = time.monotonic() + timeout / 1000
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertTrue(predicate(), "background operation did not finish")

    def test_delayed_local_service_keeps_gui_responsive_and_ignores_closed_result(self):
        # Exercise a real loopback HTTP request without depending on a provider/SDK.
        from urllib.request import build_opener, ProxyHandler
        entered = threading.Event()
        release = threading.Event()
        paths = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path)
                entered.set()
                release.wait(2)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"data":[]}')
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.addCleanup(release.set)
        self.write_config("自定义", api_url=f"http://127.0.0.1:{server.server_port}/v1")
        dialog = self.open_dialog()
        dialog.show()
        sdk = MagicMock()
        client = sdk.OpenAI.return_value.__enter__.return_value
        def fetch():
            opener = build_opener(ProxyHandler({}))
            with opener.open(dialog_url + "/models", timeout=2) as response:
                return response.read()
        dialog_url = dialog.apiUrlEdit.text()
        client.models.list.side_effect = fetch
        ticks = []
        timer = QTimer()
        timer.timeout.connect(lambda: ticks.append(True))
        timer.start(10)
        with patch.dict("sys.modules", {"openai": sdk}):
            started = time.monotonic()
            dialog.test_connection()
            self.assertLess(time.monotonic() - started, 0.2)
            self.wait_for(entered.is_set)
            dialog.test_connection()  # programmatic duplicate is ignored too
            self.assertFalse(dialog.testButton.isEnabled())
            QTest.qWait(40)
            self.assertTrue(ticks)
            dialog.reject()
            self.assertFalse(dialog.isVisible())
            release.set()
            self.wait_for(lambda: QThreadPool.globalInstance().activeThreadCount() == 0)
            QTest.qWait(20)
        timer.stop()
        self.assertEqual(paths, ["/v1/models"])
        self.successes.assert_not_called()
        self.errors.assert_not_called()
        self.assertTrue(dialog.testButton.isEnabled())
        dialog.show()
        # A closed dialog's stale result must not affect a new session.
        sdk.OpenAI.return_value.__enter__.return_value.models.list.side_effect = None
        with patch.dict("sys.modules", {"openai": sdk}):
            dialog.test_connection()
            self.wait_for(lambda: not dialog._connection_pending)
        self.successes.assert_called_once()

    def test_reopen_ignores_old_completion_while_new_request_is_pending(self):
        self.write_config("自定义")
        dialog = self.open_dialog()
        entered = [threading.Event(), threading.Event()]
        release = [threading.Event(), threading.Event()]
        sdk = MagicMock()
        clients = [MagicMock(), MagicMock()]
        for index, client in enumerate(clients):
            client.__enter__.return_value = client
            def block(i=index):
                entered[i].set()
                release[i].wait(2)
            client.models.list.side_effect = block
        sdk.OpenAI.side_effect = clients
        with patch.dict("sys.modules", {"openai": sdk}):
            dialog.show()
            dialog.test_connection()
            self.wait_for(entered[0].is_set)
            self.assertFalse(dialog.apiKeyEdit.isEnabled())
            dialog.reject()
            dialog.show()
            dialog.test_connection()
            self.wait_for(entered[1].is_set)
            release[0].set()
            self.wait_for(lambda: QThreadPool.globalInstance().activeThreadCount() == 1)
            QTest.qWait(20)
            self.assertTrue(dialog._connection_pending)
            self.successes.assert_not_called()
            release[1].set()
            self.wait_for(lambda: not dialog._connection_pending)
        self.successes.assert_called_once()
        self.assertTrue(dialog.apiKeyEdit.isEnabled())

    def test_deleting_dialog_while_request_runs_is_safe(self):
        self.write_config("自定义")
        dialog = self.open_dialog()
        entered, release = threading.Event(), threading.Event()
        sdk = MagicMock()
        def block():
            entered.set()
            release.wait(2)
        sdk.OpenAI.return_value.__enter__.return_value.models.list.side_effect = block
        with patch.dict("sys.modules", {"openai": sdk}):
            dialog.test_connection()
            self.wait_for(entered.is_set)
            dialog.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            self.dialogs.remove(dialog)
            release.set()
            self.wait_for(lambda: QThreadPool.globalInstance().activeThreadCount() == 0)
            QTest.qWait(20)
        self.successes.assert_not_called()
        self.errors.assert_not_called()

    def test_timeout_restores_button_and_closes_client(self):
        self.write_config("自定义")
        dialog = self.open_dialog()
        sdk = MagicMock()
        sdk.OpenAI.return_value.__enter__.return_value.models.list.side_effect = TimeoutError("timed out")
        with patch.dict("sys.modules", {"openai": sdk}):
            dialog.test_connection()
            self.wait_for(lambda: not dialog._connection_pending)
        self.assertTrue(dialog.testButton.isEnabled())
        self.assertIn("timed out", self.errors.call_args.kwargs["content"])
        sdk.OpenAI.return_value.__exit__.assert_called_once()

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
        sdk.OpenAI.return_value.__enter__.return_value = sdk.OpenAI.return_value
        with patch.dict("sys.modules", {"openai": sdk}):
            dialog.testButton.click()
            self.wait_for(lambda: not dialog._connection_pending)
        sdk.OpenAI.assert_called_once_with(api_key="test-only-key", base_url="https://example.invalid/v1", timeout=10.0, max_retries=0)
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
        sdk.OpenAI.return_value.__enter__.return_value = sdk.OpenAI.return_value
        sdk.OpenAI.return_value.models.list.side_effect = RuntimeError("404 models endpoint")
        with patch.dict("sys.modules", {"openai": sdk}):
            dialog.test_connection()
            self.wait_for(lambda: not dialog._connection_pending)
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
