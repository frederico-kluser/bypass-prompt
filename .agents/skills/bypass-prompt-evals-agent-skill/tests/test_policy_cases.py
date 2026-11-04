# -*- coding: utf-8 -*-
"""Offline-only tests for request-policy fixtures; no harmful completions."""
from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defensive_api as api
import defensive_lab as lab
import policy_cases as policy


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.corpus = policy.load_corpus()

    def test_sixty_unique_cases_in_ten_categories(self):
        cases = self.corpus["cases"]
        self.assertEqual(len(cases), 60)
        self.assertEqual(len(self.corpus["categories"]), 10)
        self.assertEqual(len({c["id"] for c in cases}), 60)
        self.assertEqual(len({c["request"].casefold() for c in cases}), 60)
        self.assertTrue(all(sum(c["category"] == category for c in cases) == 6 for category in self.corpus["categories"]))

    def test_reference_counts_are_computed_not_quality_metrics(self):
        summary = policy.summarize(self.corpus, self.corpus["cases"])
        self.assertEqual(summary["expected_actions"], {"refuse": 27, "answer": 19, "clarify": 9, "safety_support": 5})
        self.assertEqual(summary["explicit_harm_requests"], 29)
        self.assertFalse(summary["human_gold"])
        self.assertNotIn("accuracy", summary)
        self.assertEqual(summary["scope"], "classification-only")

    def test_crisis_is_not_equated_to_harmful_intent_or_bare_refusal(self):
        crises = [c for c in self.corpus["cases"] if c["slice"] == "crisis"]
        self.assertEqual(len(crises), 5)
        self.assertTrue(all(c["expected"]["response_action"] == "safety_support" for c in crises))
        self.assertEqual(sum(c["expected"]["explicit_harm_request"] for c in crises), 2)

    def test_pentest_has_legitimate_controls_and_uncertain_authorization(self):
        cases = policy.select_cases(self.corpus, categories=["pentest"])
        self.assertEqual(len(cases), 6)
        self.assertEqual({c["expected"]["response_action"] for c in cases}, {"refuse", "answer", "clarify"})

    def test_provenance_is_literal_ai_and_pending_human_review(self):
        self.assertEqual(self.corpus["provenance"]["origin"], "ai")
        self.assertIs(self.corpus["provenance"]["humanReviewed"], False)
        for field, value in (("origin", "human"), ("humanReviewed", True)):
            data = copy.deepcopy(self.corpus)
            data["provenance"][field] = value
            with self.subTest(field=field), self.assertRaises(api.LabError):
                policy.validate_corpus(data)

    def test_unknown_or_executable_fields_rejected(self):
        for key in ("payload", "code", "target_url", "tools", "models"):
            data = copy.deepcopy(self.corpus)
            data["cases"][0][key] = "outside-schema"
            with self.subTest(key=key), self.assertRaises(api.LabError):
                policy.validate_corpus(data)

    def test_duplicate_id_and_request_rejected(self):
        for field in ("id", "request"):
            data = copy.deepcopy(self.corpus)
            data["cases"][1][field] = data["cases"][0][field]
            with self.subTest(field=field), self.assertRaises(api.LabError):
                policy.validate_corpus(data)

    def test_reference_bool_and_slice_consistency(self):
        for field, value in (("explicit_harm_request", 1), ("explicit_harm_request", False), ("response_action", "answer")):
            data = copy.deepcopy(self.corpus)
            data["cases"][0]["expected"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(api.LabError):
                policy.validate_corpus(data)

    def test_json_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory(prefix="policy-json-offline-") as temp:
            path = Path(temp) / "duplicate.json"
            path.write_text('{"scope":"classification-only","scope":"changed"}', encoding="utf-8")
            with self.assertRaises(api.LabError):
                policy.load_json(path)

    def test_filters_intersect_reproducibly_without_duplicate_cases(self):
        first = policy.select_cases(self.corpus, categories=["pentest", "armas", "pentest"], actions=["refuse"])
        second = policy.select_cases(self.corpus, categories=["armas", "pentest"], slices=["disallowed"])
        self.assertEqual(first, second)
        self.assertEqual(len(first), 6)
        first[0]["request"] = "changed in detached result"
        self.assertNotEqual(first[0]["request"], self.corpus["cases"][0]["request"])

    def test_unknown_and_empty_filters_fail_closed(self):
        for kwargs in ({"categories": ["absent"]}, {"actions": ["always-comply"]}, {"categories": "pentest"}, {"categories": ["armas"], "slices": ["crisis"]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(api.LabError):
                policy.select_cases(self.corpus, **kwargs)


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="policy-packet-offline-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "new-packet"
        self.corpus = policy.load_corpus()
        self.cases = self.corpus["cases"]

    def export(self, **kwargs):
        return policy.export_packet(self.directory, self.corpus, self.cases, budget="0.10", **kwargs)

    def test_export_does_not_instantiate_client_or_generate_responses(self):
        with patch.object(api, "DefensiveAPI", side_effect=AssertionError("network/client forbidden")):
            result = self.export()
            self.assertEqual(result["paid_calls"], 0)
            self.assertTrue(policy.verify_packet(self.directory)["ok"])
        manifest = policy.load_json(self.directory / "manifest.json")
        self.assertFalse(manifest["generation_enabled"])
        self.assertFalse(manifest["collect_supported"])
        self.assertFalse(manifest["human_gold"])

    def test_jev_only_annotation_config_keeps_references_out_of_state(self):
        self.export()
        config = policy.load_json(self.directory / "jev-policy.json")
        self.assertEqual(config["models"], {"decision": ["typesafe/jev-1.13"]})
        self.assertEqual(config["mode"], "eval")
        self.assertFalse(config["fit"])
        self.assertEqual(config["repeats"], 1)
        self.assertEqual(config["split"]["holdoutRatio"], 0)
        for case in config["cases"]:
            self.assertEqual(case["expected"], {})
            self.assertEqual(set(case["state"]), {"request", "application_policy"})
            self.assertEqual(len(case["id"]), 24)
            self.assertEqual(case["provenance"], self.corpus["provenance"])
            for field in ("expected", "rationale", "safe_alternative", "category", "slice", "human_gold"):
                self.assertNotIn(field, case["state"])
        refs = policy.load_json(self.directory / "references.json")
        self.assertEqual(len(refs["references"]), 60)
        self.assertFalse(refs["human_gold"])
        self.assertEqual(refs["provenance"]["origin"], "ai")

    def test_versions_explicit_without_model_fallback(self):
        for model in policy.MODELS:
            config = policy.build_config(self.corpus, self.cases, budget="0.10", model=model)
            self.assertEqual(config["models"], {"decision": [model]})
        with self.assertRaises(api.LabError):
            policy.build_config(self.corpus, self.cases, budget="0.1", model="openrouter/auto")

    def test_invalid_budget_creates_no_output(self):
        for cap in ("0", "NaN", "Infinity", "-1", "1e10000", "1e-10000", True):
            with self.subTest(cap=cap), self.assertRaises(api.LabError):
                policy.export_packet(self.directory, self.corpus, self.cases, budget=cap)
            self.assertFalse(self.directory.exists())

    def test_export_never_overwrites_existing_experience(self):
        self.export()
        before = (self.directory / "manifest.json").read_bytes()
        with self.assertRaises(api.LabError):
            self.export()
        self.assertEqual((self.directory / "manifest.json").read_bytes(), before)

    def test_references_and_provenance_are_covered_by_own_hashes(self):
        self.export()
        path = self.directory / "references.json"
        refs = policy.load_json(path)
        refs["provenance"]["humanReviewed"] = True
        path.write_text(json.dumps(refs), encoding="utf-8")
        with self.assertRaises(api.LabError) as error:
            policy.verify_packet(self.directory)
        self.assertEqual(error.exception.code, "policy.integrity")

    def test_configuration_tampering_rejected(self):
        self.export()
        path = self.directory / "jev-policy.json"
        config = policy.load_json(path)
        config["models"]["llm"] = [{"modelId": "some/llm"}]
        path.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaises(api.LabError):
            policy.verify_packet(self.directory)

    def test_foreign_selection_cannot_claim_source_corpus(self):
        changed = copy.deepcopy(self.cases)
        changed[0]["rationale"] = "A different reference curator."
        with self.assertRaises(api.LabError):
            policy.export_packet(self.directory, self.corpus, changed, budget="0.1")
        self.assertFalse(self.directory.exists())

    def test_malformed_manifest_fails_with_actionable_error(self):
        self.export()
        (self.directory / "manifest.json").write_text('"invalid-manifest"', encoding="utf-8")
        with self.assertRaises(api.LabError) as error:
            policy.verify_packet(self.directory)
        self.assertEqual(error.exception.code, "policy.manifest")

    def test_scope_barrier_blocks_policy_packet_from_old_glm_collector(self):
        self.export()
        with patch.object(api, "DefensiveAPI", side_effect=AssertionError("GLM must never see policy corpus")):
            with self.assertRaises(api.LabError) as error:
                lab.collect(self.directory, "original", budget="1", live=True)
        self.assertEqual(error.exception.code, "lab.scope")

    def test_old_benign_corpus_still_frozen(self):
        # Corpus v2 grows, but the historical v1 slice (first 24 cases) stays
        # byte-identical so registered manifests remain interpretable.
        cases = lab.synthetic_cases()
        self.assertEqual(len(cases), 48)
        self.assertEqual(api.digest(cases[:24]), "f7f567e6cec12c82fdefe601ff301f032464e6d06bdcc37a1138c8528cec0542")

    def test_review_document_escapes_markdown_commands_and_images(self):
        cases = copy.deepcopy(self.cases[:1])
        cases[0]["request"] = '![external](https://example.invalid) | <img src="x"> `text`'
        result = policy.render_review(self.corpus, cases)
        self.assertNotIn("![external]", result)
        self.assertNotIn("<img", result)
        self.assertIn("\\!\\[external\\]", result)

    def test_cli_list_and_export_are_offline(self):
        stream = io.StringIO()
        with patch.object(api, "DefensiveAPI", side_effect=AssertionError("network forbidden")), redirect_stdout(stream):
            self.assertEqual(lab.main(["policy-cases", "--list", "--category", "armas"]), 0)
        self.assertEqual(json.loads(stream.getvalue())["cases"], 6)
        stream = io.StringIO()
        with patch.object(api, "DefensiveAPI", side_effect=AssertionError("network forbidden")), redirect_stdout(stream):
            self.assertEqual(lab.main(["policy-cases", "--out-dir", str(self.directory), "--budget", "0.10", "--category", "pentest"]), 0)
        self.assertEqual(json.loads(stream.getvalue())["cases"], 6)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(lab.main(["policy-cases", "--verify", str(self.directory)]), 0)

    def test_cli_export_requires_budget_without_asking_for_key(self):
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            self.assertEqual(lab.main(["policy-cases", "--out-dir", str(self.directory)]), 1)
        self.assertFalse(self.directory.exists())


if __name__ == "__main__":
    unittest.main()
