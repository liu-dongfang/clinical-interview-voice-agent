import logging
from pathlib import Path

from bailing import asr, llm, player, recorder, tts, vad
from bailing.dialogue import Dialogue
from bailing.utils import drain_segments, read_config


logger = logging.getLogger(__name__)


class VoiceAgent:
    def __init__(self, config, config_path=None):
        self.config = config
        self.config_path = config_path
        self.selected = config["selected_module"]
        memory_config = config.get("Memory", {})
        self.dialogue = Dialogue(memory_config.get("dialogue_history_path", "tmp/dialogue"))
        self.allow_interruptions = config.get("system", {}).get("allow_interruptions", True)

        self.recorder = recorder.create_instance(
            self.selected["Recorder"],
            config["Recorder"][self.selected["Recorder"]],
        )
        self.asr = asr.create_instance(
            self.selected["ASR"],
            config["ASR"][self.selected["ASR"]],
        )
        self.vad = vad.create_instance(
            self.selected["VAD"],
            config["VAD"][self.selected["VAD"]],
        )
        self.llm = llm.create_instance(
            self.selected["LLM"],
            config["LLM"][self.selected["LLM"]],
        )
        self.tts = tts.create_instance(
            self.selected["TTS"],
            config["TTS"][self.selected["TTS"]],
        )
        self.player = player.create_instance(
            self.selected["Player"],
            config["Player"][self.selected["Player"]],
        )

        system_prompt = config.get("system", {}).get("system_prompt")
        if system_prompt:
            self.dialogue.add("system", system_prompt)

    @classmethod
    def from_config_file(cls, config_path):
        config_path = Path(config_path)
        return cls(read_config(config_path), config_path=config_path)

    def backend_summary(self):
        return {
            "recorder": self.selected["Recorder"],
            "asr": self.selected["ASR"],
            "vad": self.selected["VAD"],
            "llm": self.selected["LLM"],
            "tts": self.selected["TTS"],
            "player": self.selected["Player"],
        }

    def handle_audio_file(self, wav_file_path, speak=True):
        transcript, _ = self.asr.recognizer(wav_file_path)
        if not transcript:
            logger.warning("No transcript produced for %s", wav_file_path)
            return ""
        return self.respond(transcript, speak=speak)

    def respond(self, user_text, speak=True):
        return "".join(self.stream_reply(user_text, speak=speak)).strip()

    def stream_reply(self, user_text, speak=True):
        user_text = user_text.strip()
        if not user_text:
            return

        self.dialogue.add("user", user_text)
        llm_dialogue = self.dialogue.get_llm_dialogue()

        reply_chunks = []
        tts_buffer = ""
        for chunk in self.llm.stream_response(llm_dialogue):
            if not chunk:
                continue

            reply_chunks.append(chunk)
            yield chunk

            if speak:
                tts_buffer += chunk
                segments, tts_buffer = drain_segments(tts_buffer)
                for segment in segments:
                    self._speak_segment(segment)

        if speak and tts_buffer.strip():
            self._speak_segment(tts_buffer.strip())

        final_reply = "".join(reply_chunks).strip()
        if final_reply:
            self.dialogue.add("assistant", final_reply)
            self.dialogue.dump_dialogue()

    def process_audio_frame(self, audio_frame):
        if not self.allow_interruptions:
            return False
        if self.player.get_playing_status() and self.vad.is_vad(audio_frame):
            self.interrupt("speech detected while assistant output was active")
            return True
        return False

    def interrupt(self, reason="manual interrupt"):
        logger.info("Interrupt triggered: %s", reason)
        self.player.stop()
        self.vad.reset_states()

    def shutdown(self):
        self.player.shutdown()

    def _speak_segment(self, text_segment):
        audio_path = self.tts.to_tts(text_segment)
        if audio_path:
            self.player.play(audio_path)
