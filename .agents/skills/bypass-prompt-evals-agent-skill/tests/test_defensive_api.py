# -*- coding: utf-8 -*-
"""Offline tests: all model replies/transports are synthetic, no API calls."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defensive_api as api


def catalog():
    return {"model": {"id": api.MODEL, "canonical_slug": "z-ai/glm-5.3-flash-20260826",
                      "reasoning": {"supported_efforts": ["max", "high", "low"]}},
            "endpoints": {"endpoints": [{"tag": api.PROVIDER, "pricing": {"prompt": "0.00000015", "completion": "0.0000005"},
                                           "supported_parameters": sorted(api.REQUIRED_PARAMETERS),
                                           "context_length": 1048576, "max_completion_tokens": 131072}]}}


def reply(text="Resumo sintético.", *, cost="0.0001", finish="stop", model=api.MODEL):
    return {"model": model, "id": "gen-test", "provider": "Z.AI",
            "choices": [{"finish_reason": finish, "message": {"role": "assistant", "content": text}}],
            "usage": {"cost": cost, "prompt_tokens": 30, "completion_tokens": 20,
                      "completion_tokens_details": {"reasoning_tokens": 12}}}


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses) or [(200, {}, reply())]
        self.calls = []

    def __call__(self, method, path, body, key, timeout):
        self.calls.append((method, path, copy.deepcopy(body), key, timeout))
        status, headers, value = self.responses.pop(0)
        return status, headers, value if isinstance(value, bytes) else json.dumps(value).encode()


def client(transport=None, **kwargs):
    c = api.DefensiveAPI("0.10", key="local-test-key-not-a-secret", transport=transport or FakeTransport(), **kwargs)
    c.load_catalog(catalog())
    return c


class MoneyTests(unittest.TestCase):
    def test_invalid_money(self):
        for value in (True, False, None, "bad", "NaN", "Infinity", -1, float("nan")):
            with self.subTest(value=value), self.assertRaises(api.LabError):
                api.money(value)

    def test_positive_budget_required(self):
        with self.assertRaises(api.LabError):
            api.Budget(Decimal("0"))

    def test_budget_blocks_before_attempt(self):
        b = api.Budget(Decimal("0.01"))
        with self.assertRaises(api.LabError):
            b.reserve(Decimal("0.02"))
        self.assertEqual(b.attempts, 0)

    def test_unknown_cost_retains_reservation(self):
        b = api.Budget(Decimal("0.01"))
        b.reserve(Decimal("0.001"))
        self.assertIsNone(b.settle(Decimal("0.001"), {}))
        self.assertFalse(b.snapshot()["cost_exact"])
        self.assertEqual(b.uncertain, Decimal("0.001"))

    def test_cost_overrun_recorded_and_rejected(self):
        b = api.Budget(Decimal("0.01"))
        b.reserve(Decimal("0.001"))
        with self.assertRaises(api.LabError):
            b.settle(Decimal("0.001"), {"cost": "0.02"})
        self.assertEqual(b.spent, Decimal("0.02"))


class CatalogTests(unittest.TestCase):
    def test_exact_model_required(self):
        data = catalog()
        data["model"]["id"] += "x"
        with self.assertRaises(api.LabError):
            api.validate_catalog(data["model"], data["endpoints"])

    def test_max_is_never_downgraded(self):
        data = catalog()
        data["model"]["reasoning"]["supported_efforts"] = ["high"]
        with self.assertRaises(api.LabError):
            api.validate_catalog(data["model"], data["endpoints"])

    def test_provider_must_exist_once(self):
        for endpoints in ([], catalog()["endpoints"]["endpoints"] * 2):
            with self.subTest(endpoints=endpoints), self.assertRaises(api.LabError):
                api.validate_catalog(catalog()["model"], {"endpoints": endpoints})

    def test_parameters_required(self):
        data = catalog()
        data["endpoints"]["endpoints"][0]["supported_parameters"] = ["max_tokens"]
        with self.assertRaises(api.LabError):
            api.validate_catalog(data["model"], data["endpoints"])

    def test_price_and_limits_required(self):
        for field, value in (("context_length", 0), ("max_completion_tokens", True), ("pricing", {"prompt": "NaN", "completion": "0"})):
            with self.subTest(field=field), self.assertRaises(api.LabError):
                data = catalog()
                data["endpoints"]["endpoints"][0][field] = value
                api.validate_catalog(data["model"], data["endpoints"])

    def test_public_catalog_does_not_send_key(self):
        data = catalog()
        fake = FakeTransport((200, {}, {"data": data["model"]}), (200, {}, {"data": data["endpoints"]}))
        c = api.DefensiveAPI("0.1", key="test-only", transport=fake)
        c.load_catalog()
        self.assertEqual([call[3] for call in fake.calls], ["", ""])
        self.assertEqual(c.budget.attempts, 0)

    def test_catalog_errors_do_not_retry(self):
        fake = FakeTransport((503, {}, {"error": {"code": 503}}))
        c = api.DefensiveAPI("0.1", key="test-only", transport=fake)
        with self.assertRaises(api.LabError):
            c.load_catalog()
        self.assertEqual(len(fake.calls), 1)


class RequestTests(unittest.TestCase):
    def test_fixed_model_provider_and_max_effort(self):
        body, reserve = client().prepare("Instrução defensiva.", "Documento sintético.")
        self.assertEqual(body["model"], api.MODEL)
        self.assertEqual(body["reasoning"], {"effort": "max", "exclude": True})
        self.assertEqual(body["provider"]["only"], [api.PROVIDER])
        self.assertFalse(body["provider"]["allow_fallbacks"])
        self.assertTrue(body["provider"]["require_parameters"])
        for name in ("models", "tools", "plugins", "fallbacks"):
            self.assertNotIn(name, body)
        self.assertGreater(reserve, 0)

    def test_no_catalog_no_request(self):
        c = api.DefensiveAPI("0.1", key="test-only", transport=FakeTransport())
        with self.assertRaises(api.LabError):
            c.prepare("defense", "synthetic")

    def test_dry_prepare_needs_no_key(self):
        c = client()
        c.key = ""
        c.prepare("defense", "synthetic")
        self.assertEqual(c.budget.attempts, 0)

    def test_invalid_inputs(self):
        for system, user, tokens in (("", "x", 128), ("x", " ", 128), (None, "x", 128), ("x", "x", True), ("x", "x", 10), ("x", "x", 32769)):
            with self.subTest(system=system, user=user, tokens=tokens), self.assertRaises(api.LabError):
                client().prepare(system, user, max_tokens=tokens)

    def test_context_preflight(self):
        c = client()
        c.endpoint["context_length"] = 256
        with self.assertRaises(api.LabError):
            c.prepare("defense", "synthetic")

    def test_invalid_operational_arguments(self):
        for kwargs in ({"timeout": float("nan")}, {"timeout": 0}, {"max_attempts": True}, {"max_attempts": 4}, {"provider": "bad\nheader"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(api.LabError):
                client(**kwargs)

    def test_missing_key_blocks_before_transport(self):
        fake = FakeTransport()
        c = client(fake)
        c.key = ""
        with self.assertRaises(api.LabError):
            c.complete("defense", "synthetic")
        self.assertEqual(fake.calls, [])

    def test_budget_blocks_before_transport(self):
        fake = FakeTransport()
        c = client(fake)
        c.budget.cap = Decimal("0.00000001")
        with self.assertRaises(api.LabError):
            c.complete("defense", "synthetic")
        self.assertEqual(fake.calls, [])


class ResponseTests(unittest.TestCase):
    def test_success_only_public_text_and_usage(self):
        data = reply()
        data["choices"][0]["message"]["reasoning"] = "not part of observable output"
        result = client(FakeTransport((200, {}, data))).complete("defense", "synthetic")
        self.assertEqual(result["text"], "Resumo sintético.")
        self.assertEqual(result["reasoning_tokens"], 12)
        self.assertEqual(result["cost_usd"], "0.0001")
        self.assertNotIn("reasoning", result)
        self.assertTrue(result["budget"]["cost_exact"])

    def test_missing_cost_is_unknown_not_free(self):
        data = reply()
        del data["usage"]["cost"]
        result = client(FakeTransport((200, {}, data))).complete("defense", "synthetic")
        self.assertIsNone(result["cost_usd"])
        self.assertFalse(result["budget"]["cost_exact"])
        self.assertGreater(Decimal(result["budget"]["unknown_cost_reserved_usd"]), 0)

    def test_textual_refusal_is_an_observation_not_a_retry(self):
        fake = FakeTransport((200, {}, reply("Não posso realizar essa tarefa.")))
        result = client(fake).complete("defense", "synthetic")
        self.assertIn("Não posso", result["text"])
        self.assertEqual(len(fake.calls), 1)

    def test_structured_refusal_is_terminal(self):
        data = reply()
        data["choices"][0]["message"]["refusal"] = "Refused"
        fake = FakeTransport((200, {}, data))
        with self.assertRaises(api.LabError) as error:
            client(fake).complete("defense", "synthetic")
        self.assertEqual(error.exception.code, "response.refusal")
        self.assertEqual(len(fake.calls), 1)

    def test_no_tool_execution(self):
        data = reply()
        data["choices"][0]["message"]["tool_calls"] = [{"id": "not-executed"}]
        with self.assertRaises(api.LabError) as error:
            client(FakeTransport((200, {}, data))).complete("defense", "synthetic")
        self.assertEqual(error.exception.code, "response.tools")

    def test_incomplete_and_empty_are_not_blocked_attacks(self):
        for text, finish in (("", "stop"), ("partial", "length"), ("partial", "error"), (None, "stop")):
            with self.subTest(text=text, finish=finish), self.assertRaises(api.LabError) as error:
                client(FakeTransport((200, {}, reply(text, finish=finish)))).complete("defense", "synthetic")
            self.assertEqual(error.exception.code, "response.incomplete")

    def test_unexpected_model_rejected(self):
        with self.assertRaises(api.LabError) as error:
            client(FakeTransport((200, {}, reply(model="different/model")))).complete("defense", "synthetic")
        self.assertEqual(error.exception.code, "response.model")

    def test_invalid_json_does_not_echo_remote_body(self):
        fake = FakeTransport((200, {}, b"private remote text"))
        with self.assertRaises(api.LabError) as error:
            client(fake).complete("defense", "synthetic")
        self.assertNotIn("private remote text", str(error.exception))

    def test_wrong_schema_rejected(self):
        for value in ([], {"model": api.MODEL, "choices": []}, {"model": api.MODEL, "choices": [{"message": None}]}):
            fake = FakeTransport((200, {}, value))
            with self.subTest(value=value), self.assertRaises(api.LabError):
                client(fake).complete("defense", "synthetic")


class RetryTests(unittest.TestCase):
    def test_numeric_retry_after_and_same_request(self):
        waits = []
        fake = FakeTransport((429, {"Retry-After": "3"}, {"error": {"code": 429}}), (200, {}, reply()))
        c = client(fake, sleeper=waits.append)
        result = c.complete("defense", "synthetic")
        self.assertEqual(waits, [3])
        self.assertEqual(fake.calls[0][2], fake.calls[1][2])
        self.assertFalse(result["budget"]["cost_exact"])
        self.assertEqual(result["budget"]["attempts"], 2)

    def test_200_error_envelope_is_not_success(self):
        fake = FakeTransport((200, {}, {"error": {"code": 402, "metadata": {"error_type": "payment_required"}}}))
        with self.assertRaises(api.LabError) as error:
            client(fake).complete("defense", "synthetic")
        self.assertEqual(error.exception.code, "payment_required")
        self.assertEqual(len(fake.calls), 1)

    def test_terminal_statuses_never_fallback(self):
        for status in (400, 401, 402, 403, 404, 422):
            fake = FakeTransport((status, {}, {"error": {"code": status}}))
            with self.subTest(status=status), self.assertRaises(api.LabError):
                client(fake).complete("defense", "synthetic")
            self.assertEqual(len(fake.calls), 1)

    def test_policy_refusal_never_retries_even_if_503(self):
        fake = FakeTransport((503, {}, {"error": {"code": 503, "metadata": {"error_type": "refusal"}}}))
        with self.assertRaises(api.LabError):
            client(fake).complete("defense", "synthetic")
        self.assertEqual(len(fake.calls), 1)

    def test_http_date_retry_after(self):
        now = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(api.retry_delay({"retry-after": "Wed, 04 Nov 2026 12:00:05 GMT"}, 0, now), 5)

    def test_retry_after_is_not_clamped_early(self):
        with self.assertRaises(api.LabError):
            api.retry_delay({"Retry-After": "120"}, 0)

    def test_invalid_retry_hint_uses_backoff(self):
        for hint in ("bad", "NaN", "-1"):
            with self.subTest(hint=hint):
                self.assertEqual(api.retry_delay({"Retry-After": hint}, 1), 2)

    def test_redirects_are_not_forwarded(self):
        self.assertIsNone(api._NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.invalid"))


if __name__ == "__main__":
    unittest.main()
