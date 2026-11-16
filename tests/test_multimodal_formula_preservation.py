"""Offline synthetic regressions, not a benchmark of model recognition accuracy."""
import base64
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from test_recognition_routing import method


class MultimodalFormulaPreservationTest(unittest.TestCase):
    def setUp(self):
        self.recognize = method("tools/local_processor.py", "_process_with_multimodal", {})
        self.sdk = MagicMock()
        self.image = MagicMock()
        # Deliberately not contributor imagery; the transport is fully mocked.
        self.image.save.side_effect = lambda stream, format: stream.write(b"synthetic-image-bytes")
        self.config = {"api_key": "synthetic-key", "api_url": "https://example.invalid/v1",
                       "model_name": "synthetic-vision-model", "system_prompt": "synthetic prompt"}

    def result_for(self, latex):
        self.sdk.OpenAI.return_value.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=latex))])
        with patch.dict("sys.modules", {"openai": self.sdk}):
            return self.recognize(SimpleNamespace(), self.image, self.config)

    def test_nested_fractions_summation_limits_and_indices_are_preserved(self):
        # Original synthetic formula, not a transcription/ground truth for #37.
        latex = r"F(z)=\frac{1}{\sum_{k=2}^{m}\frac{a_k}{B}\frac{\sum_{p\ne q}c_{pq}^{r}}{m(m+1)}}"
        self.assertEqual(self.result_for(latex), latex)

    def test_whitespace_normalization_does_not_remove_sum_limits(self):
        latex = "  \\frac{1}{\\sum_{k=2}^{m} x_k}\n  "
        self.assertEqual(self.result_for(latex), latex.strip())

    def test_missing_limit_is_not_invented_by_postprocessing(self):
        latex = r"\frac{1}{\sum x_k}"
        self.assertEqual(self.result_for(latex), latex)

    def test_selected_model_prompt_and_image_use_chat_endpoint(self):
        self.result_for("x")
        self.sdk.OpenAI.assert_called_once_with(api_key="synthetic-key", base_url="https://example.invalid/v1")
        client = self.sdk.OpenAI.return_value
        client.models.list.assert_not_called()
        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["model"], self.config["model_name"])
        self.assertEqual(request["messages"][0]["content"], "synthetic prompt")
        image = request["messages"][1]["content"][0]["image_url"]["url"]
        self.assertEqual(image, "data:image/png;base64," + base64.b64encode(b"synthetic-image-bytes").decode())
        self.assertEqual(request["max_tokens"], 1024)
        self.assertEqual(request["temperature"], 0.2)


if __name__ == "__main__":
    unittest.main()
