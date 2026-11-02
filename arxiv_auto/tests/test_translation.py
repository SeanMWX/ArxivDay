import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from openai import (
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
)


translation = importlib.import_module("arxiv_auto.arxiv_auto")


def completion(content="中文翻译", finish_reason="stop"):
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1,
        "model": "gpt-5.6-luna",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content},
            }
        ],
    }


class TranslationTests(unittest.TestCase):
    def make_model(self, responses, **kwargs):
        """Exercise SDK serialization and errors without making network calls."""
        requests = []
        remaining_responses = iter(responses)

        def handle(request):
            requests.append(json.loads(request.content))
            status, payload = next(remaining_responses)
            return httpx.Response(status, json=payload)

        client = OpenAI(
            api_key="test-key",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handle)),
        )
        self.addCleanup(client.close)
        with patch.object(translation, "OpenAI", return_value=client) as factory:
            model = translation.ChatGPTModel(api_key="test-key", **kwargs)
        factory.assert_called_once_with(
            api_key="test-key", max_retries=0, timeout=60.0
        )
        return model, requests

    def make_config(self, text):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "config.ini"
        path.write_text(text, encoding="utf-8")
        return translation.Config(str(path))

    def test_default_request_uses_supported_parameters_and_returns_trimmed_text(self):
        model, requests = self.make_model([(200, completion("  标题译文\n"))])

        self.assertEqual(model.prompt("Translate this title"), "标题译文")

        self.assertEqual(
            requests,
            [
                {
                    "model": "gpt-5.6-luna",
                    "messages": [
                        {"role": "user", "content": "Translate this title"}
                    ],
                    "max_completion_tokens": 2000,
                    "reasoning_effort": "none",
                }
            ],
        )

    def test_can_omit_reasoning_and_explicitly_set_temperature_and_token_limit(self):
        model, requests = self.make_model(
            [(200, completion())],
            model="custom-model",
            reasoning_effort=None,
        )

        model.prompt("Translate", temperature=0.2, max_tokens=128)

        self.assertEqual(requests[0]["model"], "custom-model")
        self.assertEqual(requests[0]["temperature"], 0.2)
        self.assertEqual(requests[0]["max_completion_tokens"], 128)
        self.assertNotIn("reasoning_effort", requests[0])
        self.assertNotIn("max_tokens", requests[0])

    def test_old_config_without_model_uses_new_defaults(self):
        config = self.make_config("[chatgpt]\napi_key=test-key\n")

        self.assertEqual(config.chatgpt_model(), "gpt-5.6-luna")
        self.assertEqual(config.reasoning_effort(), "none")

    def test_config_selects_model_and_reasoning_effort(self):
        config = self.make_config(
            "[chatgpt]\napi_key=test-key\n"
            "model=gpt-5.6-terra\nreasoning_effort=low\n"
        )

        self.assertEqual(config.chatgpt_model(), "gpt-5.6-terra")
        self.assertEqual(config.reasoning_effort(), "low")

    def test_empty_reasoning_setting_disables_request_parameter(self):
        config = self.make_config(
            "[chatgpt]\napi_key=test-key\nreasoning_effort=\n"
        )

        self.assertIsNone(config.reasoning_effort())

    def test_empty_and_incomplete_responses_are_rejected(self):
        cases = [
            (None, "stop"),
            ("", "stop"),
            (" \n", "stop"),
            ("被截断的翻译", "length"),
            ("过滤后的翻译", "content_filter"),
        ]
        for content, finish_reason in cases:
            with self.subTest(content=content, finish_reason=finish_reason):
                model, _ = self.make_model(
                    [(200, completion(content, finish_reason))]
                )
                with self.assertRaises(ValueError):
                    model.prompt("Translate")

    def test_permanent_api_errors_propagate_without_article_retries(self):
        cases = [
            (400, BadRequestError, "invalid_request_error"),
            (401, AuthenticationError, "invalid_api_key"),
            (403, PermissionDeniedError, "permission_denied"),
            (404, NotFoundError, "model_not_found"),
        ]
        for status, error_type, code in cases:
            with self.subTest(status=status):
                model, requests = self.make_model(
                    [
                        (
                            status,
                            {
                                "error": {
                                    "message": "The configured model is unavailable",
                                    "type": "invalid_request_error",
                                    "code": code,
                                }
                            },
                        )
                    ]
                )
                article = translation.Article(title="Title", summary="Summary")

                with self.assertRaises(error_type) as context:
                    article.gpt_CN_translate(model)

                self.assertEqual(context.exception.status_code, status)
                self.assertEqual(context.exception.code, code)
                self.assertEqual(len(requests), 1)

    def test_transient_error_retries_and_recovers(self):
        model, requests = self.make_model(
            [
                (500, {"error": {"message": "Temporary server failure"}}),
                (200, completion("标题译文")),
                (200, completion("摘要译文")),
            ]
        )
        article = translation.Article(title="Title", summary="Summary")

        self.assertTrue(article.gpt_CN_translate(model))

        self.assertEqual(article.CN_title, "标题译文")
        self.assertEqual(article.CN_summary, "摘要译文")
        self.assertEqual(len(requests), 3)

    def test_transient_error_stops_after_three_attempts(self):
        model, requests = self.make_model(
            [(500, {"error": {"message": "Temporary server failure"}})] * 3
        )
        article = translation.Article(title="Title", summary="Summary")

        self.assertFalse(article.gpt_CN_translate(model))

        self.assertEqual(len(requests), 3)

    def test_batch_uses_configured_model_and_excludes_incomplete_translation(self):
        model, requests = self.make_model(
            [
                (200, completion("标题译文")),
                (200, completion("摘要被截断", "length")),
                (200, completion("摘要被截断", "length")),
                (200, completion("摘要被截断", "length")),
            ],
            model="gpt-5.6-terra",
            reasoning_effort="low",
        )
        config = Mock()
        config.api_key.return_value = "test-key"
        config.chatgpt_model.return_value = "gpt-5.6-terra"
        config.reasoning_effort.return_value = "low"
        config.db_config.return_value = {"database": "test"}
        article = translation.Article(
            entry_id="https://arxiv.org/abs/test", title="Title", summary="Summary"
        )

        with (
            patch.object(translation, "Config", return_value=config),
            patch.object(translation, "ChatGPTModel", return_value=model) as factory,
            patch.object(translation, "Database") as database,
            patch.object(translation, "fetch_recent_articles", return_value=[article]),
            patch.object(translation, "insert_articles_to_database") as insert,
        ):
            database.return_value.article_exists.return_value = False

            translation.fetch_process_insert_articles("cs.AI", "articles", 3)

        factory.assert_called_once_with(
            api_key="test-key", model="gpt-5.6-terra", reasoning_effort="low"
        )
        self.assertEqual(len(requests), 4)
        for call in insert.call_args_list:
            self.assertNotIn(article, call.args[0])


if __name__ == "__main__":
    unittest.main()
