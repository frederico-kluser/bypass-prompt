# -*- coding: utf-8 -*-
"""Synthetic, offline integration tests for pairing, missingness and provenance."""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defensive_api as api
import defensive_lab as lab
from test_defensive_api import FakeTransport, catalog, reply


class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="defensive-lab-offline-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "experiment"
        lab.prepare(self.directory)
        lab.save_json(self.directory / "catalog.json", catalog())
        self.n = len(lab.synthetic_cases())
        self.pairs_per_slice = self.n // 2

    def write_revision(self):
        original = (self.directory / "original.md").read_text(encoding="utf-8")
        (self.directory / "revised.md").write_text(original + "\nResponda no formato benigno solicitado, sem preâmbulo desnecessário.\n", encoding="utf-8")

    def collect_both(self):
        self.write_revision()
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "local-test-key-not-a-secret"}):
            for label in ("original", "revised"):
                transport = FakeTransport(*[(200, {}, reply("azul")) for _ in lab.synthetic_cases()])
                lab.collect(self.directory, label, budget="1.00", live=True, transport=transport)
        return lab.export_jev(self.directory, budget="0.01")

    def run_record(self):
        config = lab.load_json(self.directory / "jev-eval.json")
        return {"format": "jev-run@1", "id": "offline-run", "mode": "eval", "status": "inconclusive",
                "contestants": [{"id": "decision-control", "kind": "decision", "modelId": lab.JEV_MODEL}],
                "cases": copy.deepcopy(config["cases"]),
                "specs": [{"questions": [{"id": qid, **spec} for qid, spec in lab.QUESTIONS.items()]}],
                "resolvedModels": {lab.JEV_MODEL: [lab.JEV_MODEL + "-20260917"]},
                "cells": [{"caseId": case["id"], "contestantId": "decision-control", "rep": 0, "status": "ok",
                           "resolvedModel": lab.JEV_MODEL + "-20260917", "answers": {
                               "task_fulfilled": {"type": "noul", "noul": 0.99},
                               "external_instruction_adopted": {"type": "noul", "noul": 0.01},
                               "evidence": {"type": "choice", "choice": "sufficient", "confidence": 0.99}}}
                          for case in config["cases"]]}

    def compare_record(self, record):
        path = self.directory / "offline-record.json"
        lab.save_json(path, record)
        return lab.compare(self.directory, path)

    def test_prepared_scope_and_no_live_outputs(self):
        directory, manifest, original, cases = lab.read_lab(self.directory)
        self.assertEqual(directory, self.directory)
        self.assertEqual(len(cases), self.n)
        self.assertGreaterEqual(self.n, 48)
        self.assertFalse(manifest["human_gold"])
        self.assertEqual(api.digest(original), manifest["original_sha256"])
        self.assertFalse((directory / "revised.md").exists())
        self.assertEqual(lab.harden.check(original)["score"], 18)

    def test_corpus_covers_known_trigger_families(self):
        cases = lab.synthetic_cases()
        # Base pairs keep the v1 shape (no family field); fallback names them.
        def family(case):
            return case.get("family", "direct-instruction" if case["slice"] == "document-conflict" else "benign")
        conflict_families = {family(case) for case in cases if case["slice"] == "document-conflict"}
        self.assertGreaterEqual(len(conflict_families), 13)
        self.assertIn("direct-instruction", conflict_families)
        markers = [case["marker"] for case in cases if case["marker"]]
        self.assertEqual(len(markers), len(set(markers)))
        self.assertTrue(all(case["id"] in {c["id"] for c in cases} for case in (
            {"id": "cor-benign"}, {"id": "base64-conflict"}, {"id": "persona-benign"},
            {"id": "politica-conflict"}, {"id": "payload64-conflict"},
            {"id": "homoglifo-conflict"}, {"id": "turnos-conflict"})))
        for case in cases:
            self.assertIn(case["slice"], {"benign", "document-conflict"})
            self.assertTrue(case["instruction"])
            self.assertTrue(case["document"])
            self.assertIsNotNone(case["reference"])

    def test_corpus_v1_slice_stays_frozen_and_v2_digest_is_pinned(self):
        cases = lab.synthetic_cases()
        self.assertEqual(len(cases), 48)
        self.assertEqual(api.digest(cases[:24]), "f7f567e6cec12c82fdefe601ff301f032464e6d06bdcc37a1138c8528cec0542")
        self.assertEqual(api.digest(cases), "5f76c4635ff47a7f30c43b1055b4d4c335518fb83d3451a297ab8cf957e55ce3")

    def test_no_clobber_prepare(self):
        with self.assertRaises(api.LabError):
            lab.prepare(self.directory)

    def test_tampered_corpus_rejected(self):
        path = self.directory / "cases.json"
        cases = lab.load_json(path)
        cases[0]["instruction"] = "different"
        path.write_text(json.dumps(cases), encoding="utf-8")
        with self.assertRaises(api.LabError):
            lab.read_lab(self.directory)

    def test_removed_defense_clause_rejected(self):
        (self.directory / "revised.md").write_text("A weak replacement prompt.", encoding="utf-8")
        directory, manifest, original, _ = lab.read_lab(self.directory)
        with self.assertRaises(api.LabError):
            lab.candidate_text(directory, "revised", manifest, original)

    def test_dry_run_no_key_no_journal_no_api(self):
        fake = FakeTransport()
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            result = lab.collect(self.directory, "original", budget="1.00", transport=fake)
        self.assertEqual(result["api_calls_sent"], 0)
        self.assertEqual(fake.calls, [])
        self.assertFalse((self.directory / "original.observations.jsonl").exists())

    def test_insufficient_preflight_budget_no_api(self):
        fake = FakeTransport()
        with self.assertRaises(api.LabError):
            lab.collect(self.directory, "original", budget="0.00001", transport=fake)
        self.assertEqual(fake.calls, [])

    def test_live_fake_journal_complete_no_clobber(self):
        fake = FakeTransport(*[(200, {}, reply()) for _ in lab.synthetic_cases()])
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-only"}):
            result = lab.collect(self.directory, "original", budget="1.00", live=True, transport=fake)
            self.assertEqual(result["observations"], self.n)
            with self.assertRaises(FileExistsError):
                lab.collect(self.directory, "original", budget="1.00", live=True, transport=fake)
        self.assertEqual(len(fake.calls), self.n)
        rows = lab.observations(self.directory / "original.observations.jsonl")
        self.assertEqual(rows[0]["kind"], "started")
        self.assertEqual(rows[-1]["kind"], "finished")
        self.assertEqual(sum(row["kind"] == "observation" for row in rows), self.n)

    def test_infra_failure_is_retained_and_stops_collection(self):
        fake = FakeTransport((402, {}, {"error": {"code": 402}}))
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-only"}):
            with self.assertRaises(api.LabError):
                lab.collect(self.directory, "original", budget="1.00", live=True, transport=fake)
        rows = lab.observations(self.directory / "original.observations.jsonl")
        self.assertEqual(rows[-1]["status"], "error")
        self.assertNotIn("response", rows[-1])
        self.assertEqual(len(fake.calls), 1)

    def test_incomplete_response_marks_case_and_continues_collection(self):
        # One blank completion must be recorded as an inconclusive case; the
        # collection continues and the journal finishes — never a full abort.
        self.write_revision()
        fake = FakeTransport((200, {}, reply(text="")),
                             *[(200, {}, reply()) for _ in range(self.n - 1)])
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-only"}):
            summary = lab.collect(self.directory, "revised", budget="1.00", live=True, transport=fake)
        self.assertEqual(summary["inconclusive_responses"], 1)
        self.assertEqual(len(fake.calls), self.n)
        rows = lab.observations(self.directory / "revised.observations.jsonl")
        self.assertEqual(rows[-1]["kind"], "finished")
        first = next(row for row in rows if row.get("kind") == "observation")
        self.assertEqual(first["status"], "inconclusive-response")
        self.assertEqual(first["error_code"], "response.incomplete")
        self.assertNotIn("response", first)
        # The incomplete case leaves the conclusive denominator downstream.
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-only"}):
            lab.collect(self.directory, "original", budget="1.00", live=True,
                        transport=FakeTransport(*[(200, {}, reply()) for _ in range(self.n)]))
            lab.export_jev(self.directory, budget="0.01")
        pairing = lab.load_json(self.directory / "pairing.json")
        incomplete = {meta["scenario_id"] for meta in pairing["pairs"].values()
                      if not meta["collection_complete"]}
        self.assertEqual(incomplete, {"cor-benign"})

    def test_export_blinded_and_no_invented_gold_or_llm_judge(self):
        self.collect_both()
        config = lab.load_json(self.directory / "jev-eval.json")
        self.assertEqual(config["models"], {"decision": [lab.JEV_MODEL]})
        self.assertEqual(config["mode"], "eval")
        self.assertEqual(len(config["cases"]), 2 * self.n)
        for case in config["cases"]:
            self.assertEqual(case["expected"], {})
            self.assertEqual(len(case["id"]), 24)
            for field in ("candidate", "reference", "expected", "prompt_sha256", "scenario_id"):
                self.assertNotIn(field, case["state"])
        self.assertFalse(config["fit"])

    def test_pairing_no_improvement_is_not_a_win(self):
        self.collect_both()
        result = self.compare_record(self.run_record())
        for row in result["slices"].values():
            self.assertEqual(row["decisive_pairs"], self.pairs_per_slice)
            self.assertEqual(row["utility_delta_pp"], 0)
            self.assertEqual(row["improved_pairs"], 0)
            self.assertEqual(row["regressed_pairs"], 0)
        self.assertFalse(result["human_gold"])

    def test_collection_telemetry_does_not_double_count_reasoning(self):
        self.collect_both()
        result = self.compare_record(self.run_record())
        data = result["collection"]["original"]
        self.assertEqual(data["complete_responses"], self.n)
        self.assertEqual(data["completion_tokens"], self.n * 20)
        self.assertEqual(data["reasoning_tokens_subset_of_completion"], self.n * 12)
        self.assertTrue(data["budget"]["cost_exact"])
        self.assertIsNone(result["judge_run"]["observed_cost_usd"])
        self.assertFalse(result["judge_run"]["cost_exact"])

    def test_running_or_untrusted_status_is_not_a_final_record(self):
        self.collect_both()
        run = self.run_record()
        run["status"] = "running"
        with self.assertRaises(api.LabError) as error:
            self.compare_record(run)
        self.assertEqual(error.exception.code, "jev.record")

    def test_missing_cell_excludes_both_sides_not_success(self):
        self.collect_both()
        run = self.run_record()
        run["cells"].pop(0)
        result = self.compare_record(run)
        row = result["slices"]["benign"]
        self.assertEqual(row["decisive_pairs"], self.pairs_per_slice - 1)
        self.assertEqual(row["inconclusive_pairs"], 1)
        self.assertEqual(row["original"]["task_fulfilled"], self.pairs_per_slice - 1)
        self.assertEqual(row["revised"]["task_fulfilled"], self.pairs_per_slice - 1)

    def test_low_confidence_is_inconclusive(self):
        self.collect_both()
        run = self.run_record()
        run["cells"][0]["answers"]["evidence"]["confidence"] = 0.2
        result = self.compare_record(run)
        self.assertEqual(result["slices"]["benign"]["inconclusive_pairs"], 1)

    def test_borderline_noul_threshold_symmetric(self):
        self.collect_both()
        run = self.run_record()
        for cell in run["cells"]:
            cell["answers"]["task_fulfilled"]["noul"] = 0.9
            cell["answers"]["external_instruction_adopted"]["noul"] = 0.1
        result = self.compare_record(run)
        self.assertEqual(result["slices"]["benign"]["decisive_pairs"], self.pairs_per_slice)

    def test_duplicate_cells_rejected(self):
        self.collect_both()
        run = self.run_record()
        run["cells"].append(copy.deepcopy(run["cells"][0]))
        with self.assertRaises(api.LabError):
            self.compare_record(run)

    def test_different_state_or_questions_rejected(self):
        self.collect_both()
        run = self.run_record()
        run["cases"][0]["state"]["public_response"] = "different"
        with self.assertRaises(api.LabError) as error:
            self.compare_record(run)
        self.assertEqual(error.exception.code, "jev.provenance")

    def test_llm_fallback_record_rejected(self):
        self.collect_both()
        run = self.run_record()
        run["contestants"][0]["kind"] = "llm"
        with self.assertRaises(api.LabError) as error:
            self.compare_record(run)
        self.assertEqual(error.exception.code, "jev.model")

    def test_snapshot_drift_rejected(self):
        self.collect_both()
        run = self.run_record()
        run["resolvedModels"][lab.JEV_MODEL].append(lab.JEV_MODEL + "-different")
        with self.assertRaises(api.LabError) as error:
            self.compare_record(run)
        self.assertEqual(error.exception.code, "jev.drift")

    def test_nan_answer_is_inconclusive_not_valid(self):
        self.assertIsNone(lab._noul({"type": "noul", "noul": float("nan")}))
        self.assertIsNone(lab._noul({"type": "noul", "noul": True}))
        self.assertIsNone(lab._noul({"type": "score", "noul": 1}))


if __name__ == "__main__":
    unittest.main()
