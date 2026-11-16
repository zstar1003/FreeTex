"""Isolated production-method tests; no model imports, files or network calls."""
import ast
import json
import logging
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, mock_open, patch

ROOT = Path(__file__).resolve().parents[1]


def method(path, name, namespace):
    # Compile the actual method unchanged while excluding startup/model imports.
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    node = next(node for cls in tree.body if isinstance(cls, ast.ClassDef)
                for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


class RecognitionRoutingTest(unittest.TestCase):
    def setUp(self):
        self.torch = MagicMock()
        self.process = method("tools/local_processor.py", "process_pixmap", {
            "json": json, "sys": sys, "os": os, "torch": self.torch,
            "read_config": lambda: json.load(open("mock-config.json")),
            "__file__": str(ROOT / "tools/local_processor.py")
        })
        self.processor = SimpleNamespace(
            model=MagicMock(), vis_processor=MagicMock(), device="cpu",
            logger=logging.getLogger("test"), finished=MagicMock(),
            preprocess_image=MagicMock(return_value=object()),
            _pixmap_to_pil=MagicMock(return_value=object()),
            _process_with_multimodal=MagicMock(return_value="cloud-result")
        )
        self.processor.model.generate.return_value = {"pred_str": ["local-result"]}

    def run_config(self, config):
        with patch("builtins.open", mock_open(read_data=json.dumps(config))):
            self.process(self.processor, object())

    def test_cloud_does_not_require_local_model(self):
        self.processor.model = self.processor.vis_processor = None
        self.run_config({"model_config": {"enabled": True}})
        self.processor.finished.emit.assert_called_once_with("cloud-result")

    def test_cloud_error_is_visible_without_local_fallback(self):
        self.processor._process_with_multimodal.side_effect = RuntimeError("provider rejected request")
        self.run_config({"model_config": {"enabled": True}})
        self.processor.finished.emit.assert_called_once_with("识别失败: provider rejected request")
        self.processor.model.generate.assert_not_called()
        self.processor.vis_processor.assert_not_called()

    def test_local_mode_still_uses_local_model(self):
        self.run_config({"model_config": {"enabled": False}})
        self.processor.finished.emit.assert_called_once_with("local-result")
        self.processor._process_with_multimodal.assert_not_called()

    def test_local_missing_model_is_error(self):
        self.processor.model = None
        self.run_config({})
        self.assertTrue(self.processor.finished.emit.call_args.args[0].startswith("识别失败:"))
        self.processor._process_with_multimodal.assert_not_called()

    def test_invalid_config_does_not_silently_choose_local(self):
        with patch("builtins.open", mock_open(read_data="invalid json")):
            self.process(self.processor, object())
        self.assertTrue(self.processor.finished.emit.call_args.args[0].startswith("识别失败:"))
        self.processor.model.generate.assert_not_called()
        self.processor._process_with_multimodal.assert_not_called()

    def test_unreadable_config_is_visible_without_backend_call(self):
        with patch("builtins.open", side_effect=OSError("config unavailable")):
            self.process(self.processor, object())
        self.processor.finished.emit.assert_called_once_with("识别失败: config unavailable")
        self.processor.model.generate.assert_not_called()
        self.processor._process_with_multimodal.assert_not_called()

    def test_image_conversion_failure_has_error_prefix(self):
        self.processor._pixmap_to_pil.return_value = None
        self.run_config({"model_config": {"enabled": True}})
        self.processor.finished.emit.assert_called_once_with("识别失败: 图像转换失败")
        self.processor._process_with_multimodal.assert_not_called()


class RecognitionUiTest(unittest.TestCase):
    def test_error_is_not_rendered_or_announced_as_success(self):
        render, tooltip = MagicMock(), MagicMock()
        callback = method("main.py", "on_recognition_finished", {
            "render_latex_to_html": render, "StateToolTip": tooltip
        })
        view = MagicMock()
        view.width.return_value = 800
        tooltip.return_value.width.return_value = 100
        view.current_latex = "old-result"
        callback(view, "识别失败: provider error")
        render.assert_not_called()
        view.latexEdit.setText.assert_called_once_with("识别失败: provider error")
        view.update_copy_button_state.assert_called_once()
        self.assertEqual(view.current_latex, "")
        tooltip.return_value.setState.assert_called_once_with(False)
        state = method("main.py", "update_copy_button_state", {})
        view.latexEdit.toPlainText.return_value = "识别失败: provider error"
        view.latexEdit.placeholderText.return_value = "placeholder"
        state(view)
        view.copyButton.setEnabled.assert_called_once_with(False)
        view.copyWordButton.setEnabled.assert_called_once_with(False)

    def test_success_still_renders_and_announces_success(self):
        render, tooltip = MagicMock(return_value="html"), MagicMock()
        callback = method("main.py", "on_recognition_finished", {
            "render_latex_to_html": render, "StateToolTip": tooltip
        })
        view = MagicMock()
        view.width.return_value = 800
        tooltip.return_value.width.return_value = 100
        callback(view, "x^2")
        render.assert_called_once_with("x^2")
        tooltip.return_value.setState.assert_called_once_with(True)
        self.assertEqual(view.current_latex, "x^2")

    def test_display_dispatches_without_local_model(self):
        callback = method("main.py", "display_result_pixmap", {"QPixmap": MagicMock()})
        view, pixmap = MagicMock(), MagicMock()
        view.local_processor.model = None
        pixmap.isNull.return_value = False
        callback(view, pixmap)
        view.process_request.emit.assert_called_once_with(pixmap)

    def test_local_load_failure_keeps_recognition_inputs_available(self):
        tooltip = MagicMock()
        tooltip.return_value.width.return_value = 100
        callback = method("main.py", "on_model_loading_finished", {"StateToolTip": tooltip})
        view = MagicMock()
        view.width.return_value = 800
        callback(view, "加载失败 (cpu)")
        view.uploadButton.setEnabled.assert_called_once_with(True)
        view.screenshotButton.setEnabled.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
