import argparse
import logging

from bailing.voice_agent import VoiceAgent


def parse_args():
    parser = argparse.ArgumentParser(description="Run the interruptible voice agent showcase.")
    parser.add_argument("--config", default="config/config.yaml", help="Path to the YAML config file.")
    parser.add_argument("--no-speak", action="store_true", help="Disable TTS and audio playback.")
    return parser.parse_args()


def main():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    agent = VoiceAgent.from_config_file(args.config)
    print("Interruptible Voice Agent")
    print("Type text to simulate a user turn. Use /interrupt to stop playback and /quit to exit.\n")
    print(f"Active backends: {agent.backend_summary()}\n")

    try:
        while True:
            user_text = input("user> ").strip()
            if not user_text:
                continue
            if user_text in {"/quit", "quit", "exit"}:
                break
            if user_text == "/interrupt":
                agent.interrupt("manual CLI interrupt")
                print("assistant> [playback interrupted]\n")
                continue

            print("assistant> ", end="", flush=True)
            for chunk in agent.stream_reply(user_text, speak=not args.no_speak):
                print(chunk, end="", flush=True)
            print("\n")
    finally:
        agent.shutdown()


if __name__ == "__main__":
    main()
