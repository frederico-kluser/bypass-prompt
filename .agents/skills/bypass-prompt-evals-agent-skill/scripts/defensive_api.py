# -*- coding: utf-8 -*-
"""Internal OpenRouter API for the isolated defensive prompt laboratory.

This module is deliberately not connected to bypass.py convert/eval. It never
selects a more permissive model after a refusal, executes tools, or optimizes
against a detector. Only public/synthetic defensive evaluation data belong here.
Python 3.10+, standard library only. Importing this module performs no I/O.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from typing import Callable

MODEL = "z-ai/glm-5.3-flash"
PROVIDER = "z-ai/fp8"
BASE_URL = "https://openrouter.ai/api/v1"
MAX_RESPONSE_BYTES = 2_000_000
REQUIRED_PARAMETERS = {"reasoning", "max_tokens", "temperature"}


class LabError(Exception):
    """Actionable error without remote response bodies or credentials."""

    def __init__(self, problem: str, solution: str, *, code: str = "lab.error"):
        super().__init__(f"Erro: {problem} — Solução: {solution}")
        self.code = code


def money(value, name="valor", *, positive=False) -> Decimal:
    """Reject bool, NaN, infinity, negative and malformed monetary values."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise LabError(f"{name} inválido", "use um número USD finito", code="budget.invalid") from None
    if isinstance(value, bool) or not result.is_finite() or result < 0 or (positive and result == 0):
        raise LabError(f"{name} inválido", "use um número USD finito e não negativo", code="budget.invalid")
    return result


def digest(value) -> str:
    raw = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class Budget:
    """Per-process budget; ambiguous attempts retain their full reservation.

    The input bound is a deliberately conservative byte-based estimate, not a
    tokenizer or an account-wide hard billing limit. Configure a credit limit on
    the OpenRouter key as well. A new process is a new budget, not a free resume.
    """
    cap: Decimal
    spent: Decimal = Decimal("0")
    uncertain: Decimal = Decimal("0")
    attempts: int = 0

    def __post_init__(self):
        self.cap = money(self.cap, "orçamento", positive=True)

    def reserve(self, amount: Decimal):
        amount = money(amount, "reserva", positive=True)
        if self.spent + self.uncertain + amount > self.cap:
            raise LabError("orçamento insuficiente antes da chamada", "reduza a coleta ou autorize novo teto", code="budget.exceeded")
        self.uncertain += amount
        self.attempts += 1

    def settle(self, reservation: Decimal, usage) -> Decimal | None:
        raw = usage.get("cost") if isinstance(usage, dict) else None
        if raw is None:
            return None  # Unknown is NOT zero; retain the reservation.
        actual = money(raw, "usage.cost")
        self.uncertain -= reservation
        self.spent += actual
        if actual > reservation or self.spent + self.uncertain > self.cap:
            raise LabError("custo observado excede a reserva conservadora", "interrompa e confira a cobrança da conta", code="budget.overrun")
        return actual

    def snapshot(self) -> dict:
        return {"budget_usd": str(self.cap), "observed_cost_usd": str(self.spent),
                "unknown_cost_reserved_usd": str(self.uncertain),
                "cost_exact": self.uncertain == 0, "attempts": self.attempts}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward prompts or Authorization to a new URL.


class HttpTransport:
    """Fixed-host HTTPS transport; no caller-controlled URL or redirect."""

    def __init__(self):
        self._opener = urllib.request.build_opener(_NoRedirect())

    def __call__(self, method, path, body, key, timeout):
        if not isinstance(path, str) or not path.startswith("/") or "//" in path or "?" in path:
            raise LabError("caminho de API inválido", "use os métodos internos do laboratório", code="request.path")
        headers = {"Accept": "application/json", "X-OpenRouter-Title": "bypass-prompt defensive lab"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if key:
            headers["Authorization"] = "Bearer " + key
        request = urllib.request.Request(BASE_URL + path, data=None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8"), headers=headers, method=method)
        try:
            response = self._opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            response = exc
        except (urllib.error.URLError, TimeoutError, OSError):
            raise LabError("falha de rede; cobrança pode estar pendente", "consulte a conta antes de repetir; nenhum fallback foi usado", code="network.unknown") from None
        with response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise LabError("resposta excede o limite local", "investigue a geração sem repetir automaticamente", code="response.too_large")
            return response.code, dict(response.headers), raw


def _decode(raw):
    try:
        value = json.loads(raw)
    except (ValueError, TypeError, UnicodeError):
        raise LabError("resposta não é JSON válido", "inspecione o estado da geração sem expor dados", code="response.json") from None
    if not isinstance(value, dict):
        raise LabError("envelope de API inválido", "confira o contrato OpenRouter", code="response.schema")
    return value


def _error_kind(value) -> str:
    error = value.get("error", {})
    metadata = error.get("metadata", {}) if isinstance(error, dict) else {}
    kind = metadata.get("error_type", "remote.error") if isinstance(metadata, dict) else "remote.error"
    return kind if isinstance(kind, str) and re.fullmatch(r"[a-z_\.]{1,64}", kind) else "remote.error"


def retry_delay(headers, attempt, now=None):
    """Honor numeric OR HTTP-date Retry-After; never retry earlier than requested."""
    value = next((str(v) for k, v in headers.items() if k.lower() == "retry-after"), None)
    delay = float(2 ** attempt)
    if value is not None:
        try:
            hinted = float(value)
            if not math.isfinite(hinted) or hinted < 0:
                raise ValueError
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                hinted = max(0.0, (date - (now or datetime.now(timezone.utc))).total_seconds())
            except (ValueError, TypeError, OverflowError):
                hinted = 0.0
        delay = max(delay, hinted)
    if delay > 30:
        raise LabError("Retry-After exige espera superior a 30 segundos", "aguarde o prazo do servidor antes de iniciar nova execução", code="retry.deferred")
    return delay


def validate_catalog(model, endpoints, provider=PROVIDER):
    """No approximate model match and no silent max -> high downgrade."""
    if not isinstance(model, dict) or model.get("id") != MODEL:
        raise LabError("modelo solicitado não consta exatamente no catálogo", "confira z-ai/glm-5.3-flash; não será trocado automaticamente", code="catalog.model")
    reasoning = model.get("reasoning")
    efforts = reasoning.get("supported_efforts") if isinstance(reasoning, dict) else None
    if not isinstance(efforts, list) or "max" not in efforts:
        raise LabError("effort max não é anunciado pelo modelo", "revise o catálogo; não reduza o effort silenciosamente", code="catalog.reasoning")
    candidates = endpoints.get("endpoints", []) if isinstance(endpoints, dict) else []
    if not isinstance(candidates, list):
        raise LabError("lista de endpoints inválida", "confira o catálogo antes de gastar", code="catalog.schema")
    matches = [ep for ep in candidates if isinstance(ep, dict) and ep.get("tag") == provider]
    if len(matches) != 1:
        raise LabError("provider fixado não está disponível de forma inequívoca", "confira o tag no catálogo sem habilitar fallback", code="catalog.provider")
    ep = matches[0]
    parameters = ep.get("supported_parameters")
    if not isinstance(parameters, list) or any(not isinstance(p, str) for p in parameters) or not REQUIRED_PARAMETERS.issubset(parameters):
        raise LabError("provider não anuncia todos os parâmetros necessários", "use um provider explicitamente compatível", code="catalog.parameters")
    pricing = ep.get("pricing")
    if not isinstance(pricing, dict):
        raise LabError("preços do provider indisponíveis", "confira preços antes de gastar", code="catalog.pricing")
    for name in ("prompt", "completion"):
        money(pricing.get(name), "preço " + name)
    for name in ("context_length", "max_completion_tokens"):
        n = ep.get(name)
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise LabError("limites de tokens do provider indisponíveis", "confira o endpoint antes de gastar", code="catalog.limits")
    return ep


class DefensiveAPI:
    """Fixed GLM 5.3 Flash, max effort, a single provider and bounded attempts.

    Transport/sleeper injection is a Python test seam, not a network-routing CLI.
    Textual refusals remain observations; structured refusals are terminal.
    """

    def __init__(self, budget_usd, *, provider=PROVIDER, key=None,
                 timeout=180, max_attempts=2, transport: Callable | None = None,
                 sleeper: Callable = time.sleep):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 1 <= timeout <= 300:
            raise LabError("timeout inválido", "use de 1 a 300 segundos", code="request.timeout")
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 3:
            raise LabError("limite de tentativas inválido", "use de 1 a 3 tentativas", code="request.attempts")
        if not isinstance(provider, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_./-]{0,100}", provider):
            raise LabError("tag de provider inválido", "use o tag exato do catálogo", code="request.provider")
        self.provider = provider
        self.key = key if key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        self.budget = Budget(money(budget_usd, "orçamento", positive=True))
        self.timeout, self.max_attempts = timeout, max_attempts
        self.transport, self.sleeper = transport or HttpTransport(), sleeper
        self.model = self.endpoint = None

    def load_catalog(self, snapshot=None):
        if snapshot is None:
            result = {}
            for name, path in (("model", "/model/" + MODEL), ("endpoints", "/models/" + MODEL + "/endpoints")):
                status, _, raw = self.transport("GET", path, None, "", self.timeout)
                value = _decode(raw)
                if status != 200 or "error" in value:
                    raise LabError("catálogo OpenRouter indisponível", "repita apenas a consulta pública", code="catalog.http")
                result[name] = value.get("data")
            result["fetched_utc"] = datetime.now(timezone.utc).isoformat()
            snapshot = result
        if not isinstance(snapshot, dict):
            raise LabError("snapshot de catálogo inválido", "forneça model e endpoints", code="catalog.schema")
        self.model = snapshot.get("model")
        self.endpoint = validate_catalog(self.model, snapshot.get("endpoints"), self.provider)
        return snapshot

    def prepare(self, system_prompt: str, user_prompt: str, *, max_tokens=4096):
        if self.endpoint is None:
            raise LabError("catálogo não carregado", "execute load_catalog antes de preparar uma chamada", code="catalog.required")
        if any(not isinstance(text, str) or not text.strip() for text in (system_prompt, user_prompt)):
            raise LabError("prompt vazio ou inválido", "forneça instrução defensiva e tarefa sintética", code="request.prompt")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 128 <= max_tokens <= 32768:
            raise LabError("max_tokens inválido", "use de 128 a 32768, incluindo reasoning", code="request.tokens")
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        # Conservative byte proxy + generous framing allowance; not an exact tokenizer.
        input_bound = len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) + 2048
        ep = self.endpoint
        if max_tokens > ep["max_completion_tokens"] or input_bound + max_tokens > ep["context_length"] or (ep.get("max_prompt_tokens") and input_bound > ep["max_prompt_tokens"]):
            raise LabError("pedido excede limites conservadores do endpoint", "reduza entrada/saída antes de enviar", code="request.context")
        prices = {k: money(ep["pricing"][k], "preço " + k) for k in ("prompt", "completion")}
        request_price = money(ep["pricing"].get("request", "0"), "preço por request")
        reserved = input_bound * prices["prompt"] + max_tokens * prices["completion"] + request_price
        # A zero-price endpoint still needs a nonzero reservation unit locally.
        reserved = max(reserved, Decimal("0.000000001"))
        body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens,
                "temperature": 0, "stream": False,
                "reasoning": {"effort": "max", "exclude": True},
                "provider": {"only": [self.provider], "allow_fallbacks": False,
                             "require_parameters": True, "data_collection": "deny",
                             "max_price": {"prompt": float(prices["prompt"] * 1_000_000),
                                           "completion": float(prices["completion"] * 1_000_000),
                                           "request": float(request_price)}}}
        return body, reserved

    def complete(self, system_prompt, user_prompt, *, max_tokens=4096):
        if not self.key or not isinstance(self.key, str) or any(c in self.key for c in "\r\n"):
            raise LabError("OPENROUTER_API_KEY ausente ou inválida", "carregue a variável por armazenamento seguro, nunca pelo chat", code="auth.missing")
        body, reservation = self.prepare(system_prompt, user_prompt, max_tokens=max_tokens)
        started = time.monotonic()
        for attempt in range(self.max_attempts):
            self.budget.reserve(reservation)
            status, headers, raw = self.transport("POST", "/chat/completions", body, self.key, self.timeout)
            value = _decode(raw)
            actual = self.budget.settle(reservation, value.get("usage"))
            if status != 200 or "error" in value:
                kind = _error_kind(value)
                terminal = kind in {"refusal", "content_policy_violation", "permission_denied", "authentication", "payment_required"}
                code = (value.get("error") or {}).get("code", status) if isinstance(value.get("error", {}), dict) else status
                if not terminal and (status in (429, 503) or code in (429, 503)) and attempt + 1 < self.max_attempts:
                    self.sleeper(retry_delay(headers, attempt))
                    continue  # Same body, same model, same provider; each attempt reserved.
                raise LabError(f"OpenRouter recusou/falhou (HTTP {status}; {kind})", "verifique permissão/créditos/serviço; não haverá troca de modelo", code=kind)
            allowed_models = {MODEL, self.model.get("canonical_slug", MODEL)}
            if value.get("model") not in allowed_models:
                raise LabError("modelo retornado difere do modelo fixado", "interrompa e confira o roteamento", code="response.model")
            choices = value.get("choices")
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise LabError("choices inválido", "trate a observação como inconclusiva", code="response.choices")
            choice = choices[0]
            message = choice.get("message")
            if not isinstance(message, dict):
                raise LabError("message inválida", "trate a observação como inconclusiva", code="response.message")
            if message.get("refusal") or choice.get("finish_reason") == "content_filter":
                raise LabError("recusa explícita do modelo", "registre a recusa; não repita noutro modelo", code="response.refusal")
            if message.get("tool_calls") or message.get("function_call"):
                raise LabError("resposta propôs ferramentas fora do contrato", "não execute nada; revise a coleta", code="response.tools")
            text = message.get("content")
            if choice.get("finish_reason") != "stop" or not isinstance(text, str) or not text.strip():
                raise LabError("resposta vazia, parcial ou inválida", "registre como inconclusiva, sem contar como bloqueio", code="response.incomplete")
            usage = value.get("usage") if isinstance(value.get("usage"), dict) else {}
            return {"text": text, "model": value["model"], "provider": value.get("provider"),
                    "generation_id": value.get("id"), "finish_reason": "stop",
                    "cost_usd": str(actual) if actual is not None else None,
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                    "elapsed_ms": round((time.monotonic() - started) * 1000),
                    "request_sha256": digest(body), "budget": self.budget.snapshot()}
        raise AssertionError("unreachable")
