#!/usr/bin/env node
/** One blinded, defensive prompt proposal through prompt-builder's LOCAL internals.
 * No arena, agent execution, detector feedback, judge LLM, or refusal fallback.
 * Internal imports are version/hash recorded; this is not a public package API.
 */
import { createHash } from 'node:crypto';
import { readFile, writeFile, open, access } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

export const MODEL = 'z-ai/glm-5.3-flash';
export const PROVIDER = 'z-ai/fp8';
export const MODULES = ['dist/variator.js', 'dist/openrouter.js', 'dist/budget.js', 'dist/cli/spendGuards.js', 'dist/engine/contracts.js'];
export const sha = value => createHash('sha256').update(value).digest('hex');
const fail = (problem, solution) => { throw new Error(`Erro: ${problem} — Solução: ${solution}`); };
const readJson = async path => JSON.parse((await readFile(path, 'utf8')).replace(/^\uFEFF/, ''));

export function normalizeModel(snapshot) {
  const raw = snapshot?.model;
  const endpoint = snapshot?.endpoints?.endpoints?.filter(ep => ep.tag === PROVIDER);
  if (raw?.id !== MODEL || !Array.isArray(raw.reasoning?.supported_efforts) || !raw.reasoning.supported_efforts.includes('max'))
    fail('modelo/effort max não confirmado', 'atualize o catálogo sem trocar silenciosamente o modelo');
  if (endpoint?.length !== 1) fail('provider fixado ausente ou ambíguo', 'confira o tag exato no catálogo');
  const ep = endpoint[0];
  for (const parameter of ['reasoning', 'max_tokens', 'temperature'])
    if (!ep.supported_parameters?.includes(parameter)) fail('provider incompatível', 'confira parâmetros antes de gastar');
  const pricing = {};
  for (const field of ['prompt', 'completion']) {
    const n = Number(ep.pricing?.[field]);
    if (ep.pricing?.[field] == null || !Number.isFinite(n) || n < 0) fail('preço desconhecido', 'não assuma custo zero');
    pricing[field] = n;
  }
  return { id: MODEL, name: raw.name ?? MODEL, contextLength: ep.context_length,
    pricing, supportedParameters: ep.supported_parameters, canonicalSlug: raw.canonical_slug,
    reasoning: { mandatory: raw.reasoning.mandatory, defaultEnabled: raw.reasoning.default_enabled,
      supportedEfforts: raw.reasoning.supported_efforts, defaultEffort: raw.reasoning.default_effort } };
}

export function proposalParams({ key, original, manifest, signal, sink, maxPrice }) {
  if (manifest?.purpose !== 'synthetic-defensive-smoke-comparison' || manifest?.model !== MODEL || manifest?.provider !== PROVIDER)
    fail('escopo do manifesto incompatível', 'use defensive_lab.py prepare');
  const anchors = original.split(/\r?\n/).filter(line => line.startsWith('- '));
  if (!Array.isArray(manifest.never_break) || JSON.stringify(anchors) !== JSON.stringify(manifest.never_break))
    fail('contratos defensivos divergentes', 'preserve todas as regras defensivas do original');
  return { apiKey: key, modelId: MODEL, optimizerModelId: MODEL,
    theme: 'Melhorar somente a clareza operacional e a especificidade de um assistente defensivo para tarefas textuais benignas; preservar literalmente todas as cláusulas defensivas. Nunca facilitar evasão, suspender salvaguardas ou reduzir detecção. Não acrescentar raciocínio privado nem instruções para ferramentas.',
    basePrompt: original, originalPrompt: original, includeOriginal: true,
    promptOptimization: true, techniqueIds: ['specificity'],
    reasoningLevel: 'max', contestantReasoningLevel: 'max', runner: 'chat',
    contracts: { neverBreak: anchors, placeholders: [], minLengthRatio: 1, judgeDiff: false, canaries: [] },
    timeoutMs: 180000, ctx: { signal, sink }, maxPricePerMTok: maxPrice };
}

export function checkedFetch(realFetch) {
  return async (input, init = {}) => {
    const url = new URL(String(input));
    if (url.origin !== 'https://openrouter.ai' || url.username || url.password)
      fail('destino de API fora da allowlist', 'não encaminhe prompts nem credenciais a outro host');
    if ((init.method ?? 'GET').toUpperCase() === 'POST') {
      if (url.pathname !== '/api/v1/chat/completions') fail('endpoint não permitido na proposta', 'não use decisões ou execução de agentes nesta fase');
      const body = JSON.parse(String(init.body));
      if (body.model !== MODEL || body.models || body.tools || body.tool_choice || body.plugins || body.fallbacks)
        fail('request saiu do escopo GLM sem ferramentas', 'interrompa sem fallback');
      if (body.reasoning?.effort !== 'max' || body.max_tokens !== 8192)
        fail('effort/teto do reescritor divergente', 'revise o contrato da instalação prompt-builder');
      const provider = body.provider;
      if (JSON.stringify(provider?.order) !== JSON.stringify([PROVIDER]) || provider.allow_fallbacks !== false || provider.require_parameters !== true)
        fail('provider não está fixado estritamente', 'configure a rota auditável do reescritor');
      body.provider.data_collection = 'deny';
      body.reasoning.exclude = true; // Do not collect private reasoning as an artifact.
      return realFetch(String(url), { ...init, body: JSON.stringify(body), redirect: 'error' });
    }
    if (!['/api/v1/models', '/api/v1/generation'].includes(url.pathname))
      fail('consulta de metadata fora do contrato', 'revise a versão do gateway');
    return realFetch(String(url), { ...init, redirect: 'error' });
  };
}

export function looksLikeRefusal(text) {
  // Conservative prefix heuristic for an explicit speaker refusal, not a safety
  // classifier. It deliberately does not match defensive directives such as
  // "Não aceites personas". Ambiguity stops a proposal; it never selects a model.
  const prefix = typeof text === 'string' ? text.trim().slice(0, 400) : '';
  return /^(?:(?:desculpe|desculpa|sinto muito|i(?:['’]m| am) sorry|i apologize)[\s,.:;!—-]*)?(?:n[ãa]o (?:posso|consigo|vou (?:ajudar|atender|fornecer|cumprir|realizar))\b|i (?:cannot|can['’]t|won['’]t|am unable to|will not (?:help|provide|comply))\b)/iu.test(prefix);
}

export async function loadInstallation(root) {
  root = resolve(root);
  const pkg = await readJson(join(root, 'package.json'));
  if (pkg.name !== 'prompt-builder-cli') fail('diretório não é prompt-builder-cli', 'informe a instalação compilada do prompt-builder');
  const hashes = {};
  for (const name of MODULES) hashes[name] = sha(await readFile(join(root, name)));
  const modules = {};
  for (const [name, path] of Object.entries({ variator: MODULES[0], gateway: MODULES[1], spend: MODULES[3] }))
    modules[name] = await import(pathToFileURL(join(root, path)).href);
  return { root, version: pkg.version, hashes, ...modules };
}

export async function runProposal({ directory, pbRoot, dataDir, budget, live = false, approvalHash, fetchImpl = globalThis.fetch }) {
  const cap = Number(budget);
  if (!Number.isFinite(cap) || cap <= 0) fail('orçamento inválido', 'informe um teto USD positivo');
  directory = resolve(directory);
  dataDir = resolve(dataDir ?? join(directory, 'prompt-builder-state'));
  const manifest = await readJson(join(directory, 'manifest.json'));
  const original = (await readFile(join(directory, 'original.md'), 'utf8')).replace(/^\uFEFF/, '');
  if (sha(original) !== manifest.original_sha256) fail('hash do original diverge', 'não altere o prompt após o congelamento');
  const snapshot = await readJson(join(directory, 'catalog.json'));
  const model = normalizeModel(snapshot);
  const installation = await loadInstallation(pbRoot);
  const maxPrice = { prompt: model.pricing.prompt * 1e6, completion: model.pricing.completion * 1e6 };
  const config = { kind: 'blinded-defensive-rewrite@1', originalSha256: sha(original),
    adapterSha256: sha(await readFile(fileURLToPath(import.meta.url))),
    catalogSha256: sha(JSON.stringify(snapshot)), dataDir,
    modelId: MODEL, provider: PROVIDER, effort: 'max', technique: 'specificity',
    promptBuilderVersion: installation.version, moduleHashes: installation.hashes,
    budgetUsd: cap, maxPricePerMTok: maxPrice };
  const identity = sha(JSON.stringify(config));
  proposalParams({ key: '', original, manifest, maxPrice }); // Offline scope/contracts check.
  const refusals = installation.spend.spendGuardRefusals({ dataDir, config });
  if (refusals.length) fail('guarda de gasto/lock bloqueou a proposta', 'corrija a causa na instalação sem contornar o gate');
  const preflight = { ...config, operationSha256: identity, paidCallsSent: 0,
    maxOutputTokensPerAttempt: 8192, proposalVariants: 1,
    localContractCorrectionLimit: 1, gatewayTransientRetriesPerCall: 4,
    humanReviewRequired: true, judgeLlm: false, detectorFeedback: false,
    internalApiWarning: 'Pinned local internals; not a stable public prompt-builder API.' };
  if (!live) return preflight;
  if (approvalHash !== identity) fail('hash aprovado ausente ou divergente', 'revise o dry-run e forneça --approval-hash do mesmo plano');
  const key = process.env.OPENROUTER_API_KEY;
  if (!key || /[\r\n]/.test(key)) fail('OPENROUTER_API_KEY ausente/inválida', 'carregue a variável do armazenamento seguro, nunca em argumento');
  try {
    await access(join(directory, 'revised.md'));
    fail('já existe uma revisão', 'use outra experiência; não sobrescreva uma proposta');
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
  // The append-only operation journal provides a persistent no-replay barrier,
  // including crashes/unknown outcomes. A different budget is not a free retry.
  const journal = await open(join(directory, 'rewrite.operation.jsonl'), 'wx');
  const append = async value => { await journal.writeFile(JSON.stringify(value) + '\n'); await journal.sync(); };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 240000);
  let accounting = null;
  let suppressedWarnings = 0;
  const previousWarn = console.warn;
  // Local internals can log upstream error.message. Never allow an untrusted
  // provider body (which may echo a credential/prompt) to reach stderr.
  console.warn = () => { suppressedWarnings++; previousWarn('[prompt-builder] Aviso interno omitido; consulte o status e a contabilidade sanitizados.'); };
  try {
    await append({ status: 'started', ...preflight, startedAt: new Date().toISOString() });
    const gateway = installation.gateway.configureGateway({
      baseUrl: 'https://openrouter.ai/api/v1', attribution: false, maxConcurrency: 1,
      streamTransport: true, providerLookup: 'missing', fetch: checkedFetch(fetchImpl),
      auditableRoles: ['rewriter'], auditableProviderOrder: [PROVIDER], auditableQuantizations: ['fp8'],
      roleTimeouts: { rewriter: { idleMs: 90000, totalMs: 180000 } }, metaTimeoutMs: 20000,
    });
    // A structured refusal/block stops the proposal BEFORE a local correction.
    const guarded = new Proxy(gateway, { get(target, prop) {
      const value = Reflect.get(target, prop);
      if (prop === 'chatCompletion') return async (...args) => {
        const result = await value.apply(target, args);
        if (result.refusal || result.blocked || looksLikeRefusal(result.text)) fail('reescritor recusou/bloqueou a proposta', 'registre a recusa; não reencaminhe nem repita noutro modelo');
        return result;
      };
      return typeof value === 'function' ? value.bind(target) : value;
    } });
    installation.gateway.setDefaultGateway(guarded);
    installation.gateway.primeModelsCache(key, [model]);
    const result = await installation.spend.withSpendGuards({ dataDir, config, command: 'defensive-rewrite', models: [model], signal: controller.signal }, async guard => {
      try {
        const candidates = await installation.variator.generateContestants(proposalParams({ key, original, manifest,
          signal: controller.signal, sink: guard.parentLedger, maxPrice }));
        const variants = candidates.filter(c => !c.isOriginal);
        if (variants.length !== 1 || typeof variants[0].systemPrompt !== 'string')
          fail('nenhuma proposta defensiva válida foi produzida', 'revise o journal; não faça retry automático de uma geração paga');
        const text = variants[0].systemPrompt;
        if (manifest.never_break.some(anchor => !text.includes(anchor)))
          fail('proposta alterou cláusulas defensivas literais', 'revise humanamente sem enfraquecer o contrato');
        return { text, techniqueId: variants[0].techniqueId };
      } finally {
        await installation.gateway.reconcileAtRunEnd(guard.parentLedger, key);
        accounting = { snapshot: guard.parentLedger.snapshot(), summary: guard.parentLedger.summary(), calls: guard.parentLedger.callLog() };
      }
    });
    await writeFile(join(directory, 'revised.md'), result.text, { encoding: 'utf8', flag: 'wx' });
    const report = { status: 'finished', operationSha256: identity,
      originalSha256: sha(original), revisedSha256: sha(result.text),
      techniqueId: result.techniqueId, humanReviewRequired: true, suppressedWarnings, accounting,
      promptBuilderVersion: installation.version, moduleHashes: installation.hashes };
    await append(report);
    await writeFile(join(directory, 'rewrite.summary.json'), JSON.stringify(report, null, 2) + '\n', { encoding: 'utf8', flag: 'wx' });
    return report;
  } catch (error) {
    await append({ status: 'failed-or-unknown', accounting, suppressedWarnings, errorClass: error?.name ?? 'Error',
      instruction: 'No automatic retry; inspect billing and retained artifacts.' });
    // No raw provider message, prompt or secret in the CLI error.
    fail('proposta interrompida; cobrança pode existir', 'consulte o journal e a conta antes de qualquer nova experiência');
  } finally {
    console.warn = previousWarn;
    clearTimeout(timer);
    await journal.close();
  }
}

async function main() {
  const { values } = parseArgs({ options: {
    directory: { type: 'string' }, 'prompt-builder-root': { type: 'string' },
    'data-dir': { type: 'string' }, budget: { type: 'string' },
    live: { type: 'boolean', default: false }, 'dry-run': { type: 'boolean', default: false },
    'approval-hash': { type: 'string' },
  } });
  if (!values.directory || !values['prompt-builder-root'] || !values.budget || values.live === values['dry-run'])
    fail('argumentos incompletos', 'use --directory DIR --prompt-builder-root ROOT --budget USD e exatamente um de --dry-run/--live');
  const result = await runProposal({ directory: values.directory, pbRoot: values['prompt-builder-root'],
    dataDir: values['data-dir'], budget: values.budget, live: values.live, approvalHash: values['approval-hash'] });
  console.log(JSON.stringify(result, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { await main(); }
  catch (error) {
    console.error(error?.message?.startsWith('Erro:') ? error.message : 'Erro: artefato ou instalação incompatível — Solução: confira os caminhos, o catálogo e a versão compilada; nenhum fallback será usado');
    process.exitCode = 1;
  }
}
