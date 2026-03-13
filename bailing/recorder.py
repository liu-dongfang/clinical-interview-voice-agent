import logging
import queue
import threading
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class AbstractRecorder(ABC):
    @abstractmethod
    def start_recording(self, audio_queue: queue.Queue):
        """Push audio frames into the provided queue."""

    @abstractmethod
    def stop_recording(self):
        """Stop recording and release the input device."""


class NullRecorder(AbstractRecorder):
    def start_recording(self, audio_queue: queue.Queue):
        del audio_queue
        return None

    def stop_recording(self):
        return None


class RecorderPyAudio(AbstractRecorder):
    def __init__(self, config):
        import pyaudio

        self._pyaudio = pyaudio
        self.format = pyaudio.paInt16
        self.channels = config.get("channels", 1)
        self.rate = config.get("sample_rate", 16000)
        self.chunk = config.get("chunk_size", 1024)
        self.py_audio = None
        self.stream = None
        self.thread = None
        self.running = False

    def start_recording(self, audio_queue: queue.Queue):
        if self.running:
            raise RuntimeError("Recorder is already running.")

        self.py_audio = self._pyaudio.PyAudio()

        def stream_thread():
            try:
                self.stream = self.py_audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk,
                )
                self.running = True
                while self.running:
                    audio_queue.put(self.stream.read(self.chunk, exception_on_overflow=False))
            except Exception as exc:
                logger.error("Recorder stream failed: %s", exc)
            finally:
                self.running = False

        self.thread = threading.Thread(target=stream_thread, daemon=True)
        self.thread.start()

    def stop_recording(self):
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.py_audio:
            self.py_audio.terminate()
            self.py_audio = None
        if self.thread and self.thread.is_alive() and threading.current_thread() is not self.thread:
            self.thread.join(timeout=1)
        self.thread = None


def create_instance(class_name, config):
    cls = globals().get(class_name)
    if cls is None:
        raise ValueError(f"Recorder backend `{class_name}` not found")
    return cls(config)
