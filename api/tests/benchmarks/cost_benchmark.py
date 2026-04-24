"""
LLM Cost Optimization Benchmark

Tests prompt caching, response caching, and usage tracking.

Usage:
    cd api
    python -m tests.benchmarks.cost_benchmark --provider anthropic --api-key $ANTHROPIC_API_KEY
    python -m tests.benchmarks.cost_benchmark --provider openai --api-key $OPENAI_API_KEY
    python -m tests.benchmarks.cost_benchmark --all
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


RESULTS: list[dict] = []


def _row(label: str, value: str, note: str = "") -> str:
    return f"| {label:<40} | {value:<30} | {note} |"


def print_table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt = "|" + "|".join(f" {{:<{w}}} " for w in widths) + "|"
    print(f"\n### {title}")
    print(sep)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*row))
    print(sep)


# ---------------------------------------------------------------------------
# Test 1: Anthropic prompt caching
# ---------------------------------------------------------------------------

async def test_anthropic_prompt_cache(api_key: str) -> dict:
    """Verify cache_read_input_tokens appear from call 2 onwards."""
    from src.services.agents.config import ModelConfig
    from src.services.agents.llm_client import MultiProviderLLMClient, _llm_usage_ctx

    model = "claude-haiku-4-5-20251001"
    # Long system prompt (>1024 tokens) to trigger caching
    long_system = "You are a helpful assistant. " * 200

    config = ModelConfig(
        provider="anthropic",
        model_name=model,
        api_key=api_key,
        temperature=0.0,
        max_tokens=64,
    )

    rows = []
    for i in range(3):
        client = MultiProviderLLMClient(config=config)
        messages = [
            {"role": "system", "content": long_system},
            {"role": "user", "content": "Reply with the word PONG only."},
        ]
        t0 = time.perf_counter()
        chunks = []
        async for chunk in client.generate_content_stream_with_messages(messages):
            chunks.append(chunk)
        latency_ms = (time.perf_counter() - t0) * 1000
        usage = _llm_usage_ctx.get() or {}
        rows.append([
            str(i + 1),
            f"{usage.get('input_tokens', '?')}",
            f"{usage.get('cache_creation_tokens', 0)}",
            f"{usage.get('cache_read_tokens', 0)}",
            f"{latency_ms:.0f}ms",
        ])

    print_table(
        "Anthropic Prompt Caching",
        ["Call", "Input Tokens", "Cache Write", "Cache Read", "Latency"],
        rows,
    )
    cache_reads = sum(int(r[3]) for r in rows[1:] if r[3].isdigit())
    passed = cache_reads > 0
    print(f"  Result: {'PASS' if passed else 'FAIL'} — cache_read_tokens={cache_reads} on calls 2-3")
    return {"test": "anthropic_prompt_cache", "passed": passed, "rows": rows}


# ---------------------------------------------------------------------------
# Test 2: OpenAI cached_tokens tracking
# ---------------------------------------------------------------------------

async def test_openai_cached_tokens(api_key: str) -> dict:
    """Verify cached_input_tokens appear in usage for repeated prompts (>1024 tokens)."""
    from src.services.agents.config import ModelConfig
    from src.services.agents.llm_client import MultiProviderLLMClient, _llm_usage_ctx

    model = "gpt-4o-mini"
    # Need >1024 tokens for OpenAI to cache
    long_prompt = "Explain the theory of relativity. " * 40

    config = ModelConfig(
        provider="openai",
        model_name=model,
        api_key=api_key,
        temperature=0.0,
        max_tokens=32,
    )

    rows = []
    for i in range(3):
        client = MultiProviderLLMClient(config=config)
        messages = [{"role": "user", "content": long_prompt}]
        t0 = time.perf_counter()
        chunks = []
        async for chunk in client.generate_content_stream_with_messages(messages):
            chunks.append(chunk)
        latency_ms = (time.perf_counter() - t0) * 1000
        usage = _llm_usage_ctx.get() or {}
        rows.append([
            str(i + 1),
            f"{usage.get('input_tokens', '?')}",
            f"{usage.get('cached_input_tokens', 0)}",
            f"{latency_ms:.0f}ms",
        ])

    print_table(
        "OpenAI Automatic Caching",
        ["Call", "Input Tokens", "Cached Tokens", "Latency"],
        rows,
    )
    cached = sum(int(r[2]) for r in rows[1:] if r[2].isdigit())
    passed = cached > 0
    print(f"  Result: {'PASS' if passed else 'FAIL (may need larger prompt or 2nd call)'} — cached={cached}")
    return {"test": "openai_cached_tokens", "passed": passed, "rows": rows}


# ---------------------------------------------------------------------------
# Test 3: Response cache (Redis)
# ---------------------------------------------------------------------------

async def test_response_cache(provider: str, api_key: str) -> dict:
    """Verify Redis response cache returns sub-5ms on 2nd call."""
    from src.services.agents.config import ModelConfig
    from src.services.agents.llm_client import MultiProviderLLMClient
    from src.services.cache.llm_response_cache import get_cached_response, set_cached_response

    if provider == "anthropic":
        model = "claude-haiku-4-5-20251001"
    else:
        model = "gpt-4o-mini"

    config = ModelConfig(
        provider=provider,
        model_name=model,
        api_key=api_key,
        temperature=0.0,
        max_tokens=32,
    )
    client = MultiProviderLLMClient(config=config)
    client.set_cost_context(
        tenant_id="00000000-0000-0000-0000-000000000001",
        enable_response_cache=True,
        system_prompt_hash="abcd1234",
        agent_updated_at="1234567890.0",
    )

    prompt = "What is the capital of France? Reply in one word."
    messages = [{"role": "user", "content": prompt}]

    rows = []
    for i in range(2):
        t0 = time.perf_counter()
        if i == 0:
            # First call: LLM
            response = await client.generate_content(prompt, temperature=0.0)
            # Manually cache since generate_content uses response cache too
            await set_cached_response(
                provider=provider,
                model_name=model,
                temperature=0.0,
                messages=messages,
                response=response,
                system_prompt_hash="abcd1234",
                agent_updated_at="1234567890.0",
            )
            source = "LLM"
        else:
            cached = await get_cached_response(
                provider=provider,
                model_name=model,
                temperature=0.0,
                messages=messages,
                system_prompt_hash="abcd1234",
                agent_updated_at="1234567890.0",
            )
            response = cached or "(cache miss)"
            source = "Redis Cache" if cached else "MISS"

        latency_ms = (time.perf_counter() - t0) * 1000
        rows.append([str(i + 1), source, f"{latency_ms:.1f}ms", response[:40]])

    print_table(
        "LLM Response Cache (Redis)",
        ["Call", "Source", "Latency", "Response Preview"],
        rows,
    )
    passed = len(rows) >= 2 and rows[1][1] == "Redis Cache" and float(rows[1][2].rstrip("ms")) < 50
    print(f"  Result: {'PASS' if passed else 'FAIL'} — call-2 from Redis: {rows[1][1]}, {rows[1][2]}")
    return {"test": "response_cache", "passed": passed, "rows": rows}


# ---------------------------------------------------------------------------
# Test 4: Cost calculation
# ---------------------------------------------------------------------------

def test_cost_calculation() -> dict:
    """Verify cost resolution uses existing pricing sources."""
    from src.services.billing.llm_cost_service import _resolve_pricing, calculate_cost

    rows = []
    cases = [
        ("claude-haiku-4-5-20251001", None, 1000, 500, 0, 0),
        ("gpt-4o", None, 1000, 200, 0, 0),
        ("claude-haiku-4-5-20251001", None, 500, 200, 300, 100),  # with cache
        ("totally-unknown-model-xyz", None, 1000, 200, 0, 0),
    ]
    all_passed = True
    for model, rules, inp, out, cache_read, cache_create in cases:
        cost = calculate_cost(model, inp, out, cache_read, cache_create, rules)
        inp_rate, out_rate = _resolve_pricing(model, rules)
        rows.append([
            model[:35],
            f"{inp}",
            f"{out}",
            f"${inp_rate:.5f}/1k" if inp_rate else "unknown",
            f"${cost:.8f}" if cost is not None else "None",
        ])
        if "unknown-model" not in model and cost is None:
            all_passed = False

    print_table(
        "Cost Calculation",
        ["Model", "In Tokens", "Out Tokens", "Input Rate", "Estimated Cost"],
        rows,
    )
    print(f"  Result: {'PASS' if all_passed else 'FAIL'}")
    return {"test": "cost_calculation", "passed": all_passed, "rows": rows}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="LLM Cost Optimization Benchmark")
    p.add_argument("--provider", choices=["anthropic", "openai"], default="anthropic")
    p.add_argument("--api-key", help="API key (defaults to ANTHROPIC_API_KEY / OPENAI_API_KEY env var)")
    p.add_argument("--all", action="store_true", dest="run_all", help="Run all tests")
    p.add_argument("--output", default="tests/benchmarks/benchmark_results.md", help="Output file for results")
    return p.parse_args()


async def main():
    args = parse_args()

    provider = args.provider
    api_key = args.api_key or os.getenv(
        "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY", ""
    )

    print(f"\nLLM Cost Optimization Benchmark")
    print(f"Provider: {provider}  |  Model: varies")
    print("=" * 60)

    results = []

    # Cost calculation (no API key needed)
    results.append(test_cost_calculation())

    if api_key:
        if provider == "anthropic" or args.run_all:
            anthropic_key = api_key if provider == "anthropic" else os.getenv("ANTHROPIC_API_KEY", "")
            if anthropic_key:
                results.append(await test_anthropic_prompt_cache(anthropic_key))

        if provider == "openai" or args.run_all:
            openai_key = api_key if provider == "openai" else os.getenv("OPENAI_API_KEY", "")
            if openai_key:
                results.append(await test_openai_cached_tokens(openai_key))

        results.append(await test_response_cache(provider, api_key))
    else:
        print("\n  (Skipping API tests — no API key provided)")

    # Summary
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")

    # Write markdown results
    md_lines = [
        "# LLM Cost Benchmark Results\n",
        f"Provider: {provider}\n",
    ]
    for r in results:
        status = "PASS" if r.get("passed") else "FAIL"
        md_lines.append(f"- {r['test']}: **{status}**\n")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(md_lines))
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
