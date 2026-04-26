"""
Drop-in Python snippets for preflight init-time questions.

Every snippet is self-contained. Imports at top of each function so
callers can copy one at a time. All citations point at source that
has been verified against transformers main / v5.5.4 as of 2026-04-21.

Usage:

    from references.snippets import (
        discover_added_tokens,
        resolve_marker_to_id,
        is_turn_marker_eos,
        cross_ref_files,
        version_gate_tokenizer_class,
        build_chat_template_env,
    )
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 1. Discover every added token ID
# ---------------------------------------------------------------------------


def discover_added_tokens(
    tokenizer, snapshot_dir: Path | None = None
) -> dict[int, dict[str, Any]]:
    """
    Return every added token in the tokenizer, keyed by integer ID.

    Precedence:
      1. Rust truth: tokenizer.backend_tokenizer.get_added_tokens_decoder()
      2. Python mirror: tokenizer.added_tokens_decoder
      3. Config file fallback: tokenizer_config.json["added_tokens_decoder"]
      4. tokenizer.json raw scan

    Each entry has: {"content", "special", "lstrip", "rstrip",
                     "normalized", "single_word"}.

    For TokenizersBackend, (1) and (2) agree. For PythonBackend
    (Kimi), (1) is unavailable; (2) works. For offline inspection
    without loading, use snapshot_dir + (3)/(4).
    """
    # Source 1: Rust passthrough — most authoritative
    backend = getattr(tokenizer, "backend_tokenizer", None) if tokenizer else None
    if backend is not None:
        try:
            decoder = backend.get_added_tokens_decoder()
            return {int(i): _added_token_to_dict(t) for i, t in decoder.items()}
        except (AttributeError, TypeError):
            pass

    # Source 2: Python mirror
    if tokenizer is not None:
        py_decoder = getattr(tokenizer, "added_tokens_decoder", None)
        if isinstance(py_decoder, dict) and py_decoder:
            return {int(i): _added_token_to_dict(t) for i, t in py_decoder.items()}

    # Source 3: tokenizer_config.json added_tokens_decoder
    if snapshot_dir is not None:
        tok_cfg_path = Path(snapshot_dir) / "tokenizer_config.json"
        if tok_cfg_path.exists():
            cfg = json.loads(tok_cfg_path.read_text())
            raw = cfg.get("added_tokens_decoder")
            if isinstance(raw, dict):
                return {
                    int(k): _normalize_added_token_dict(v)
                    for k, v in raw.items()
                    if isinstance(v, dict)
                }

        # Source 4: tokenizer.json raw scan
        tok_json_path = Path(snapshot_dir) / "tokenizer.json"
        if tok_json_path.exists():
            tok_json = json.loads(tok_json_path.read_text())
            added = tok_json.get("added_tokens", [])
            return {
                int(t["id"]): _normalize_added_token_dict(t) for t in added if "id" in t
            }

    return {}


def _added_token_to_dict(token) -> dict[str, Any]:
    """Coerce an AddedToken (from tokenizers Rust) into a plain dict."""
    return {
        "content": getattr(token, "content", str(token)),
        "special": bool(getattr(token, "special", False)),
        "lstrip": bool(getattr(token, "lstrip", False)),
        "rstrip": bool(getattr(token, "rstrip", False)),
        "normalized": bool(getattr(token, "normalized", True)),
        "single_word": bool(getattr(token, "single_word", False)),
    }


def _normalize_added_token_dict(entry: dict[str, Any]) -> dict[str, Any]:
    """Ensure a JSON-deserialized added-token dict has all expected keys."""
    return {
        "content": entry.get("content", ""),
        "special": bool(entry.get("special", False)),
        "lstrip": bool(entry.get("lstrip", False)),
        "rstrip": bool(entry.get("rstrip", False)),
        "normalized": bool(entry.get("normalized", True)),
        "single_word": bool(entry.get("single_word", False)),
    }


# ---------------------------------------------------------------------------
# 2. Resolve a structural marker string to a single ID (or list)
# ---------------------------------------------------------------------------


def resolve_marker_to_id(tokenizer, marker_str: str) -> list[int]:
    """
    Return the list of IDs that decode to `marker_str`.

    Walks the same precedence chain as discover_added_tokens(). Empty
    list means the marker is not in the vocabulary — caller should
    treat this as a template-reference-without-definition bug.

    Returns a list (not a single int) because vocab collisions do
    happen (e.g. a content-identical token registered twice at
    different IDs). Preflight should flag len > 1 as suspicious.
    """
    # Fast path — AutoTokenizer.convert_tokens_to_ids
    if tokenizer is not None:
        try:
            tid = tokenizer.convert_tokens_to_ids(marker_str)
            if tid is not None and tid != tokenizer.unk_token_id:
                # Also check added_tokens_decoder for duplicates
                decoder = discover_added_tokens(tokenizer)
                return sorted(
                    i for i, t in decoder.items() if t["content"] == marker_str
                ) or [tid]
        except (AttributeError, TypeError):
            pass

    # Fallback — raw scan of added_tokens_decoder
    decoder = discover_added_tokens(tokenizer)
    return sorted(i for i, t in decoder.items() if t["content"] == marker_str)


# ---------------------------------------------------------------------------
# 3. Check if a turn marker is declared as EOS
# ---------------------------------------------------------------------------


def is_turn_marker_eos(snapshot_dir: Path) -> list[tuple[int, str, str]]:
    """
    Return [(eos_id, token_content, where_in_template), ...] for every
    entry in generation_config.json's eos_token_id list that the
    chat template emits as a turn primer (i.e. a role-section opener).

    Canonical hit: GLM-5.1's [154820, 154827, 154829] —
    154827 = "<|user|>", 154829 = "<|observation|>".

    Heuristic for "is a turn primer": the token string appears in the
    template adjacent to a role tag or at the start of a branch.
    Preflight should treat any non-empty return as "EOS list leaks
    turn primers when skip_special_tokens=False".
    """
    snapshot_dir = Path(snapshot_dir)
    gen_cfg_path = snapshot_dir / "generation_config.json"
    tok_cfg_path = snapshot_dir / "tokenizer_config.json"
    template_path = snapshot_dir / "chat_template.jinja"

    if not gen_cfg_path.exists():
        return []

    gen_cfg = json.loads(gen_cfg_path.read_text())
    eos = gen_cfg.get("eos_token_id")
    if isinstance(eos, int):
        eos_ids = [eos]
    elif isinstance(eos, list):
        eos_ids = [int(x) for x in eos if isinstance(x, int)]
    else:
        return []

    # Build id -> content map from tokenizer_config.json
    id_to_str: dict[int, str] = {}
    if tok_cfg_path.exists():
        cfg = json.loads(tok_cfg_path.read_text())
        decoder = cfg.get("added_tokens_decoder", {})
        if isinstance(decoder, dict):
            for k, v in decoder.items():
                try:
                    kid = int(k)
                except (TypeError, ValueError):
                    continue
                if isinstance(v, dict) and "content" in v:
                    id_to_str[kid] = v["content"]

    # Also check tokenizer.json (wins on drift)
    tok_json_path = snapshot_dir / "tokenizer.json"
    if tok_json_path.exists():
        try:
            tok_json = json.loads(tok_json_path.read_text())
            for t in tok_json.get("added_tokens", []):
                if "id" in t and "content" in t:
                    id_to_str[int(t["id"])] = t["content"]
        except json.JSONDecodeError:
            # tokenizer.json may be an LFS pointer; skip silently
            pass

    # Load template (may be inline or sidecar)
    template_src = ""
    if template_path.exists():
        template_src = template_path.read_text()
    elif tok_cfg_path.exists():
        cfg = json.loads(tok_cfg_path.read_text())
        t = cfg.get("chat_template")
        if isinstance(t, str):
            template_src = t

    if not template_src:
        return []

    results: list[tuple[int, str, str]] = []
    for eos_id in eos_ids:
        marker = id_to_str.get(eos_id)
        if not marker:
            continue
        # Turn-primer pattern: marker appears before a role body or
        # at the start of an if-branch.
        patterns = [
            rf"{re.escape(marker)}\s*(?:\\n)?(?:\{{%|\{{\{{|\[)",
            rf"\{{%[^%]*role[^%]*==[^%]*'[^']*'[^%]*%\}}[^{{]*{re.escape(marker)}",
            rf"\{{\{{\s*'?{re.escape(marker)}'?\s*\+",
        ]
        for pat in patterns:
            m = re.search(pat, template_src)
            if m:
                results.append((eos_id, marker, m.group(0)[:80]))
                break

    return results


# ---------------------------------------------------------------------------
# 4. Cross-reference tokenizer.json vs tokenizer_config.json vs generation_config.json
# ---------------------------------------------------------------------------


def cross_ref_files(snapshot_dir: Path) -> list[dict[str, Any]]:
    """
    Compare the five config files for drift. Returns a list of findings,
    each a dict with {kind, severity, files, detail}.

    Checks:
      - EOS ID drift: tokenizer_config.eos_token → ID vs
        generation_config.eos_token_id vs config.eos_token_id
      - added_tokens_decoder (tokenizer_config) vs added_tokens
        (tokenizer.json) — stale entries
      - special_tokens_map.json vs tokenizer_config named slots
      - chat_template inline vs sidecar drift

    This is a diagnostic harness — produces findings, doesn't fix
    anything. Fixes live in layer3 or an equivalent patch pipeline.
    """
    snapshot_dir = Path(snapshot_dir)
    findings: list[dict[str, Any]] = []

    tok_cfg = _load_json(snapshot_dir / "tokenizer_config.json")
    gen_cfg = _load_json(snapshot_dir / "generation_config.json")
    model_cfg = _load_json(snapshot_dir / "config.json")
    special_map = _load_json(snapshot_dir / "special_tokens_map.json")
    tok_json = _load_json(snapshot_dir / "tokenizer.json")

    # Build id->content from whichever source is present
    id_to_str: dict[int, str] = {}
    if tok_cfg:
        decoder = tok_cfg.get("added_tokens_decoder")
        if isinstance(decoder, dict):
            for k, v in decoder.items():
                if isinstance(v, dict) and "content" in v:
                    try:
                        id_to_str[int(k)] = v["content"]
                    except (TypeError, ValueError):
                        pass
    if tok_json:
        for t in tok_json.get("added_tokens", []):
            if "id" in t and "content" in t:
                id_to_str[int(t["id"])] = t["content"]

    # --- Check 1: EOS drift ---
    tok_eos_str = _get_token_str(tok_cfg.get("eos_token")) if tok_cfg else None
    tok_eos_ids = (
        [i for i, s in id_to_str.items() if s == tok_eos_str] if tok_eos_str else []
    )

    gen_eos = gen_cfg.get("eos_token_id") if gen_cfg else None
    gen_eos_ids = (
        [gen_eos]
        if isinstance(gen_eos, int)
        else list(gen_eos)
        if isinstance(gen_eos, list)
        else []
    )

    cfg_eos = model_cfg.get("eos_token_id") if model_cfg else None
    cfg_eos_ids = (
        [cfg_eos]
        if isinstance(cfg_eos, int)
        else list(cfg_eos)
        if isinstance(cfg_eos, list)
        else []
    )

    all_eos_sources = {
        "tokenizer_config": set(tok_eos_ids),
        "generation_config": set(gen_eos_ids),
        "config": set(cfg_eos_ids),
    }
    present = {k: v for k, v in all_eos_sources.items() if v}
    if len(set(tuple(sorted(v)) for v in present.values())) > 1:
        findings.append(
            {
                "kind": "EOS_MISMATCH",
                "severity": "HIGH",
                "files": list(present.keys()),
                "detail": {k: sorted(v) for k, v in present.items()},
            }
        )

    # --- Check 2: extra_special_tokens shape ---
    if tok_cfg:
        est = tok_cfg.get("extra_special_tokens")
        if isinstance(est, list):
            findings.append(
                {
                    "kind": "EXTRA_SPECIAL_TOKENS_TYPE",
                    "severity": "HIGH",
                    "files": ["tokenizer_config.json"],
                    "detail": "extra_special_tokens is a list; crashes transformers <5.0",
                }
            )

    # --- Check 3: special_tokens_map.json drift ---
    if special_map and tok_cfg:
        for slot in (
            "bos_token",
            "eos_token",
            "pad_token",
            "unk_token",
            "cls_token",
            "sep_token",
            "mask_token",
        ):
            m1 = _get_token_str(tok_cfg.get(slot))
            m2 = _get_token_str(special_map.get(slot))
            if m1 and m2 and m1 != m2:
                findings.append(
                    {
                        "kind": "SPECIAL_TOKENS_MAP_DRIFT",
                        "severity": "MEDIUM",
                        "files": ["tokenizer_config.json", "special_tokens_map.json"],
                        "detail": {slot: {"tok_cfg": m1, "special_map": m2}},
                    }
                )

    # --- Check 4: chat_template sidecar vs inline drift ---
    sidecar = snapshot_dir / "chat_template.jinja"
    inline = tok_cfg.get("chat_template") if tok_cfg else None
    if sidecar.exists() and inline:
        sidecar_text = sidecar.read_text()
        if sidecar_text.strip() != str(inline).strip():
            findings.append(
                {
                    "kind": "CHAT_TEMPLATE_DRIFT",
                    "severity": "HIGH",
                    "files": ["chat_template.jinja", "tokenizer_config.json"],
                    "detail": "Sidecar and inline templates differ",
                }
            )

    return findings


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def _get_token_str(value) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("content")
    return None


# ---------------------------------------------------------------------------
# 5. Version-gate the tokenizer_class field
# ---------------------------------------------------------------------------


def version_gate_tokenizer_class(tokenizer_config: dict[str, Any]) -> str:
    """
    Return the minimum transformers version string required to
    instantiate the declared tokenizer_class.

    Examples:
      "TokenizersBackend"      -> ">=5.0"
      "PythonBackend"          -> ">=5.0"
      "PreTrainedTokenizerFast" -> ">=4.0"  (alias for TokenizersBackend in v5)
      "TikTokenTokenizer"      -> ">=4.0"   (custom class, remote code)
      "LlamaTokenizer"         -> ">=4.0"
      (unknown)                -> ">=4.0"
    """
    cls = tokenizer_config.get("tokenizer_class", "")
    v5_only = {
        "TokenizersBackend",
        "PythonBackend",
        "SentencePieceBackend",
        "MistralCommonBackend",
    }
    if cls in v5_only:
        return ">=5.0"
    return ">=4.0"


# ---------------------------------------------------------------------------
# 6. Minimal faithful chat-template Jinja environment
# ---------------------------------------------------------------------------


def build_chat_template_env():
    """
    Rebuild the environment that transformers uses in
    chat_template_utils.py for apply_chat_template.

    Missing from this minimal rebuild: AssistantTracker — only matters
    when return_assistant_tokens_mask=True for training-time masking.
    For preflight inspection, this env is sufficient.

    Callers must pass kwargs to env.from_string(template).render(...)
    exactly as apply_chat_template does: messages=..., tools=...,
    documents=..., add_generation_prompt=..., continue_final_message=...,
    and any chat_template_kwargs.
    """
    import json as _json
    from datetime import datetime

    import jinja2
    from jinja2.sandbox import ImmutableSandboxedEnvironment

    def _tojson(x, ensure_ascii=False, indent=None, separators=None, sort_keys=False):
        # Default ensure_ascii=False matches transformers, not stdlib
        # Jinja. Templates dumping CJK/emoji rely on this.
        return _json.dumps(
            x,
            ensure_ascii=ensure_ascii,
            indent=indent,
            separators=separators,
            sort_keys=sort_keys,
        )

    def _raise_exception(message):
        raise jinja2.exceptions.TemplateError(message)

    def _strftime_now(fmt):
        # Local TZ, not UTC — matches transformers behavior.
        # Host TZ affects rendered prompt. Document in preflight
        # report if deterministic output needed.
        return datetime.now().strftime(fmt)

    env = ImmutableSandboxedEnvironment(
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=[jinja2.ext.loopcontrols],
    )
    env.filters["tojson"] = _tojson
    env.globals["raise_exception"] = _raise_exception
    env.globals["strftime_now"] = _strftime_now
    return env


# ---------------------------------------------------------------------------
# 7. Orphan-commit check (HF Hub git-ref verification)
# ---------------------------------------------------------------------------


def verify_commit_reachable(
    repo_id: str, commit_sha: str, *, revision: str = "main"
) -> bool:
    """
    Verify that a commit SHA is reachable from the named revision
    (default "main") on the HF Hub. Guards against the GLM-5.1-FP8
    orphan-commit trap where a fix-commit exists in the repo's object
    store but is not part of the branch history.

    Requires `huggingface_hub` installed. Returns False if the commit
    is not reachable OR if the repo/branch is inaccessible.
    """
    try:
        from huggingface_hub import HfApi
    except ImportError:
        raise RuntimeError("huggingface_hub not installed") from None

    api = HfApi()
    try:
        refs = api.list_repo_refs(repo_id)
    except Exception:
        return False

    target = next(
        (b for b in refs.branches if b.name == revision),
        None,
    )
    if target is None:
        return False

    if target.target_commit == commit_sha:
        return True

    # Full-history walk would require additional API calls. The
    # simple "is it HEAD?" check catches the common case. For
    # deeper verification, use git-clone + git merge-base.
    return False


def find_nested_quantization_config(config: dict) -> list[tuple[str, dict]]:
    """Walk a HF config.json dict and return every (dotted_path, value)
    where the key is `quantization_config` and the value is non-empty.

    Multimodal/MoE configs commonly nest the real quant spec under
    `text_config`, `vision_config`, `audio_config`, or `language_config`
    while leaving the top level empty. Reading only top-level
    `config["quantization_config"]` returns `{}` and concludes "BF16"
    when the checkpoint is actually compressed-tensors W4A16 or similar.

    Verified misses if you don't walk:
    - Kimi-K2.6 / K2.5 — quant config at `text_config.quantization_config`
      (W4A16, group_size 32, MoE INT4 with BF16 self_attn/lm_head/dense).
      Top-level dtype:bfloat16 is the *compute* dtype, not storage.
    - Llama-4 vision configs
    - GLM-4V, Qwen3-VL — vision_config and text_config split

    Returns a list to surface ALL nested locations (multimodal models
    can quantize text and vision sub-models independently).
    """
    found: list[tuple[str, dict]] = []

    def walk(o, path: str = "") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                child = f"{path}.{k}" if path else k
                if k == "quantization_config" and isinstance(v, dict) and v:
                    found.append((child, v))
                walk(v, child)

    walk(config)
    return found


def summarize_quant_config(qc: dict) -> str:
    """Render a one-line summary of a `quantization_config` dict for
    triage. Handles compressed-tensors, GPTQ, AWQ, FP8, NVFP4, and
    plain pass-through. Use after find_nested_quantization_config()."""
    method = qc.get("quant_method", "?")

    if method == "compressed-tensors":
        groups = qc.get("config_groups", {})
        bits, gs, fmt = "?", "?", qc.get("format", "?")
        for g in groups.values():
            w = (g or {}).get("weights") or {}
            bits = w.get("num_bits", bits)
            gs = w.get("group_size", gs)
            break
        ignore_count = len(qc.get("ignore", []) or [])
        kv = qc.get("kv_cache_scheme")
        return (
            f"compressed-tensors num_bits={bits} group_size={gs} "
            f"format={fmt} ignore_patterns={ignore_count} "
            f"kv_cache_scheme={kv!r}"
        )

    if method in ("fp8", "modelopt", "modelopt_fp8"):
        return f"{method} kv_cache_quant_algo={qc.get('kv_cache_quant_algo')!r}"

    if method in ("gptq", "awq", "marlin"):
        return (
            f"{method} bits={qc.get('bits', '?')} "
            f"group_size={qc.get('group_size', '?')} "
            f"desc_act={qc.get('desc_act', '?')}"
        )

    return f"{method} (raw keys: {sorted(qc.keys())[:6]})"
