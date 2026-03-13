import logging
import wave
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class ASR(ABC):
    @staticmethod
    def save_audio_to_file(audio_frames, file_path, channels=1, sample_width=2, sample_rate=16000):
        with wave.open(file_path, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"".join(audio_frames))

    @abstractmethod
    def recognizer(self, wav_file_path):
        """Return a `(transcript, source_path)` tuple."""


class FunASR(ASR):
    def __init__(self, config):
        model_dir = config.get("model_dir")
        if not model_dir:
            raise ValueError("FunASR requires `model_dir` in config.")

        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess

        self._postprocess = rich_transcription_postprocess
        self.model = AutoModel(
            model=model_dir,
            vad_kwargs={"max_single_segment_time": config.get("max_single_segment_time", 30000)},
            disable_update=True,
            hub=config.get("hub", "hf"),
        )
        self.language = config.get("language", "zn")
        self.use_itn = config.get("use_itn", True)
        self.batch_size_s = config.get("batch_size_s", 60)

    def recognizer(self, wav_file_path):
        try:
            response = self.model.generate(
                input=wav_file_path,
                cache={},
                language=self.language,
                use_itn=self.use_itn,
                batch_size_s=self.batch_size_s,
            )
            transcript = self._postprocess(response[0]["text"]).strip()
            logger.info("ASR transcript ready")
            return transcript or None, wav_file_path
        except Exception as exc:
            logger.error("ASR failed: %s", exc)
            return None, None


class StubASR(ASR):
    def __init__(self, config):
        self.stub_text = config.get("stub_text", "Demo transcript from the stub ASR backend.")

    def recognizer(self, wav_file_path):
        return self.stub_text, wav_file_path


def create_instance(class_name, config):
    cls = globals().get(class_name)
    if cls is None:
        raise ValueError(f"ASR backend `{class_name}` not found")
    return cls(config)
