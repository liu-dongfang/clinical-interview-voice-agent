import math
import logging
from abc import ABC, abstractmethod
from array import array


logger = logging.getLogger(__name__)


class VAD(ABC):
    @abstractmethod
    def is_vad(self, data):
        """Return True when the provided audio frame contains speech."""

    def reset_states(self):
        return None


class EnergyVAD(VAD):
    def __init__(self, config):
        self.threshold = float(config.get("threshold", 550.0))

    def is_vad(self, data):
        if len(data) % 2 != 0:
            data = data + b"\x00"
        if not data:
            return False
        samples = array("h")
        samples.frombytes(data)
        if not samples:
            return False
        energy = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
        return float(energy) >= self.threshold


class SileroVAD(VAD):
    def __init__(self, config):
        import numpy as np
        import torch
        from silero_vad import VADIterator, load_silero_vad

        self.np = np
        self.torch = torch
        self.model = load_silero_vad()
        self.sampling_rate = config.get("sampling_rate", 16000)
        self.threshold = config.get("threshold", 0.25)
        self.min_silence_duration_ms = config.get("min_silence_duration_ms", 600)
        self.vad_iterator = VADIterator(
            self.model,
            threshold=self.threshold,
            sampling_rate=self.sampling_rate,
            min_silence_duration_ms=self.min_silence_duration_ms,
        )

    @staticmethod
    def _int16_to_float(data):
        return data.astype("float32") / 32768.0

    def is_vad(self, data):
        if data.startswith(b"RIFF"):
            data = data[44:]
        if len(data) % 2 != 0:
            data = data + b"\x00"

        audio = self._int16_to_float(self.np.frombuffer(data, dtype=self.np.int16))
        if audio.size == 0:
            return False

        chunk_size = 512 if self.sampling_rate == 16000 else 256
        for index in range(0, len(audio), chunk_size):
            chunk = audio[index:index + chunk_size]
            if len(chunk) < chunk_size:
                chunk = self.np.pad(chunk, (0, chunk_size - len(chunk)))
            if self.vad_iterator(self.torch.from_numpy(chunk)) is not None:
                return True
        return False

    def reset_states(self):
        self.vad_iterator.reset_states()


def create_instance(class_name, config):
    cls = globals().get(class_name)
    if cls is None:
        raise ValueError(f"VAD backend `{class_name}` not found")
    return cls(config)
