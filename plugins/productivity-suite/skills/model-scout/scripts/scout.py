#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["aiohttp>=3.9.0"]
# ///
"""
Model Scout - Discover and recommend AI models from OpenRouter.

Usage:
    uv run scout.py recommend --task "summarize 500 documents cheaply"
    uv run scout.py recommend --task "agent with tool calling" --needs tools,reasoning --top 5
    uv run scout.py compare --models anthropic/claude-sonnet-4 google/gemini-2.5-flash-preview
    uv run scout.py audit --suggest-updates
"""

import argparse
import asyncio
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def load_env() -> None:
    """Load .env from multiple locations."""
    locations = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent.parent.parent / ".env",
        Path.home() / "Coding" / "1. General Work" / "The Crucible" / ".env",
    ]
    for loc in locations:
        if loc.exists():
            for line in loc.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    val = val.strip().strip("'\"")
                    os.environ.setdefault(key.strip(), val)
            break


OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

CORE_PROVIDERS = {"openai", "anthropic", "google"}

# ---------------------------------------------------------------------------
# Quality heuristic tiers - maps name keywords to quality scores
# ---------------------------------------------------------------------------

QUALITY_TIERS: dict[str, float] = {
    # Tier 1: Flagship reasoning models
    "opus": 95, "o3": 92, "o1": 90,
    # Tier 2: Strong general-purpose
    "pro": 85, "4.5": 85, "4.1": 82,
    "sonnet": 80, "4o": 78, "4-turbo": 78,
    # Tier 3: Fast/efficient from core providers
    "flash": 65, "haiku": 60,
    "gpt-4o-mini": 55, "4.1-mini": 55,
    # Tier 4: Budget / small models
    "mini": 50, "nano": 40, "micro": 35,
    # Open-source model families (lower quality tier)
    "gemma": 45, "llama": 50, "mistral": 55, "mixtral": 55,
    "qwen": 50, "deepseek": 55, "command": 50, "dbrx": 45,
    "phi": 45, "yi": 45, "wizardlm": 45,
    # Routing/wrapper models
    "gpt-oss": 35, "safeguard": 30,
}

# Capability weights for bonus scoring
CAPABILITY_BONUS: dict[str, int] = {
    "tools": 20, "reasoning": 20, "structured_outputs": 15,
    "tool_choice": 10, "response_format": 10,
    "temperature": 3, "top_p": 3, "seed": 5,
}

# Signal word groups for dynamic weight adjustment
COST_SIGNALS = {"cheap", "cheapest", "budget", "cost", "save", "batch", "bulk", "economical", "affordable", "inexpensive"}
QUALITY_SIGNALS = {"best", "quality", "accurate", "reliable", "important", "critical", "precise", "careful", "complex", "reasoning", "sophisticated", "nuanced", "advanced"}
SPEED_SIGNALS = {"fast", "quick", "real-time", "realtime", "low-latency", "instant", "rapid"}
CONTEXT_SIGNALS = {"long", "document", "book", "large", "context", "transcript", "corpus", "pdf"}
VISION_SIGNALS = {"vision", "image", "screenshot", "photo", "picture", "visual", "ocr", "diagram"}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ModelInfo:
    id: str
    name: str
    context_length: int
    prompt_cost_per_m: float
    completion_cost_per_m: float
    combined_cost_per_m: float
    input_modalities: list[str]
    output_modalities: list[str]
    supported_params: list[str]
    max_completion_tokens: int
    provider: str
    expiration_date: str | None = None


@dataclass
class ScoredModel:
    model: ModelInfo
    scores: dict[str, float] = field(default_factory=dict)
    composite: float = 0.0


# ---------------------------------------------------------------------------
# API fetching
# ---------------------------------------------------------------------------

async def fetch_models(api_key: str) -> list[dict]:
    """Fetch all models from OpenRouter."""
    import aiohttp

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{OPENROUTER_API_BASE}/models",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"Error: OpenRouter API returned {resp.status}: {text}", file=sys.stderr)
                sys.exit(1)
            data = await resp.json()
            return data.get("data", [])


def parse_model(raw: dict) -> ModelInfo | None:
    """Parse a raw API model object into ModelInfo."""
    model_id = raw.get("id", "")
    if not model_id or "/" not in model_id:
        return None

    pricing = raw.get("pricing", {})
    prompt_per_token = float(pricing.get("prompt", "0") or "0")
    completion_per_token = float(pricing.get("completion", "0") or "0")
    prompt_per_m = prompt_per_token * 1_000_000
    completion_per_m = completion_per_token * 1_000_000

    arch = raw.get("architecture", {})
    top_prov = raw.get("top_provider", {})

    return ModelInfo(
        id=model_id,
        name=raw.get("name", model_id),
        context_length=raw.get("context_length") or 0,
        prompt_cost_per_m=prompt_per_m,
        completion_cost_per_m=completion_per_m,
        combined_cost_per_m=prompt_per_m + completion_per_m,
        input_modalities=arch.get("input_modalities", ["text"]),
        output_modalities=arch.get("output_modalities", ["text"]),
        supported_params=raw.get("supported_parameters", []),
        max_completion_tokens=top_prov.get("max_completion_tokens") or 0,
        provider=model_id.split("/")[0],
        expiration_date=raw.get("expiration_date"),
    )


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def is_expired(model: ModelInfo) -> bool:
    if not model.expiration_date:
        return False
    try:
        exp = datetime.fromisoformat(model.expiration_date.replace("Z", "+00:00"))
        return exp < datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False


def apply_hard_filters(
    models: list[ModelInfo],
    needs: list[str],
    min_context: int,
    max_cost: float | None,
    require_vision: bool,
) -> list[ModelInfo]:
    """Apply hard pass/fail filters."""
    result = []
    for m in models:
        if is_expired(m):
            continue
        if min_context > 0 and m.context_length < min_context:
            continue
        if max_cost is not None and m.combined_cost_per_m > max_cost:
            continue
        if require_vision and "image" not in m.input_modalities:
            continue
        # Check required capabilities
        if needs:
            # Map 'vision' need to modality check (already handled above)
            capability_needs = [n for n in needs if n != "vision"]
            if not all(n in m.supported_params for n in capability_needs):
                continue
        # Skip free wrapper / routing-only models (no real pricing)
        if ":free" in m.id:
            continue
        result.append(m)
    return result


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_provider(model: ModelInfo, all_providers: bool) -> float:
    if all_providers:
        return 100.0
    return 100.0 if model.provider in CORE_PROVIDERS else 50.0


def score_cost(model: ModelInfo) -> float:
    combined = model.combined_cost_per_m
    if combined <= 0:
        return 100.0
    # Log scale: $0.10/M -> ~100, $1/M -> ~80, $10/M -> ~60, $100/M -> ~40
    score = max(0, 100 - 20 * math.log10(max(combined, 0.01)))
    return min(100, score)


def score_context(model: ModelInfo, min_context: int) -> float:
    ctx = model.context_length
    if ctx <= 0:
        return 0.0
    if min_context > 0:
        ratio = ctx / min_context
        return min(100, 50 * ratio)
    # Absolute scale
    if ctx <= 0:
        return 0.0
    return min(100, 20 * math.log2(max(ctx, 1024) / 1024))


def score_capabilities(model: ModelInfo, needs: list[str]) -> float:
    supported = set(model.supported_params)
    if not needs:
        return 80.0
    # Filter out 'vision' which is a modality, not a param
    param_needs = [n for n in needs if n != "vision"]
    if not param_needs:
        return 85.0
    met = sum(1 for n in param_needs if n in supported)
    base = (met / len(param_needs)) * 70
    # Bonus for extra useful capabilities
    bonus_caps = [c for c in supported if c in CAPABILITY_BONUS and c not in param_needs]
    bonus = min(30, sum(CAPABILITY_BONUS.get(c, 2) for c in bonus_caps))
    return min(100, base + bonus)


def score_quality(model: ModelInfo) -> float:
    name_lower = model.name.lower()
    id_lower = model.id.lower()
    combined = f"{name_lower} {id_lower}"

    # Check specific full patterns first (before partial matches)
    if "gpt-4o-mini" in combined:
        return 55
    if "gpt-4.1-mini" in combined:
        return 58
    if "gpt-4.1-nano" in combined:
        return 45

    for keyword, tier_score in QUALITY_TIERS.items():
        if keyword in combined:
            return tier_score

    # Fallback: unknown model, conservative score
    if model.max_completion_tokens > 0:
        return min(45, 10 * math.log2(max(model.max_completion_tokens, 256) / 256))
    return 35.0


# ---------------------------------------------------------------------------
# Task signal parsing & dynamic weights
# ---------------------------------------------------------------------------

@dataclass
class TaskSignals:
    cost_sensitive: bool = False
    quality_focused: bool = False
    speed_focused: bool = False
    context_heavy: bool = False
    vision_needed: bool = False
    large_number: bool = False
    labels: list[str] = field(default_factory=list)


def parse_task_signals(task: str) -> TaskSignals:
    words = set(task.lower().split())
    signals = TaskSignals()

    if words & COST_SIGNALS:
        signals.cost_sensitive = True
        signals.labels.append("cost-sensitive")
    if words & QUALITY_SIGNALS:
        signals.quality_focused = True
        signals.labels.append("quality-focused")
    if words & SPEED_SIGNALS:
        signals.speed_focused = True
        signals.labels.append("speed-priority")
    if words & CONTEXT_SIGNALS:
        signals.context_heavy = True
        signals.labels.append("long-context")
    if words & VISION_SIGNALS:
        signals.vision_needed = True
        signals.labels.append("vision")

    # Detect large numbers (batch jobs)
    numbers = re.findall(r"\d+", task)
    if any(int(n) >= 100 for n in numbers):
        signals.large_number = True
        if not signals.cost_sensitive:
            signals.cost_sensitive = True
            signals.labels.append("batch-detected")

    return signals


def compute_weights(signals: TaskSignals) -> dict[str, float]:
    w = {
        "provider": 15,
        "cost": 25,
        "context": 15,
        "capability": 20,
        "quality": 25,
    }

    if signals.cost_sensitive:
        w["cost"] = 35
        w["quality"] = 15

    if signals.quality_focused:
        w["quality"] = 35
        w["cost"] = 15

    if signals.context_heavy:
        w["context"] = 30
        w["quality"] = max(10, w["quality"] - 10)

    if signals.speed_focused:
        w["cost"] = max(w["cost"], 30)  # Cheaper models tend to be faster

    return w


# ---------------------------------------------------------------------------
# Scoring orchestrator
# ---------------------------------------------------------------------------

def score_models(
    models: list[ModelInfo],
    needs: list[str],
    min_context: int,
    weights: dict[str, float],
    all_providers: bool,
) -> list[ScoredModel]:
    scored = []
    for m in models:
        s = ScoredModel(model=m)
        s.scores = {
            "provider": score_provider(m, all_providers),
            "cost": score_cost(m),
            "context": score_context(m, min_context),
            "capability": score_capabilities(m, needs),
            "quality": score_quality(m),
        }
        s.composite = sum(
            weights[dim] * s.scores[dim] for dim in weights
        ) / 100
        scored.append(s)

    scored.sort(key=lambda x: x.composite, reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def fmt_cost(cost: float) -> str:
    if cost <= 0:
        return "free"
    if cost < 0.01:
        return f"${cost:.4f}"
    if cost < 1:
        return f"${cost:.2f}"
    return f"${cost:.2f}"


def fmt_context(ctx: int) -> str:
    if ctx >= 1_000_000:
        return f"{ctx / 1_000_000:.1f}M"
    if ctx >= 1_000:
        return f"{ctx // 1_000}k"
    return str(ctx)


def fmt_capabilities(params: list[str]) -> str:
    key_caps = ["tools", "reasoning", "structured_outputs", "tool_choice", "response_format"]
    present = [c for c in key_caps if c in params]
    if not present:
        return "-"
    # Shorten names for display
    short = {
        "tools": "tools",
        "reasoning": "reasoning",
        "structured_outputs": "structured",
        "tool_choice": "tool_choice",
        "response_format": "resp_fmt",
    }
    return ", ".join(short.get(c, c) for c in present)


def print_recommend_table(
    scored: list[ScoredModel],
    task: str,
    signals: TaskSignals,
    weights: dict[str, float],
    top: int,
) -> None:
    top_models = scored[:top]
    if not top_models:
        print("No models matched the given requirements.")
        return

    # Header
    sig_str = ", ".join(signals.labels) if signals.labels else "general"
    w_str = " ".join(f"{k}={int(v)}" for k, v in weights.items())
    print(f'Task: "{task}"')
    print(f"Signal: {sig_str} | Weights: {w_str}")
    print()

    # Column widths
    id_w = max(35, max(len(m.model.id) for m in top_models) + 2)
    header = f"  # | {'Model':<{id_w}} | {'Cost/1M':>15} | {'Context':>8} | {'Capabilities':<20} | Score"
    sep = "-" * len(header)
    print(header)
    print(sep)

    for i, sm in enumerate(top_models, 1):
        m = sm.model
        cost_str = f"{fmt_cost(m.prompt_cost_per_m)} + {fmt_cost(m.completion_cost_per_m)}"
        caps = fmt_capabilities(m.supported_params)
        marker = "" if m.provider in CORE_PROVIDERS else " *"
        print(
            f"  {i} | {m.id:<{id_w}} | {cost_str:>15} | {fmt_context(m.context_length):>8} | {caps:<20} | {sm.composite:5.1f}{marker}"
        )

    print()
    print("Prices: prompt + completion per 1M tokens (USD)")
    if any(sm.model.provider not in CORE_PROVIDERS for sm in top_models):
        print("* = non-core provider (not OpenAI/Google/Anthropic)")


def print_recommend_json(
    scored: list[ScoredModel],
    task: str,
    signals: TaskSignals,
    weights: dict[str, float],
    top: int,
) -> None:
    output = {
        "task": task,
        "signals": signals.labels,
        "weights": weights,
        "results": [
            {
                "id": sm.model.id,
                "name": sm.model.name,
                "provider": sm.model.provider,
                "cost_prompt_per_m": sm.model.prompt_cost_per_m,
                "cost_completion_per_m": sm.model.completion_cost_per_m,
                "cost_combined_per_m": sm.model.combined_cost_per_m,
                "context_length": sm.model.context_length,
                "max_completion_tokens": sm.model.max_completion_tokens,
                "input_modalities": sm.model.input_modalities,
                "capabilities": [p for p in sm.model.supported_params if p in CAPABILITY_BONUS],
                "scores": sm.scores,
                "composite_score": round(sm.composite, 1),
            }
            for sm in scored[:top]
        ],
    }
    print(json.dumps(output, indent=2))


def print_compare_table(models: list[ModelInfo]) -> None:
    if not models:
        print("No models found for comparison.")
        return

    # Short IDs for column headers
    short_ids = [m.id.split("/", 1)[1] if "/" in m.id else m.id for m in models]
    col_w = max(22, max(len(s) for s in short_ids) + 2)

    def row(label: str, values: list[str]) -> str:
        cols = " | ".join(f"{v:<{col_w}}" for v in values)
        return f"  {label:<24} | {cols}"

    header = row("", short_ids)
    sep = "-" * len(header)

    print("Model Scout - Side-by-Side Comparison")
    print()
    print(header)
    print(sep)
    print(row("Provider", [m.provider.title() for m in models]))
    print(row("Cost (prompt/1M)", [fmt_cost(m.prompt_cost_per_m) for m in models]))
    print(row("Cost (completion/1M)", [fmt_cost(m.completion_cost_per_m) for m in models]))
    print(row("Cost (combined/1M)", [fmt_cost(m.combined_cost_per_m) for m in models]))
    print(row("Context Length", [f"{m.context_length:,}" for m in models]))
    print(row("Max Completion", [f"{m.max_completion_tokens:,}" if m.max_completion_tokens else "?" for m in models]))
    print(row("Input Modalities", [", ".join(m.input_modalities) for m in models]))
    print(row("Output Modalities", [", ".join(m.output_modalities) for m in models]))

    # Key capabilities
    key_caps = ["tools", "reasoning", "structured_outputs", "tool_choice"]
    for cap in key_caps:
        print(row(cap.replace("_", " ").title(), ["yes" if cap in m.supported_params else "no" for m in models]))

    print()


def print_compare_json(models: list[ModelInfo]) -> None:
    output = [
        {
            "id": m.id,
            "name": m.name,
            "provider": m.provider,
            "cost_prompt_per_m": m.prompt_cost_per_m,
            "cost_completion_per_m": m.completion_cost_per_m,
            "cost_combined_per_m": m.combined_cost_per_m,
            "context_length": m.context_length,
            "max_completion_tokens": m.max_completion_tokens,
            "input_modalities": m.input_modalities,
            "output_modalities": m.output_modalities,
            "supported_params": m.supported_params,
        }
        for m in models
    ]
    print(json.dumps(output, indent=2))


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def parse_ai_models_md(path: Path) -> list[dict]:
    """Parse task type -> model ID from ai-models.md table."""
    if not path.exists():
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)

    text = path.read_text()
    entries = []
    in_table = False

    for line in text.splitlines():
        if line.startswith("|") and "Task Type" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip().strip("`") for c in line.split("|")[1:-1]]
            if len(cols) >= 3:
                entries.append({
                    "task_type": cols[0],
                    "model_name": cols[1],
                    "model_id": cols[2],
                })
        elif in_table:
            break

    return entries


def print_audit_table(
    entries: list[dict],
    model_lookup: dict[str, ModelInfo],
    suggestions: dict[str, ModelInfo | None],
    suggest_updates: bool,
) -> None:
    print("Model Scout - ai-models.md Audit")
    print()

    header = f"  {'Task Type':<22} | {'Current Model':<40} | {'Status':<12} | Suggestion"
    print(header)
    print("-" * len(header))

    broken = 0
    improved = 0

    for entry in entries:
        mid = entry["model_id"]
        exists = mid in model_lookup
        status = "valid" if exists else "NOT FOUND"
        suggestion = "--"

        if not exists:
            broken += 1
            if mid in suggestions and suggestions[mid] is not None:
                alt = suggestions[mid]
                suggestion = f"REPLACE with {alt.id} ({fmt_cost(alt.combined_cost_per_m)}/M)"
            else:
                suggestion = "Model ID no longer exists on OpenRouter"
        elif mid in suggestions and suggestions[mid] is not None:
            alt = suggestions[mid]
            suggestion = f"Consider {alt.id} ({fmt_cost(alt.combined_cost_per_m)}/M vs {fmt_cost(model_lookup[mid].combined_cost_per_m)}/M)"
            improved += 1

        print(f"  {entry['task_type']:<22} | {mid:<40} | {status:<12} | {suggestion}")

    print()
    print(f"Verified {len(entries)} models. {broken} broken IDs, {improved} potential improvement(s).")

    if suggest_updates and (broken > 0 or improved > 0):
        print()
        print("Suggested replacement table for ai-models.md:")
        print()
        print("| Task Type | Model Name | OpenRouter ID |")
        print("|-----------|------------|---------------|")
        for entry in entries:
            mid = entry["model_id"]
            if mid in suggestions and suggestions[mid] is not None:
                alt = suggestions[mid]
                print(f"| {entry['task_type']} | {alt.name} | `{alt.id}` |")
            elif mid in model_lookup:
                print(f"| {entry['task_type']} | {entry['model_name']} | `{mid}` |")
            else:
                print(f"| {entry['task_type']} | {entry['model_name']} | `{mid}` (BROKEN) |")


def print_audit_json(
    entries: list[dict],
    model_lookup: dict[str, ModelInfo],
    suggestions: dict[str, ModelInfo | None],
) -> None:
    output = []
    for entry in entries:
        mid = entry["model_id"]
        exists = mid in model_lookup
        item = {
            "task_type": entry["task_type"],
            "model_id": mid,
            "model_name": entry["model_name"],
            "valid": exists,
        }
        if mid in model_lookup:
            m = model_lookup[mid]
            item["current_cost_per_m"] = m.combined_cost_per_m
        if mid in suggestions and suggestions[mid] is not None:
            alt = suggestions[mid]
            item["suggestion"] = {
                "id": alt.id,
                "name": alt.name,
                "cost_per_m": alt.combined_cost_per_m,
            }
        output.append(item)
    print(json.dumps(output, indent=2))


# Task type -> scoring requirements for audit
AUDIT_PROFILES: dict[str, dict] = {
    "Simple extraction": {"signals": "cheap batch", "needs": [], "bias": "cost"},
    "Summarization": {"signals": "cheap batch", "needs": [], "bias": "cost"},
    "Code generation": {"signals": "quality accurate", "needs": ["tools"], "bias": "quality"},
    "Complex reasoning": {"signals": "best quality", "needs": ["reasoning"], "bias": "quality"},
    "Image generation": {"signals": "", "needs": [], "bias": "skip"},  # Not an LLM task
    "Long documents": {"signals": "long document", "needs": [], "bias": "context"},
    "Fast/cheap batch": {"signals": "cheap batch fast", "needs": [], "bias": "cost"},
}


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

async def cmd_recommend(args: argparse.Namespace) -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    raw_models = await fetch_models(api_key)
    models = [m for raw in raw_models if (m := parse_model(raw)) is not None]

    needs = [n.strip() for n in args.needs.split(",")] if args.needs else []
    signals = parse_task_signals(args.task)

    # Vision detection from needs or task signals
    require_vision = "vision" in needs or signals.vision_needed

    filtered = apply_hard_filters(
        models,
        needs=needs,
        min_context=args.min_context,
        max_cost=args.max_cost,
        require_vision=require_vision,
    )

    if not filtered:
        print("No models match the given requirements. Try relaxing constraints.")
        sys.exit(0)

    weights = compute_weights(signals)
    scored = score_models(filtered, needs, args.min_context, weights, args.all_providers)

    if args.json:
        print_recommend_json(scored, args.task, signals, weights, args.top)
    else:
        print_recommend_table(scored, args.task, signals, weights, args.top)


async def cmd_compare(args: argparse.Namespace) -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    raw_models = await fetch_models(api_key)
    lookup: dict[str, ModelInfo] = {}
    for raw in raw_models:
        m = parse_model(raw)
        if m:
            lookup[m.id] = m

    found = []
    not_found = []
    for mid in args.models:
        if mid in lookup:
            found.append(lookup[mid])
        else:
            not_found.append(mid)

    if not_found:
        print(f"Warning: Model(s) not found: {', '.join(not_found)}", file=sys.stderr)

    if not found:
        print("No valid models to compare.")
        sys.exit(1)

    if args.json:
        print_compare_json(found)
    else:
        print_compare_table(found)


async def cmd_audit(args: argparse.Namespace) -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    # Find ai-models.md
    ai_models_path = Path(__file__).parent.parent.parent.parent / "rules" / "ai-models.md"
    entries = parse_ai_models_md(ai_models_path)

    raw_models = await fetch_models(api_key)
    all_models = [m for raw in raw_models if (m := parse_model(raw)) is not None]
    lookup = {m.id: m for m in all_models}

    # For each task type, find if there's a better alternative or replacement
    suggestions: dict[str, ModelInfo | None] = {}
    for entry in entries:
        mid = entry["model_id"]
        task_type = entry["task_type"]
        profile = AUDIT_PROFILES.get(task_type)

        if not profile or profile.get("bias") == "skip":
            suggestions[mid] = None
            continue

        # Run scoring for this task type
        task_signals = parse_task_signals(profile.get("signals", ""))
        needs = profile.get("needs", [])
        weights = compute_weights(task_signals)

        filtered = apply_hard_filters(
            all_models, needs=needs, min_context=0, max_cost=None, require_vision=False
        )
        scored = score_models(filtered, needs, 0, weights, all_providers=False)

        if mid not in lookup:
            # Model is broken — suggest the top-ranked replacement
            if scored:
                suggestions[mid] = scored[0].model
            else:
                suggestions[mid] = None
            continue

        # Model exists — check if there's a significantly better option
        if scored and scored[0].model.id != mid:
            top = scored[0].model
            current_scored = next((s for s in scored if s.model.id == mid), None)
            if current_scored and scored[0].composite > current_scored.composite * 1.10:
                suggestions[mid] = top
            else:
                suggestions[mid] = None
        else:
            suggestions[mid] = None

    if args.json:
        print_audit_json(entries, lookup, suggestions)
    else:
        print_audit_table(entries, lookup, suggestions, args.suggest_updates)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    load_env()

    parser = argparse.ArgumentParser(
        prog="scout",
        description="Model Scout - Discover and recommend AI models from OpenRouter",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # recommend
    rec = subparsers.add_parser("recommend", help="Recommend models for a task")
    rec.add_argument("--task", required=True, help="Natural language task description")
    rec.add_argument("--needs", default="", help="Required capabilities (comma-separated)")
    rec.add_argument("--min-context", type=int, default=0, help="Minimum context window")
    rec.add_argument("--max-cost", type=float, default=None, help="Max combined cost per 1M tokens")
    rec.add_argument("--top", type=int, default=5, help="Number of results")
    rec.add_argument("--all-providers", action="store_true", help="Remove core-three bias")
    rec.add_argument("--json", action="store_true", help="Output as JSON")

    # compare
    cmp = subparsers.add_parser("compare", help="Compare specific models side-by-side")
    cmp.add_argument("--models", nargs="+", required=True, help="Model IDs to compare")
    cmp.add_argument("--json", action="store_true", help="Output as JSON")

    # audit
    aud = subparsers.add_parser("audit", help="Audit ai-models.md")
    aud.add_argument("--suggest-updates", action="store_true", help="Show replacement table")
    aud.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "recommend":
        asyncio.run(cmd_recommend(args))
    elif args.command == "compare":
        asyncio.run(cmd_compare(args))
    elif args.command == "audit":
        asyncio.run(cmd_audit(args))


if __name__ == "__main__":
    main()
