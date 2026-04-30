"""Single-call anti-pattern: web_search + JSON-via-prompt in one shot.

Deliberately wrong on purpose to demonstrate the failure mode the client described:
unbounded searches, JSON requested via prose, no validation, no structure enforcement.
"""
import json
import re
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"
client = Anthropic(max_retries=8)

# This is intentionally the WRONG way to do it. Real Upwork posts in this category
# include language like "search the web and return JSON". No max_uses cap, no
# tool_choice, contract enforced via prose. That is the failure mode under test.
NAIVE_SYSTEM = (
    "You are an event database scraper. Search the web for matching events and "
    "respond ONLY with valid JSON matching this exact structure: "
    "{\"events\": [{\"name\": str, \"date\": str, \"location\": str, "
    "\"url\": str, \"description\": str, \"source\": str}]}. No prose, no markdown "
    "fences, no commentary. Just the raw JSON object."
)


def get_events(query: str) -> dict:
    print(f"\n[naive] query: {query!r}")
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=NAIVE_SYSTEM,
        tools=[{"type": "web_search_20260209", "name": "web_search"}],  # NO max_uses
        messages=[{"role": "user", "content": query}],
    )

    u = response.usage
    searches = (u.server_tool_use.web_search_requests
                if getattr(u, "server_tool_use", None) else 0)
    usage = {"input": u.input_tokens, "output": u.output_tokens, "searches": searches}
    print(f"[naive] in={usage['input']} out={usage['output']} searches={usage['searches']}")

    text = "\n".join(b.text for b in response.content if b.type == "text").strip()
    # Strip markdown fences if Claude added them despite instructions
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()

    try:
        events = json.loads(text)
        json_valid = True
        error = None
    except json.JSONDecodeError as e:
        events = None
        json_valid = False
        error = f"JSONDecodeError: {e.msg} at line {e.lineno} col {e.colno}"

    return {"events": events, "usage": usage, "json_valid": json_valid, "error": error}


if __name__ == "__main__":
    result = get_events("AI and machine learning conferences in Singapore in Q3 2026")
    print(json.dumps(result, indent=2, default=str))
