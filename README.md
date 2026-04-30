# The two-call pattern for Claude API event extraction

A small demo showing why `web_search` + JSON-via-prompt in a single call burns
tokens and produces unreliable JSON, and how splitting it into two calls fixes
both problems.

## The problem

A single-call extractor that asks Claude to "search the web AND respond with JSON
matching this structure" loses on three fronts at once. The search tool runs as
many times as Claude wants because there is no `max_uses` cap, the model decides
on its own when "thorough" is thorough enough, and the JSON contract is enforced
only by prose instructions in the system prompt, so the response often arrives
wrapped in a prose preamble, fenced in ` ```json ` blocks, or with a trailing
sentence Claude added to be helpful. None of that is the model's fault. It is
the prompt asking one model turn to do two jobs.

## The fix

Split the work. **Call 1** runs `web_search` with `max_uses: 2` and a system
prompt that asks for a concise plain-text synthesis. **Call 2** has no web tools
at all, just a single custom tool whose `input_schema` is the event shape, with
`tool_choice` set to `{"type": "tool", "name": "extract_events"}` to force
Claude through the schema. The tool input is then validated against a Pydantic
model. Search and extraction are now independently bounded, independently
debuggable, and independently retriable.

## The result

On the demo query, the two-call pattern uses ~50-70% fewer total tokens than
the naive baseline (a recent run measured 68.9%), runs at most 2 searches
instead of 6-14, and returns deterministic, schema-validated JSON every time.
The naive baseline's JSON parses successfully on some runs and fails on others
because it depends on whether Claude wrapped the response in a prose preamble
or a ` ```json ` fence. Run `compare.py` to see the numbers on your own key.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # then paste your key
python compare.py
```

## Files

- `extractor.py`: the two-call pattern (the fix)
- `naive_baseline.py`: single-call anti-pattern for comparison
- `schemas.py`: Pydantic models + tool input schema
- `compare.py`: runs both, prints token / cost / reliability diff

Built against `anthropic>=0.88.0`, Pydantic v2, and the `web_search_20260209`
tool version. Sonnet 4.6 throughout. Pricing reflects Sonnet 4.6 list prices as
of 2026-04-30 plus the `$10 / 1k searches` web search charge.

## License

MIT
