"""Two-call pattern: bounded search, then forced structured extraction.

Verified against https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
on 2026-04-30. web_search_20260209 is current; runs in basic mode without code_execution.
"""
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from schemas import EventList, EXTRACT_TOOL_SCHEMA

load_dotenv()

MODEL = "claude-sonnet-4-6"
# Generous retries so rate-limit hiccups self-heal during the demo
client = Anthropic(max_retries=8)


def _usage(response):
    u = response.usage
    searches = (u.server_tool_use.web_search_requests
                if getattr(u, "server_tool_use", None) else 0)
    return {"input": u.input_tokens, "output": u.output_tokens, "searches": searches}


def search(query: str) -> tuple[str, dict]:
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=(
            "Use the web_search tool at most twice. Synthesize findings concisely "
            "into a single plain-text summary listing each event with name, date, "
            "location, URL, and source. Stop searching as soon as you have enough."
        ),
        tools=[{
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": 2,
        }],
        messages=[{"role": "user", "content": query}],
    )
    text = "\n".join(b.text for b in response.content if b.type == "text")
    return text, _usage(response)


def extract(text: str) -> tuple[dict, dict]:
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        tools=[{
            "name": "extract_events",
            "description": "Record the events found in the input text.",
            "input_schema": EXTRACT_TOOL_SCHEMA,
        }],
        tool_choice={"type": "tool", "name": "extract_events"},
        messages=[{
            "role": "user",
            "content": (
                "Extract every event mentioned below into the extract_events tool. "
                "Use ISO 8601 dates when possible. Keep descriptions under 200 chars.\n\n"
                f"{text}"
            ),
        }],
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    validated = EventList.model_validate(tool_use.input).model_dump()
    return validated, _usage(response)


def get_events(query: str) -> dict:
    print(f"\n[two-call] query: {query!r}")
    text, search_usage = search(query)
    print(f"[two-call] search:  in={search_usage['input']} out={search_usage['output']} "
          f"searches={search_usage['searches']}")
    try:
        events, extract_usage = extract(text)
    except ValidationError as e:
        print(f"[two-call] validation failed: {e}")
        raise
    print(f"[two-call] extract: in={extract_usage['input']} out={extract_usage['output']}")
    return {
        "events": events,
        "search_usage": search_usage,
        "extract_usage": extract_usage,
    }


if __name__ == "__main__":
    import json
    result = get_events("AI and machine learning conferences in Singapore in Q3 2026")
    print(json.dumps(result["events"], indent=2))
