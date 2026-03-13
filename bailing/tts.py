import asyncio
import logging
import os
import platform
import subprocess
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime


logger = logging.getLogger(__name__)


class AbstractTTS(ABC):
    def __init__(self, config):
        self.output_dir = config.get("output_dir", "tmp/")
        os.makedirs(self.output_dir, exist_ok=True)

    def _generate_filename(self, extension):
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        return os.path.join(self.output_dir, f"tts-{timestamp}-{uuid.uuid4().hex}{extension}")

    def _log_duration(self, start_time):
        logger.debug("TTS generated in %.2fs", time.time() - start_time)

    @abstractmethod
    def to_tts(self, text):
        """Return a local audio file path."""


class GTTS(AbstractTTS):
    def __init__(self, config):
        super().__init__(config)
        self.lang = config.get("lang", "en")

    def to_tts(self, text):
        from gtts import gTTS

        output_file = self._generate_filename(".mp3")
        start_time = time.time()
        try:
            gTTS(text=text, lang=self.lang).save(output_file)
            self._log_duration(start_time)
            return output_file
        except Exception as exc:
            logger.error("gTTS failed: %s", exc)
            return None


class SystemTTS(AbstractTTS):
    def __init__(self, config):
        super().__init__(config)
        self.voice = config.get("voice")

    def to_tts(self, text):
        start_time = time.time()
        system = platform.system()
        try:
            if system == "Darwin":
                output_file = self._generate_filename(".aiff")
                command = ["say", "-o", output_file]
                if self.voice:
                    command.extend(["-v", self.voice])
                command.append(text)
            else:
                output_file = self._generate_filename(".wav")
                command = ["espeak", "-w", output_file]
                if self.voice:
                    command.extend(["-v", self.voice])
                command.append(text)

            subprocess.run(command, check=True)
            self._log_duration(start_time)
            return output_file
        except Exception as exc:
            logger.error("System TTS failed: %s", exc)
            return None


class EdgeTTS(AbstractTTS):
    def __init__(self, config):
        super().__init__(config)
        self.voice = config.get("voice", "en-US-AvaNeural")

    async def _text_to_speech(self, text, output_file):
        import edge_tts

        communicate = edge_tts.Communicate(text=text, voice=self.voice)
        await communicate.save(output_file)

    def to_tts(self, text):
        output_file = self._generate_filename(".mp3")
        start_time = time.time()
        try:
            asyncio.run(self._text_to_speech(text, output_file))
            self._log_duration(start_time)
            return output_file
        except Exception as exc:
            logger.error("EdgeTTS failed: %s", exc)
            return None


def create_instance(class_name, config):
    cls = globals().get(class_name)
    if cls is None:
        raise ValueError(f"TTS backend `{class_name}` not found")
    return cls(config)
