import logging
import platform
import queue
import shutil
import subprocess
import threading
import time


logger = logging.getLogger(__name__)


class AbstractPlayer:
    def __init__(self, config=None):
        del config
        self.is_playing = False
        self.play_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._consume_queue, daemon=True)
        self._worker.start()

    def _consume_queue(self):
        while not self._stop_event.is_set():
            try:
                audio_file = self.play_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            self.is_playing = True
            try:
                self.do_playing(audio_file)
            except Exception as exc:
                logger.error("Audio playback failed: %s", exc)
            finally:
                self.is_playing = False
                self.play_queue.task_done()

    def play(self, audio_file):
        logger.info("queue audio file: %s", audio_file)
        self.play_queue.put(audio_file)

    def stop(self):
        self._clear_queue()

    def shutdown(self):
        self.stop()
        self._stop_event.set()
        if self._worker.is_alive():
            self._worker.join(timeout=1)

    def get_playing_status(self):
        return self.is_playing or not self.play_queue.empty()

    def _clear_queue(self):
        with self.play_queue.mutex:
            self.play_queue.queue.clear()

    def do_playing(self, audio_file):
        raise NotImplementedError


class NoopPlayer(AbstractPlayer):
    def do_playing(self, audio_file):
        logger.info("noop player received: %s", audio_file)
        time.sleep(0.01)


class CommandPlayer(AbstractPlayer):
    def __init__(self, config=None):
        super().__init__(config=config)
        self._current_process = None

    def _resolve_command(self, audio_file):
        system = platform.system()
        if system == "Darwin":
            return ["afplay", audio_file]
        if shutil.which("ffplay"):
            return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_file]
        raise RuntimeError("CommandPlayer requires `afplay` on macOS or `ffplay` on other platforms.")

    def do_playing(self, audio_file):
        command = self._resolve_command(audio_file)
        self._current_process = subprocess.Popen(command)
        self._current_process.wait()
        self._current_process = None

    def stop(self):
        super().stop()
        if self._current_process and self._current_process.poll() is None:
            self._current_process.terminate()
            try:
                self._current_process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self._current_process.kill()
        self._current_process = None


class PygameSoundPlayer(AbstractPlayer):
    def __init__(self, config=None):
        super().__init__(config=config)
        import pygame

        self.pygame = pygame
        self.pygame.mixer.init()

    def do_playing(self, audio_file):
        sound = self.pygame.mixer.Sound(audio_file)
        channel = sound.play()
        while channel and channel.get_busy():
            time.sleep(0.05)

    def get_playing_status(self):
        return super().get_playing_status() or self.pygame.mixer.get_busy()

    def stop(self):
        super().stop()
        self.pygame.mixer.stop()


def create_instance(class_name, config):
    cls = globals().get(class_name)
    if cls is None:
        raise ValueError(f"Player backend `{class_name}` not found")
    return cls(config)
