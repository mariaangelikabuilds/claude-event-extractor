from pydantic import BaseModel, Field
from typing import Optional


class Event(BaseModel):
    name: str
    date: str
    location: str
    url: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=200)
    source: Optional[str] = None


class EventList(BaseModel):
    events: list[Event]


EXTRACT_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "date": {"type": "string", "description": "ISO 8601 if possible"},
                    "location": {"type": "string"},
                    "url": {"type": "string"},
                    "description": {"type": "string", "maxLength": 200},
                    "source": {"type": "string"},
                },
                "required": ["name", "date", "location"],
            },
        }
    },
    "required": ["events"],
}
