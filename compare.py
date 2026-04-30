"""Run both extractors on the same query and print a side-by-side comparison."""
import time
import extractor
import naive_baseline

QUERY = "AI and machine learning conferences in Singapore in Q3 2026"

INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00
COST_PER_SEARCH = 0.01  # $10 / 1k searches


def cost(input_tokens: int, output_tokens: int, searches: int) -> float:
    return (
        input_tokens / 1_000_000 * INPUT_COST_PER_M
        + output_tokens / 1_000_000 * OUTPUT_COST_PER_M
        + searches * COST_PER_SEARCH
    )


def main() -> None:
    print(f"QUERY: {QUERY!r}")

    # Two-call first (light) so naive's heavier run can't starve it for tokens.
    try:
        two = extractor.get_events(QUERY)
    except Exception as e:
        print(f"\n[two-call] FAILED: {e!r}")
        raise

    print("\n[main] sleeping 60s so the rate-limit bucket refills before naive...")
    time.sleep(60)

    naive = naive_baseline.get_events(QUERY)
    n_in = naive["usage"]["input"]
    n_out = naive["usage"]["output"]
    n_searches = naive["usage"]["searches"]
    n_cost = cost(n_in, n_out, n_searches)
    n_count = len((naive["events"] or {}).get("events", [])) if naive["json_valid"] else 0

    print("\n" + "=" * 60)
    print("NAIVE PATTERN (single call, JSON via prompt, no max_uses)")
    print("=" * 60)
    print(f"Search rounds:  {n_searches}")
    print(f"Input tokens:   {n_in:,}")
    print(f"Output tokens:  {n_out:,}")
    print(f"Estimated cost: ${n_cost:.4f}")
    print(f"JSON valid:     {naive['json_valid']}"
          + (f" ({naive['error']})" if not naive["json_valid"] else ""))
    print(f"Events found:   {n_count}")

    print("\n" + "=" * 60)
    print("TWO-CALL PATTERN (bounded search + forced tool_use)")
    print("=" * 60)

    s = two["search_usage"]
    e = two["extract_usage"]
    t_in = s["input"] + e["input"]
    t_out = s["output"] + e["output"]
    t_searches = s["searches"]
    t_cost = cost(t_in, t_out, t_searches)
    t_count = len(two["events"]["events"])

    print(f"Search rounds:    {t_searches}  (capped at 2)")
    print(f"Search call:      in={s['input']:,}  out={s['output']:,}")
    print(f"Extract call:     in={e['input']:,}  out={e['output']:,}")
    print(f"Total input:      {t_in:,}")
    print(f"Total output:     {t_out:,}")
    print(f"Estimated cost:   ${t_cost:.4f}")
    print("JSON valid:       True (Pydantic-validated)")
    print(f"Events found:     {t_count}")

    print("\n" + "=" * 60)
    print("DIFFERENCE")
    print("=" * 60)
    total_naive = n_in + n_out
    total_two = t_in + t_out
    if total_naive > 0:
        print(f"Tokens reduced:   {(1 - total_two / total_naive) * 100:.1f}%")
    if n_cost > 0:
        print(f"Cost reduced:     {(1 - t_cost / n_cost) * 100:.1f}%")
    print(f"Searches:         {n_searches} -> {t_searches}")
    print(f"Reliability:      "
          f"{'1' if naive['json_valid'] else '0'}/1 -> 1/1")


if __name__ == "__main__":
    main()
