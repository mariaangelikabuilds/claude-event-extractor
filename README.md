# claude-event-extractor

A working demo of the **two-call pattern** for extracting structured event data
from web searches with the Claude API, without the token blowup and unreliable
JSON that plagues naive single-call implementations.

## The problem this solves

Most teams wiring up Claude with web search for data extraction do it like
this:

> One Claude call. `web_search` enabled. System prompt says "respond ONLY with
> valid JSON matching this schema."

That fails predictably:

- Claude loops the search tool 4-6+ times because it can't decide when it has
  "enough"
- JSON output is forced via prompt instructions, so it's inconsistent and
  frequently malformed
- Token usage is 2-3x what it needs to be
- No validation layer, so hallucinated fields land in your database

*None of that is the model's fault. It is the prompt asking one model turn to do two jobs.*

## The fix

Split the work into two calls. Each does one thing well.

**Call 1: bounded search.** Claude with `web_search`, capped at 2 uses, system
prompt says "synthesize and stop." Returns plain text findings.

**Call 2: forced extraction.** Claude with no web access. A `tool_use` schema
*is* the JSON contract. `tool_choice` forces Claude to call that tool. Output
is validated with Pydantic before it leaves the function.

Result: ~50% fewer tokens, deterministic JSON, validated output.

## Quick start

```bash
git clone https://github.com/mariaangelikabuilds/claude-event-extractor
cd claude-event-extractor
pip install -r requirements.txt
cp .env.example .env   # paste your ANTHROPIC_API_KEY
python compare.py
```

`compare.py` runs both the naive baseline and the two-call pattern on the same
query and prints a side-by-side token, cost, and reliability comparison.

## Configuration

Everything below is a one-line change. No hidden config, no YAML.

| What                | Where                                                         | Default                                  |
| ------------------- | ------------------------------------------------------------- | ---------------------------------------- |
| The search query    | `QUERY` in `compare.py`                                       | AI/ML conferences in Singapore Q3 2026   |
| Model               | `MODEL` in `extractor.py` and `naive_baseline.py`             | `claude-sonnet-4-6`                      |
| Search cap          | `max_uses` in `extractor.search()`                            | `2`                                      |
| Output schema       | `Event` and `EXTRACT_TOOL_SCHEMA` in `schemas.py`             | event-shaped (name, date, location, ...) |
| Pricing (cost calc) | `INPUT_COST_PER_M`, `OUTPUT_COST_PER_M`, `COST_PER_SEARCH` in `compare.py` | Sonnet 4.6 list pricing       |
| Per-call max tokens | `max_tokens=` arguments in `extractor.search` / `extract`     | `4096` / `2048`                          |
| SDK retries         | `Anthropic(max_retries=...)` in both extractors               | `8`                                      |

Adapting this to a different domain (products, places, papers, jobs, talent
profiles) is mostly a matter of editing `schemas.py` and pointing the query at
data relevant to your use case. The two-call structure stays the same.

> **Note on rate limits.** The default Sonnet 4.6 tier is 30K input
> tokens/minute. The naive baseline alone can spike to 200K+ in a single run,
> which depletes the per-minute bucket. `compare.py` runs the two-call pattern
> first and sleeps 60s before naive to give the bucket room to refill. If you
> hit `429` errors back-to-back, wait a few minutes and try again, or raise
> your tier.

## Files

- `extractor.py`: the two-call pattern
- `naive_baseline.py`: the anti-pattern, for comparison
- `compare.py`: runs both, prints the diff
- `schemas.py`: Pydantic models + JSON tool schema

## Why this matters

Token cost compounds fast in production. A 50% token reduction on 10,000
events/month at current Sonnet pricing is real money. More importantly,
deterministic JSON means your downstream pipeline (database writes, dashboards,
alerting) stops breaking on malformed output.

## License

MIT.

---

Built by [Maria Angelika Agutaya](https://github.com/mariaangelikabuilds),
Product Engineer working on Claude API integrations and MCP servers.
