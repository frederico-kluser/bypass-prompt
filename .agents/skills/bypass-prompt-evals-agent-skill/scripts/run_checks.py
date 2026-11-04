#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run every offline check that belongs to this skill.

Default: Python suites, Node suite, the project's legacy selftest, the
hardening-template checks and the benchmark registry hashes. No model call,
credential, network request or paid operation is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # .agents/skills/<skill>
PROJECT = ROOT.parents[2]                            # repository root
REGISTRY = ROOT / "benchmarks" / "registry.json"


def _run(command, cwd):
    process = subprocess.run([str(part) for part in command], cwd=str(cwd),
                             text=True, capture_output=True, check=False)
    return process.returncode, (process.stdout or "") + (process.stderr or "")


def _last(text):
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else "sem saída"


def check_python():
    code, output = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], ROOT)
    return code == 0, _last(output)


def check_node():
    node = shutil.which("node")
    if not node:
        return False, "node não encontrado (requer >= 20.11 para o adaptador)"
    code, output = _run([node, "--test", "tests/test_prompt_builder_rewrite.mjs"], ROOT)
    summary = next((line.strip() for line in reversed(output.splitlines())
                    if line.strip().startswith("ℹ pass")), _last(output))
    return code == 0, summary


def check_project():
    script = PROJECT / "scripts" / "bypass.py"
    if not script.is_file():
        return False, "scripts/bypass.py não encontrado; defina BYPASS_PROMPT_ROOT"
    code, output = _run([sys.executable, str(script), "selftest"], PROJECT)
    passed = sum(1 for line in output.splitlines() if "[PASS]" in line)
    failed = sum(1 for line in output.splitlines() if "[FAIL]" in line)
    return code == 0 and failed == 0, "%d cenários PASS, %d FAIL" % (passed, failed)


def check_templates():
    code = (
        "import sys; sys.path.insert(0, %r); import harden; "
        "bad=[t for t in sorted(harden.TEMPLATES) if harden.check(harden.render(t))['score'] != 18]; "
        "print('templates falhados:', bad); raise SystemExit(1 if bad else 0)"
    ) % str(PROJECT / "scripts")
    status, output = _run([sys.executable, "-c", code], ROOT)
    return status == 0, _last(output)


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(131072), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_registry():
    if not REGISTRY.is_file():
        return False, "benchmarks/registry.json ausente"
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return False, "registry ilegível (%s)" % type(error).__name__
    if data.get("format") != "bypass-prompt-benchmarks@1":
        return False, "formato de registry inválido"
    benchmarks = data.get("benchmarks")
    if not isinstance(benchmarks, list) or not benchmarks:
        return False, "registry sem benchmarks"
    problems = []
    for benchmark in benchmarks:
        if not isinstance(benchmark, dict) or not benchmark.get("id") or not benchmark.get("status"):
            problems.append("benchmark sem id/status")
            continue
        if benchmark.get("human_gold") is not False:
            problems.append("%s: human_gold deve ser false" % benchmark["id"])
        files = benchmark.get("files")
        if benchmark.get("kind") == "offline-suite":
            if files:
                problems.append("%s: suíte offline não deve declarar artefactos" % benchmark["id"])
            continue
        if not isinstance(files, dict) or not files:
            problems.append("%s: sem hashes" % benchmark["id"])
            continue
        for relative, expected in files.items():
            path = ROOT / relative
            if not path.is_file():
                problems.append("falta %s" % relative)
            elif _sha256(path) != expected:
                problems.append("hash divergente: %s" % relative)
    detail = "%d benchmarks" % len(benchmarks)
    if problems:
        detail += "; " + "; ".join(problems)
    return not problems, detail


CHECKS = {
    "python": check_python,
    "node": check_node,
    "project": check_project,
    "templates": check_templates,
    "registry": check_registry,
}
DEFAULT_ORDER = ["python", "node", "project", "templates", "registry"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="lista separada por vírgulas: " + ", ".join(DEFAULT_ORDER))
    parser.add_argument("--json", action="store_true", help="saída JSON em stdout")
    args = parser.parse_args(argv)
    names = DEFAULT_ORDER if not args.only else [name.strip() for name in args.only.split(",") if name.strip()]
    unknown = [name for name in names if name not in CHECKS]
    if not names or unknown:
        print("Erro: check desconhecido %s — Solução: use %s" % (", ".join(unknown) or "(vazio)",
                                                                ", ".join(DEFAULT_ORDER)), file=sys.stderr)
        return 2
    results = []
    for name in names:
        ok, detail = CHECKS[name]()
        results.append({"name": name, "ok": bool(ok), "detail": detail})
        if not args.json:
            print("[%s] %-9s %s" % ("PASS" if ok else "FAIL", name, detail))
    payload = {"ok": all(item["ok"] for item in results), "skill": ROOT.name,
               "project": str(PROJECT), "checks": results, "paid_calls": 0, "network_calls": 0}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("\nResumo: %d ok · %d falha(s) · 0 chamadas de modelo"
              % (sum(item["ok"] for item in results), sum(not item["ok"] for item in results)))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
