from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from bailing.utils import write_json_file


@dataclass
class Message:
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class Dialogue:
    def __init__(self, dialogue_history_path=None):
        self.dialogue_history_path = Path(dialogue_history_path) if dialogue_history_path else None
        self.messages: list[Message] = []

    def put(self, message: Message):
        self.messages.append(message)

    def add(self, role, content, metadata=None):
        self.put(Message(role=role, content=content, metadata=metadata or {}))

    def get_llm_dialogue(self):
        return [{"role": message.role, "content": message.content} for message in self.messages]

    def dump_dialogue(self):
        if not self.dialogue_history_path:
            return

        self.dialogue_history_path.mkdir(parents=True, exist_ok=True)
        file_name = self.dialogue_history_path / f"dialogue-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        write_json_file(file_name, [message.__dict__ for message in self.messages])
