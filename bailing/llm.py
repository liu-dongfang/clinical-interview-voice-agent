import json
import logging
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class LLM(ABC):
    @abstractmethod
    def stream_response(self, dialogue):
        """Yield partial text chunks."""

    def response(self, dialogue):
        yield from self.stream_response(dialogue)


class OpenAIChatLLM(LLM):
    def __init__(self, config):
        import openai

        self.model_name = config.get("model_name", "gpt-4o-mini")
        self.client = openai.OpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("base_url") or config.get("url"),
        )

    def stream_response(self, dialogue):
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=dialogue,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            logger.error("OpenAI stream failed: %s", exc)


class OllamaLLM(LLM):
    def __init__(self, config):
        self.model_name = config.get("model_name", "llama3.1")
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.timeout = config.get("timeout", 120)

    def stream_response(self, dialogue):
        import requests

        payload = {
            "model": self.model_name,
            "messages": dialogue,
            "stream": True,
        }
        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/api/chat",
                json=payload,
                stream=True,
                timeout=self.timeout,
            )
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                line = json.loads(raw_line.decode("utf-8"))
                content = line.get("message", {}).get("content", "")
                if content:
                    yield content
        except Exception as exc:
            logger.error("Ollama stream failed: %s", exc)


class DummyLLM(LLM):
    def __init__(self, config):
        self.canned_response = config.get(
            "canned_response",
            "This repository is a modular voice agent prototype with interruptible dialogue flow.",
        )

    def stream_response(self, dialogue):
        del dialogue
        for token in self.canned_response.split():
            yield token + " "


def create_instance(class_name, config):
    cls = globals().get(class_name)
    if cls is None:
        raise ValueError(f"LLM backend `{class_name}` not found")
    return cls(config)
