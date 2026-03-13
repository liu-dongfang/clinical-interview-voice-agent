import json
import os
import re
from pathlib import Path

import yaml


ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(:-([^}]*))?\}")
SEGMENT_ENDINGS = {"。", "！", "？", ".", "!", "?", ";", "；", ":"}


def load_prompt(prompt_path):
    return Path(prompt_path).read_text(encoding="utf-8").strip()


def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json_file(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def _expand_env_string(value):
    def replace(match):
        env_name = match.group(1)
        default = match.group(3) or ""
        return os.getenv(env_name, default)

    return ENV_VAR_PATTERN.sub(replace, value)


def _expand_env_values(value):
    if isinstance(value, dict):
        return {key: _expand_env_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env_values(item) for item in value]
    if isinstance(value, str):
        return _expand_env_string(value)
    return value


def read_config(config_path):
    with open(config_path, "r", encoding="utf-8") as file:
        return _expand_env_values(yaml.safe_load(file))


def is_segment(text):
    return bool(text) and text[-1] in SEGMENT_ENDINGS


def drain_segments(buffer):
    segments = []
    start = 0
    for index, char in enumerate(buffer):
        if char in SEGMENT_ENDINGS:
            segment = buffer[start:index + 1].strip()
            if segment:
                segments.append(segment)
            start = index + 1
    return segments, buffer[start:].lstrip()


def is_interrupt(query):
    lowered = query.lower()
    return any(word in lowered for word in ("停一下", "先别说", "不要说了", "stop", "hold on", "excuse me"))


def extract_json_from_string(input_string):
    match = re.search(r"(\{.*\})", input_string)
    return match.group(1) if match else None
