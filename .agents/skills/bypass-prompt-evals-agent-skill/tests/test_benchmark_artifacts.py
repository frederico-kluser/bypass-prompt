# -*- coding: utf-8 -*-
"""Integrity and interpretation tests for the recorded benchmarks (offline)."""
from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks"
REGISTRY = BENCH / "registry.json"


def load(path):
    with Path(path).open(encoding="utf-8-sig") as source:
        return json.load(source)


class BenchmarkRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = load(REGISTRY)

    def test_registry_is_valid_and_names_the_benchmarks(self):
        self.assertEqual(self.registry["format"], "bypass-prompt-benchmarks@1")
        ids = {benchmark["id"] for benchmark in self.registry["benchmarks"]}
        self.assertEqual(ids, {"defensive-prompt-lab-v1", "policy-risk-classification-v1",
                               "legacy-harness-selftest", "prompt-builder-adapter-offline",
                               "python-offline-suites"})
        for benchmark in self.registry["benchmarks"]:
            self.assertFalse(benchmark["human_gold"])
            self.assertIn(benchmark["status"], {"executed", "exported-not-executed", "offline-suite"})

    def test_every_recorded_hash_matches_the_artifact(self):
        for benchmark in self.registry["benchmarks"]:
            for relative, expected in benchmark.get("files", {}).items():
                path = ROOT / relative
                with self.subTest(path=relative):
                    self.assertTrue(path.is_file(), "artefacto em falta: " + relative)
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    self.assertEqual(digest, expected)

    def test_no_credentials_or_private_keys_in_recorded_evidence(self):
        pattern = re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[opusr]_[A-Za-z0-9]{30,}")
        for benchmark in self.registry["benchmarks"]:
            for relative in benchmark.get("files", {}):
                text = (ROOT / relative).read_text(encoding="utf-8", errors="ignore")
                with self.subTest(path=relative):
                    self.assertIsNone(pattern.search(text), "credencial aparente em " + relative)


class RecordedBenchmarkTests(unittest.TestCase):
    def test_defensive_lab_result_is_preserved_with_its_limits(self):
        comparison = load(BENCH / "defensive-lab-20261104" / "comparison.json")
        self.assertFalse(comparison["human_gold"])
        self.assertEqual(comparison["judge"], "typesafe/jev-1.13")
        self.assertEqual(comparison["judge_run"]["snapshots"], ["typesafe/jev-1.13-20260917"])
        benign = comparison["slices"]["benign"]
        conflict = comparison["slices"]["document-conflict"]
        self.assertEqual(benign["decisive_pairs"] + conflict["decisive_pairs"], 20)
        self.assertEqual(benign["planned_pairs"] + conflict["planned_pairs"], 24)
        for slice_name in ("benign", "document-conflict"):
            self.assertEqual(comparison["slices"][slice_name]["utility_delta_pp"], 0.0)
            self.assertEqual(comparison["slices"][slice_name]["improved_pairs"], 0)
            self.assertEqual(comparison["slices"][slice_name]["regressed_pairs"], 0)
        self.assertIn("sem ouro humano independente", " ".join(comparison["limitations"]))
        self.assertEqual(comparison["collection"]["original"]["complete_responses"], 24)
        self.assertEqual(comparison["collection"]["revised"]["complete_responses"], 24)

    def test_defensive_lab_report_and_cost_are_consistent(self):
        diagnostics = load(BENCH / "defensive-lab-20261104" / "diagnostics.json")
        self.assertEqual(diagnostics["cost_usd"]["total"], "0.0210912759999999997")
        self.assertEqual(diagnostics["collection_cost_delta_percent"], "58.18270835651496606208968510")
        report = (BENCH / "defensive-lab-20261104" / "relatorio-final.md").read_text(encoding="utf-8")
        self.assertIn("Manter o prompt original", report)
        self.assertIn("20 / 24", report)
        self.assertIn("não foi promovida", report)

    def test_jev_record_is_decision_only_and_matches_the_config(self):
        record = load(BENCH / "defensive-lab-20261104" / "jev-run.json")
        self.assertEqual(record["format"], "jev-run@1")
        self.assertEqual(record["mode"], "eval")
        self.assertEqual(len(record["contestants"]), 1)
        contestant = record["contestants"][0]
        self.assertEqual(contestant["kind"], "decision")
        self.assertEqual(contestant["modelId"], "typesafe/jev-1.13")
        self.assertNotIn("llm", record.get("config", {}).get("models", {}))
        self.assertEqual(record["status"], "finished")
        self.assertEqual(record["incompleteCaseIds"], [])
        self.assertEqual(len(record["cells"]), 48)
        self.assertTrue(all(cell["status"] == "ok" for cell in record["cells"]))

    def test_policy_corpus_keeps_agent_references_and_counts(self):
        corpus = load(BENCH / "policy-risk-20261104" / "cases.json")
        self.assertEqual(corpus["format"], "defensive-policy-cases@1")
        self.assertEqual(corpus["scope"], "classification-only")
        self.assertEqual(corpus["provenance"]["origin"], "ai")
        self.assertIs(corpus["provenance"]["humanReviewed"], False)
        self.assertEqual(len(corpus["cases"]), 60)
        self.assertEqual(len(corpus["categories"]), 10)
        actions = {"refuse": 0, "answer": 0, "clarify": 0, "safety_support": 0}
        for case in corpus["cases"]:
            actions[case["expected"]["response_action"]] += 1
        self.assertEqual(actions, {"refuse": 27, "answer": 19, "clarify": 9, "safety_support": 5})
        references = load(BENCH / "policy-risk-20261104" / "references.json")
        self.assertEqual(len(references["references"]), 60)
        self.assertFalse(references["human_gold"])

    def test_policy_jev_config_is_annotation_only(self):
        config = load(BENCH / "policy-risk-20261104" / "jev-policy.json")
        self.assertEqual(config["models"], {"decision": ["typesafe/jev-1.13"]})
        self.assertIs(config["fit"], False)
        self.assertEqual(config["repeats"], 1)
        self.assertEqual(len(config["cases"]), 60)
        for case in config["cases"]:
            self.assertEqual(case["expected"], {})
            self.assertEqual(set(case["state"]), {"request", "application_policy"})
            for field in ("rationale", "safe_alternative", "category", "slice", "response_action"):
                self.assertNotIn(field, case["state"])


if __name__ == "__main__":
    unittest.main()
